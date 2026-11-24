import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import audit, bind_db_to_user, current_user, rate_limit
from ..models import AuthSession, Consent, Profile, User
from ..schemas import ChangePasswordIn, LoginIn, RefreshIn, SignupIn, TokenOut
from ..security import (create_access_token, email_hash, encrypt_str, hash_password, needs_rehash, new_refresh_token,
                        password_problem, sha256, verify_password)
from ..services.planner import age_from_dob

router = APIRouter(prefix="/auth", tags=["auth"])


def issue_tokens(db: Session, user_id: str, family: str | None = None) -> TokenOut:
    s = get_settings()
    refresh = new_refresh_token()
    sess = AuthSession(user_id=user_id, family=family or str(uuid.uuid4()), refresh_hash=sha256(refresh),
                       expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_days))
    db.add(sess)
    db.flush()
    return TokenOut(access_token=create_access_token(user_id, sess.id), refresh_token=refresh,
                    expires_in=s.access_token_minutes * 60)


@router.post("/signup", response_model=TokenOut, status_code=201, dependencies=[Depends(rate_limit("signup", 10, 3600))])
def signup(body: SignupIn, db: Session = Depends(get_db)):
    s = get_settings()
    if not body.accept_terms_privacy:
        raise HTTPException(422, "You need to accept the terms and privacy notice to create an account.")
    if not body.consent_health_data:
        raise HTTPException(422, "Setwise cannot build your plan without your consent to process your health information. "
                                 "You can withdraw it at any time.")
    if age_from_dob(body.date_of_birth) < s.min_age_years:
        raise HTTPException(403, f"Setwise is for people aged {s.min_age_years} or older.")
    problem = password_problem(body.password, body.email)
    if problem:
        raise HTTPException(422, problem)

    user = User(email_hash=email_hash(body.email), email_enc=body.email.lower(), password_hash=hash_password(body.password))
    try:
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError:
        raise HTTPException(409, "We could not create an account with those details.")
    bind_db_to_user(db, user.id)
    v = s.policy_version
    db.add_all([
        Consent(user_id=user.id, purpose="terms_privacy", granted=True, policy_version=v),
        Consent(user_id=user.id, purpose="health_data", granted=True, policy_version=v),
        Consent(user_id=user.id, purpose="ai_coach", granted=body.consent_ai_coach, policy_version=v),
    ])
    db.add(Profile(user_id=user.id, goal="fit", level="beginner", days_per_week=3,
                   health={"dob": body.date_of_birth.isoformat(), "sex": "x", "height_cm": None, "weight_kg": None,
                           "restrictions": [], "onboarded": False}))
    audit(db, user.id, "signup")
    return issue_tokens(db, user.id)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit("login", 20, 300))])
def login(body: LoginIn, db: Session = Depends(get_db)):
    s = get_settings()
    now = datetime.now(timezone.utc)
    user = db.execute(select(User).where(User.email_hash == email_hash(body.email))).scalar_one_or_none()
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not ok:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= s.max_failed_logins:
                user.locked_until = now + timedelta(minutes=s.lockout_minutes)
                user.failed_logins = 0
                audit(db, user.id, "account_locked")
            db.commit()  # persist the counter before raising
        raise HTTPException(401, "Incorrect email or password.")
    user.failed_logins = 0
    user.locked_until = None
    user.last_active_at = now
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    audit(db, user.id, "login")
    return issue_tokens(db, user.id)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(rate_limit("refresh", 60, 300))])
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    sess = db.execute(select(AuthSession).where(AuthSession.refresh_hash == sha256(body.refresh_token))).scalar_one_or_none()
    if not sess:
        raise HTTPException(401, "Please sign in again.")
    if sess.revoked_at is not None:
        # An old token was replayed: assume theft and end the whole session family.
        db.execute(update(AuthSession).where(AuthSession.family == sess.family, AuthSession.revoked_at.is_(None)).values(revoked_at=now))
        audit(db, sess.user_id, "refresh_reuse_detected")
        db.commit()
        raise HTTPException(401, "Please sign in again.")
    if sess.expires_at < now:
        raise HTTPException(401, "Please sign in again.")
    sess.revoked_at = now
    return issue_tokens(db, sess.user_id, family=sess.family)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    sess = db.execute(select(AuthSession).where(AuthSession.refresh_hash == sha256(body.refresh_token))).scalar_one_or_none()
    if sess and sess.revoked_at is None:
        sess.revoked_at = datetime.now(timezone.utc)


@router.post("/logout-all", status_code=204)
def logout_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
               .values(revoked_at=datetime.now(timezone.utc)))
    audit(db, user.id, "logout_all")


@router.post("/change-password", response_model=TokenOut, dependencies=[Depends(rate_limit("chpw", 10, 600))])
def change_password(body: ChangePasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(401, "Your current password is not correct.")
    problem = password_problem(body.new_password, "")
    if problem:
        raise HTTPException(422, problem)
    user.password_hash = hash_password(body.new_password)
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
               .values(revoked_at=datetime.now(timezone.utc)))
    audit(db, user.id, "password_changed")
    return issue_tokens(db, user.id)
