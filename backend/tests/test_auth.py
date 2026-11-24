from datetime import date, timedelta

from sqlalchemy import text

from tests.conftest import auth, signup


def test_signup_and_login(client):
    h, tokens = auth(client)
    assert client.get("/me", headers=h).json()["consents"] == {"terms_privacy": True, "health_data": True, "ai_coach": False}
    r = client.post("/auth/login", json={"email": "SIPHO@example.com", "password": "Correct-horse-9"})
    assert r.status_code == 200 and r.json()["access_token"]


def test_underage_rejected(client):
    dob = (date.today() - timedelta(days=365 * 16)).isoformat()
    assert signup(client, dob=dob).status_code == 403


def test_exactly_18_today_allowed(client):
    t = date.today()
    assert signup(client, dob=t.replace(year=t.year - 18).isoformat()).status_code == 201


def test_consent_is_required(client):
    assert signup(client, health=False).status_code == 422
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "Correct-horse-9", "date_of_birth": "1990-01-01",
                                          "accept_terms_privacy": False, "consent_health_data": True})
    assert r.status_code == 422


def test_weak_passwords_rejected(client):
    assert signup(client, password="short1").status_code == 422
    assert signup(client, password="password1234").status_code == 422
    assert signup(client, password="sipho-sipho-1", email="sipho@example.com").status_code == 422


def test_duplicate_email_is_generic(client):
    auth(client)
    r = signup(client)
    assert r.status_code == 409 and "email" not in r.json()["detail"].lower()


def test_wrong_password_and_unknown_user_look_identical(client):
    auth(client)
    a = client.post("/auth/login", json={"email": "sipho@example.com", "password": "nope-nope-nope"})
    b = client.post("/auth/login", json={"email": "nobody@example.com", "password": "nope-nope-nope"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_lockout_after_repeated_failures(client):
    auth(client)
    for _ in range(5):
        assert client.post("/auth/login", json={"email": "sipho@example.com", "password": "bad-bad-bad-1"}).status_code == 401
    r = client.post("/auth/login", json={"email": "sipho@example.com", "password": "Correct-horse-9"})
    assert r.status_code == 429  # even the right password is refused while locked


def test_refresh_rotation_and_reuse_detection(client):
    h, t = auth(client)
    r1 = client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r1.status_code == 200
    new = r1.json()
    # Replaying the old token is treated as theft: the new token family dies too.
    assert client.post("/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer " + new["access_token"]}).status_code == 401


def test_logout_all_and_change_password_revoke_access(client):
    h, t = auth(client)
    assert client.post("/auth/logout-all", headers=h).status_code == 204
    assert client.get("/me", headers=h).status_code == 401
    r = client.post("/auth/login", json={"email": "sipho@example.com", "password": "Correct-horse-9"})
    h2 = {"Authorization": "Bearer " + r.json()["access_token"]}
    r = client.post("/auth/change-password", json={"current_password": "Correct-horse-9", "new_password": "Another-long-pw-7"}, headers=h2)
    assert r.status_code == 200
    assert client.get("/me", headers=h2).status_code == 401
    assert client.post("/auth/login", json={"email": "sipho@example.com", "password": "Another-long-pw-7"}).status_code == 200


def test_no_token_or_garbage_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_password_hash_is_argon2_and_never_plain(client, owner_engine):
    auth(client)
    with owner_engine.connect() as c:
        pw = c.execute(text("select password_hash from users")).scalar()
    assert pw.startswith("$argon2id$") and "Correct-horse-9" not in pw


def test_extra_fields_rejected(client):
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "Correct-horse-9", "date_of_birth": "1990-01-01",
                                          "accept_terms_privacy": True, "consent_health_data": True, "is_admin": True})
    assert r.status_code == 422


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"
