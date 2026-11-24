import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from tests.conftest import auth, onboard

SETS = [{"ex": "db_bench", "w": 10, "reps": 12, "eff": "good"}, {"ex": "db_bench", "w": 10, "reps": 12, "eff": "good"}]


def log_workout(client, h):
    r = client.post("/workouts", json={"day": "2026-10-01", "name": "Push", "minutes": 40, "sets": SETS}, headers=h)
    assert r.status_code == 201, r.text


def test_health_data_is_encrypted_at_rest(client, owner_engine):
    h, _ = auth(client)
    onboard(client, h, weight_kg=78.5, height_cm=178)
    log_workout(client, h)
    with owner_engine.connect() as c:
        blob = c.execute(text("select health from profiles")).scalar()
        email = c.execute(text("select email_enc from users")).scalar()
        sets = c.execute(text("select sets from workouts")).scalar()
        kg = c.execute(text("select kg from weight_logs")).scalar()
    for raw in (blob, email, sets, kg):
        assert raw.startswith("gAAAA")  # Fernet token, not readable JSON
    assert "78.5" not in blob and "sipho" not in email and "db_bench" not in sets


def test_users_cannot_see_each_others_data(client):
    ha, _ = auth(client, email="a@example.com")
    hb, _ = auth(client, email="b@example.com")
    onboard(client, ha)
    onboard(client, hb, goal="lose")
    log_workout(client, ha)
    assert len(client.get("/workouts", headers=ha).json()) == 1
    assert client.get("/workouts", headers=hb).json() == []
    assert client.get("/me", headers=hb).json()["goal"] == "lose"


def test_database_rls_blocks_other_rows_even_with_a_bug(client, app_engine):
    ha, _ = auth(client, email="a@example.com")
    onboard(client, ha)
    log_workout(client, ha)
    with app_engine.begin() as c:
        # No user bound: the API role sees nothing in user tables.
        assert c.execute(text("select count(*) from workouts")).scalar() == 0
        assert c.execute(text("select count(*) from profiles")).scalar() == 0
        c.execute(text("select set_config('app.user_id', 'someone-else', true)"))
        assert c.execute(text("select count(*) from workouts")).scalar() == 0
    with app_engine.connect() as c:
        with pytest.raises(ProgrammingError):
            c.execute(text("insert into workouts(id,user_id,day,name,minutes,sets,created_at) values('x','nobody','2026-01-01','x',1,'x',now())"))


def test_api_role_is_least_privilege(app_engine):
    with app_engine.connect() as c:
        for stmt in ("create table evil(id int)", "update audit_log set action='x'", "delete from audit_log", "drop table users"):
            with pytest.raises(ProgrammingError):
                c.execute(text(stmt))
            c.rollback()


def test_consent_gate_and_withdrawal(client):
    h, _ = auth(client)
    onboard(client, h)
    assert client.get("/plan", headers=h).status_code == 200
    assert client.post("/me/consents", json={"purpose": "health_data", "granted": False}, headers=h).status_code == 200
    r = client.get("/plan", headers=h)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required"
    paused = client.get("/me", headers=h).json()
    assert paused["health_paused"] and paused["weight_kg"] is None and paused["targets"] is None
    for path in ("/workouts", "/cardio", "/nutrition/pantry", "/me/weights", "/coach/history"):
        assert client.get(path, headers=h).status_code == 403, path
    assert client.get("/me/export", headers=h).status_code == 200  # access rights still work
    client.post("/me/consents", json={"purpose": "health_data", "granted": True}, headers=h)
    assert client.get("/plan", headers=h).status_code == 200
    assert client.post("/me/consents", json={"purpose": "terms_privacy", "granted": False}, headers=h).status_code == 422


def test_export_contains_everything_decrypted(client):
    h, _ = auth(client)
    onboard(client, h)
    log_workout(client, h)
    client.post("/cardio", json={"kind": "walk", "started_at": "2026-10-01T08:00:00Z", "seconds": 1800, "steps": 3500}, headers=h)
    data = client.get("/me/export", headers=h).json()
    assert data["account"]["email"] == "sipho@example.com"
    assert data["profile"]["weight_kg"] == 78.5 and data["profile"]["dob"] == "1998-04-12"
    assert len(data["workouts"]) == 1 and len(data["cardio"]) == 1 and len(data["consents"]) == 3
    assert any(e["action"] == "signup" for e in data["security_events"])


def test_delete_account_erases_everything_and_keeps_anonymous_audit(client, owner_engine):
    h, _ = auth(client)
    onboard(client, h)
    log_workout(client, h)
    client.put("/nutrition/pantry", json={"foods": ["eggs", "rice"]}, headers=h)
    client.post("/coach", json={"message": "how heavy should I go?"}, headers=h)
    assert client.post("/me/delete", json={"password": "wrong-wrong-1"}, headers=h).status_code == 401
    assert client.post("/me/delete", json={"password": "Correct-horse-9"}, headers=h).status_code == 204
    with owner_engine.connect() as c:
        for t in ("users", "profiles", "workouts", "weight_logs", "food_profiles", "coach_messages", "consents", "auth_sessions", "exercise_state"):
            assert c.execute(text(f"select count(*) from {t}")).scalar() == 0, t
        rows = c.execute(text("select user_id, action from audit_log")).all()
    assert rows and all(r[0] is None for r in rows)  # events survive without any link to the person
    assert client.get("/me", headers=h).status_code == 401


def test_ai_consent_withdrawal_deletes_chat(client):
    h, _ = auth(client, ai=True)
    onboard(client, h)
    client.post("/coach", json={"message": "how many days should I train?"}, headers=h)
    assert len(client.get("/coach/history", headers=h).json()) == 2
    client.post("/me/consents", json={"purpose": "ai_coach", "granted": False}, headers=h)
    assert client.get("/coach/history", headers=h).json() == []


def test_audit_log_has_no_health_data(client, owner_engine):
    h, _ = auth(client)
    onboard(client, h, weight_kg=91.3)
    with owner_engine.connect() as c:
        dump = json.dumps([list(map(str, r)) for r in c.execute(text("select action, detail from audit_log"))])
    assert "91.3" not in dump and "sipho" not in dump


def test_maintenance_purges_inactive_and_old(client, owner_engine):
    import os
    from app import maintenance
    from tests.conftest import MAINT

    auth(client, email="old@example.com")
    auth(client, email="new@example.com")
    with owner_engine.begin() as c:
        c.execute(text("update users set last_active_at = now() - interval '800 days' where email_hash = (select email_hash from users order by created_at limit 1)"))
    res = maintenance.run(MAINT)
    assert res["accounts"] == 1
    with owner_engine.connect() as c:
        assert c.execute(text("select count(*) from users")).scalar() == 1
