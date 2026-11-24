"""Request dependencies: authentication, per-request database scoping, consent gates, audit, rate limits."""
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuditLog, AuthSession, Consent, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def audit(db: Session, user_id: str | None, action: str, detail: dict | None = None) -> None:
    """Security-relevant events only. Never put health data, message text or IP addresses here."""
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))


def bind_db_to_user(db: Session, user_id: str) -> None:
    """Row-level security: from here on, PostgreSQL itself only shows rows with this user_id."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("select set_config('app.user_id', :u, true)"), {"u": user_id})


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    unauth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauth
    data = decode_access_token(creds.credentials)
    if not data:
        raise unauth
    sess = db.get(AuthSession, data["sid"])
    now = datetime.now(timezone.utc)
    if not sess or sess.revoked_at is not None or sess.user_id != data["sub"] or sess.expires_at < now:
        raise unauth
    user = db.get(User, data["sub"])
    if not user:
        raise unauth
    bind_db_to_user(db, user.id)
    if now - user.last_active_at > timedelta(hours=1):
        user.last_active_at = now
    return user


def consent_state(db: Session, user_id: str) -> dict[str, bool]:
    rows = db.execute(select(Consent).where(Consent.user_id == user_id).order_by(Consent.created_at)).scalars().all()
    state: dict[str, bool] = {}
    for r in rows:  # later rows override earlier ones
        state[r.purpose] = r.granted
    return state


def require_consent(purpose: str):
    def dep(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
        if not consent_state(db, user.id).get(purpose):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "consent_required", "purpose": purpose})
        return user

    return dep


# ---------- rate limiting (in-memory; use Redis behind several instances) ----------
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(name: str, limit: int, per_seconds: int):
    def dep(request: Request):
        host = request.client.host if request.client else "unknown"
        key = f"{name}:{host}"  # held in memory only, never written to disk or logs
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > per_seconds:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again soon.",
                                headers={"Retry-After": str(per_seconds)})
        q.append(now)

    return dep


def reset_rate_limits() -> None:
    _hits.clear()
