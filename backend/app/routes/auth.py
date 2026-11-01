import uuid
import re
from fastapi import APIRouter, HTTPException, Depends, status
from ..models import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    AuthResponse,
    UserResponse,
    MessageResponse,
    DemoCredentialsResponse
)
from ..database import get_db, get_iso_now
from ..auth import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_recovery_key,
    hash_recovery_key,
    verify_recovery_key,
    calculate_expiry,
    validate_password_strength,
    require_current_user,
    extract_token
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

DEMO_EMAIL = "demo@codewise.dev"
DEMO_PASSWORD = "DemoUser2026!"
DEMO_RECOVERY_KEY = "CW-DEMO-2026-RECOVER"

@router.get("/demo-credentials", response_model=DemoCredentialsResponse)
def get_demo_credentials():
    """Retrieve preconfigured demo credentials for immediate demonstration."""
    return DemoCredentialsResponse(
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        recovery_key=DEMO_RECOVERY_KEY
    )

@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Authenticate user with email and password."""
    email = req.email.strip().lower()
    if not email or not req.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address and password are required."
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, password_hash, created_at
            FROM users
            WHERE lower(email) = ?;
        """, (email,))
        user = cursor.fetchone()

        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please check your credentials."
            )

        token = generate_session_token()
        expires_at = calculate_expiry(remember_me=req.remember_me)
        now_ts = get_iso_now()

        cursor.execute("""
            INSERT INTO user_sessions (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?);
        """, (token, user["id"], expires_at, now_ts))

        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                created_at=user["created_at"]
            ),
            expires_at=expires_at
        )

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """Register a new user account with validation and local recovery key."""
    name = req.name.strip()
    email = req.email.strip().lower()

    if not name or len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters long."
        )

    if not email or not EMAIL_REGEX.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address."
        )

    pw_err = validate_password_strength(req.password)
    if pw_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err
        )

    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please verify your password."
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE lower(email) = ?;", (email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists. Please sign in instead."
            )

        user_id = str(uuid.uuid4())
        pw_hash = hash_password(req.password)
        recovery_key = generate_recovery_key()
        rec_hash = hash_recovery_key(recovery_key)
        now_ts = get_iso_now()

        cursor.execute("""
            INSERT INTO users (id, name, email, password_hash, recovery_key_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (user_id, name, email, pw_hash, rec_hash, now_ts, now_ts))

        # Create active session
        token = generate_session_token()
        expires_at = calculate_expiry(remember_me=True)

        cursor.execute("""
            INSERT INTO user_sessions (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?);
        """, (token, user_id, expires_at, now_ts))

        return AuthResponse(
            token=token,
            user=UserResponse(
                id=user_id,
                name=name,
                email=email,
                created_at=now_ts
            ),
            expires_at=expires_at,
            recovery_key=recovery_key
        )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: dict = Depends(require_current_user)):
    """Retrieve current authenticated user profile."""
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        created_at=user["created_at"]
    )

@router.post("/logout", response_model=MessageResponse)
def logout(user: dict = Depends(require_current_user)):
    """Sign out the current user and invalidate active session token."""
    token = user.get("session_token")
    if token:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_sessions WHERE token = ?;", (token,))
    return MessageResponse(message="Signed out successfully.")

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(req: ForgotPasswordRequest):
    """
    Reset account password using the local Security Recovery Key.
    Does not pretend to send emails if no email provider is configured.
    """
    email = req.email.strip().lower()
    recovery_key = req.recovery_key.strip()

    if not email or not recovery_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account email and Security Recovery Key are required."
        )

    pw_err = validate_password_strength(req.new_password)
    if pw_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err
        )

    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match."
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, recovery_key_hash
            FROM users
            WHERE lower(email) = ?;
        """, (email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address."
            )

        if not verify_recovery_key(recovery_key, user["recovery_key_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Security Recovery Key for this account."
            )

        new_pw_hash = hash_password(req.new_password)
        now_ts = get_iso_now()

        cursor.execute("""
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?;
        """, (new_pw_hash, now_ts, user["id"]))

        # Invalidate all prior sessions for security
        cursor.execute("DELETE FROM user_sessions WHERE user_id = ?;", (user["id"],))

        return MessageResponse(
            message="Your password has been successfully reset. You can now sign in with your new password."
        )

@router.get("/protected")
def protected_route_check(user: dict = Depends(require_current_user)):
    """Guard verification endpoint: confirms protected route cannot be accessed without authentication."""
    return {
        "status": "authenticated",
        "user_id": user["id"],
        "email": user["email"],
        "message": "Access granted to protected workspace resources."
    }
