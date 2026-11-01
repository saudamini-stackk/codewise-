import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db

client = TestClient(app)

def test_demo_account_seeded():
    """Verify preconfigured demo account exists in database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM users WHERE lower(email) = 'demo@codewise.dev';")
        user = cursor.fetchone()
        assert user is not None
        assert user["name"] == "Demo Developer"
        assert user["email"] == "demo@codewise.dev"

def test_demo_credentials_endpoint():
    """Verify demo credentials endpoint returns valid credentials for demo ease."""
    res = client.get("/api/auth/demo-credentials")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "demo@codewise.dev"
    assert data["password"] == "DemoUser2026!"
    assert "CW-DEMO" in data["recovery_key"]

def test_login_successful_with_demo_account():
    """Test successful login with the preconfigured demo account."""
    payload = {
        "email": "demo@codewise.dev",
        "password": "DemoUser2026!",
        "remember_me": True
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert len(data["token"]) == 64
    assert data["user"]["email"] == "demo@codewise.dev"
    assert data["user"]["name"] == "Demo Developer"

def test_login_incorrect_password():
    """Test login rejection when password is wrong."""
    payload = {
        "email": "demo@codewise.dev",
        "password": "WrongPassword123!"
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_login_nonexistent_email():
    """Test login rejection for unknown email."""
    payload = {
        "email": "unknown_user_999@test.com",
        "password": "Password123!"
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_protected_routes_without_token():
    """Verify protected endpoints return 401 when unauthenticated."""
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 401

    res_prot = client.get("/api/auth/protected")
    assert res_prot.status_code == 401

def test_protected_routes_with_valid_token():
    """Verify protected endpoints return 200 with user context when token is supplied."""
    login_res = client.post("/api/auth/login", json={
        "email": "demo@codewise.dev",
        "password": "DemoUser2026!"
    })
    token = login_res.json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "demo@codewise.dev"

    prot_res = client.get("/api/auth/protected", headers=headers)
    assert prot_res.status_code == 200
    assert prot_res.json()["status"] == "authenticated"

def test_register_new_user_and_login():
    """Test registering a new account, checking recovery key and signing in."""
    new_email = "alice@university.edu"
    payload = {
        "name": "Alice Developer",
        "email": new_email,
        "password": "AlicePassword2026!",
        "confirm_password": "AlicePassword2026!"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == new_email
    assert data["user"]["name"] == "Alice Developer"
    assert "recovery_key" in data
    assert data["recovery_key"].startswith("CW-")

    # Login with new credentials
    login_res = client.post("/api/auth/login", json={
        "email": new_email,
        "password": "AlicePassword2026!"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == new_email

def test_register_duplicate_email():
    """Test that duplicate registration with existing email is rejected."""
    payload = {
        "name": "Duplicate Demo",
        "email": "demo@codewise.dev",
        "password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

def test_register_weak_password():
    """Test validation of short or weak passwords."""
    payload = {
        "name": "Bob",
        "email": "bob@example.com",
        "password": "short",
        "confirm_password": "short"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "at least 8 characters" in res.json()["detail"]

def test_forgot_password_reset_flow():
    """Test the complete password reset flow using the Security Recovery Key."""
    # 1. Create a user
    user_email = "charlie@college.edu"
    reg_res = client.post("/api/auth/register", json={
        "name": "Charlie",
        "email": user_email,
        "password": "OriginalPassword123!",
        "confirm_password": "OriginalPassword123!"
    })
    assert reg_res.status_code == 200
    recovery_key = reg_res.json()["recovery_key"]

    # 2. Reset password using recovery key
    reset_payload = {
        "email": user_email,
        "recovery_key": recovery_key,
        "new_password": "BrandNewPassword2026!",
        "confirm_password": "BrandNewPassword2026!"
    }
    reset_res = client.post("/api/auth/forgot-password", json=reset_payload)
    assert reset_res.status_code == 200
    assert "successfully reset" in reset_res.json()["message"]

    # 3. Old password fails
    old_login = client.post("/api/auth/login", json={
        "email": user_email,
        "password": "OriginalPassword123!"
    })
    assert old_login.status_code == 401

    # 4. New password succeeds
    new_login = client.post("/api/auth/login", json={
        "email": user_email,
        "password": "BrandNewPassword2026!"
    })
    assert new_login.status_code == 200
    assert new_login.json()["user"]["email"] == user_email

def test_forgot_password_invalid_recovery_key():
    """Test rejection when wrong recovery key is provided."""
    reset_payload = {
        "email": "demo@codewise.dev",
        "recovery_key": "CW-WRONG-KEY",
        "new_password": "NewValidPassword123!",
        "confirm_password": "NewValidPassword123!"
    }
    res = client.post("/api/auth/forgot-password", json=reset_payload)
    assert res.status_code == 400
    assert "Invalid Security Recovery Key" in res.json()["detail"]

def test_logout_invalidates_session():
    """Test that logging out removes active session from user_sessions."""
    # Login
    login_res = client.post("/api/auth/login", json={
        "email": "demo@codewise.dev",
        "password": "DemoUser2026!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify active
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Logout
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Subsequent request with same token fails
    me_res_after = client.get("/api/auth/me", headers=headers)
    assert me_res_after.status_code == 401
