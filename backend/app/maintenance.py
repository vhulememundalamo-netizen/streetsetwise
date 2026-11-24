"""Retention job (POPIA s14): run daily, e.g. `python -m app.maintenance`.

Uses its own database role (MAINTENANCE_DATABASE_URL) so the API role never needs broad delete rights.
Deletes: accounts inactive for INACTIVE_ACCOUNT_DAYS, coach chat older than 90 days, audit events
older than AUDIT_LOG_DAYS, expired or revoked login sessions older than 30 days.
"""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AuditLog, AuthSession, CoachMessage, User


def run(url: str | None = None) -> dict:
    s = get_settings()
    url = url or os.environ.get("MAINTENANCE_DATABASE_URL") or s.database_url
    eng = create_engine(url)
    now = datetime.now(timezone.utc)
    with Session(eng) as db:
        a = db.execute(delete(User).where(User.last_active_at < now - timedelta(days=s.inactive_account_days))).rowcount
        c = db.execute(delete(CoachMessage).where(CoachMessage.created_at < now - timedelta(days=90))).rowcount
        l = db.execute(delete(AuditLog).where(AuditLog.created_at < now - timedelta(days=s.audit_log_days))).rowcount
        t = db.execute(delete(AuthSession).where(AuthSession.expires_at < now - timedelta(days=30))).rowcount
        db.commit()
    return {"accounts": a, "coach_messages": c, "audit": l, "sessions": t}


if __name__ == "__main__":
    print(run())
