import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

OWNER = os.environ.get("TEST_OWNER_URL")
APP = os.environ.get("TEST_APP_URL")
MAINT = os.environ.get("TEST_MAINT_URL")

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", "")
os.environ["ANTHROPIC_API_KEY"] = ""


@pytest.fixture(scope="session")
def db_ready():
    if not (OWNER and APP):
        pytest.skip("Set TEST_OWNER_URL and TEST_APP_URL (see scripts/start_test_pg.sh)")
    from app import migrate
    from app.db import set_engine_for_tests

    migrate.run(OWNER)
    set_engine_for_tests(APP)
    return True


@pytest.fixture()
def owner_engine(db_ready):
    return create_engine(OWNER)


@pytest.fixture()
def app_engine(db_ready):
    return create_engine(APP)


@pytest.fixture()
def client(db_ready, owner_engine):
    from app.deps import reset_rate_limits
    from app.main import app

    with owner_engine.begin() as c:
        c.execute(text("TRUNCATE users, audit_log CASCADE"))
    reset_rate_limits()
    with TestClient(app) as tc:
        yield tc


def signup(client, email="sipho@example.com", password="Correct-horse-9", dob="1998-04-12", ai=False, health=True):
    r = client.post("/auth/signup", json={"email": email, "password": password, "date_of_birth": dob,
                                          "accept_terms_privacy": True, "consent_health_data": health, "consent_ai_coach": ai})
    return r


def auth(client, **kw):
    r = signup(client, **kw)
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}, r.json()


PROFILE = {"goal": "muscle", "level": "beginner", "days_per_week": 3, "sex": "m", "height_cm": 178, "weight_kg": 78.5, "restrictions": []}


def onboard(client, headers, **over):
    r = client.put("/me/profile", json={**PROFILE, **over}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()
