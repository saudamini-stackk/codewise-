import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from .database import get_db, get_iso_now

PBKDF2_ITERATIONS = 100000
DEFAULT_SESSION_DAYS = 7
REMEMBER_ME_DAYS = 30

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a unique salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${key}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2 hash using timing-safe comparison."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = parts[3]
        
        computed_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        ).hex()
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False

def generate_recovery_key() -> str:
    """Generate a clean, copyable recovery key for local account recovery."""
    p1 = secrets.token_hex(3).upper()
    p2 = secrets.token_hex(3).upper()
    return f"CW-{p1}-{p2}"

def hash_recovery_key(recovery_key: str) -> str:
    """Hash recovery key with SHA256 for secure storage."""
    clean = recovery_key.strip().upper()
    return hashlib.sha256(clean.encode('utf-8')).hexdigest()

def verify_recovery_key(recovery_key: str, hashed_key: str) -> bool:
    """Verify recovery key using timing-safe comparison."""
    try:
        clean = recovery_key.strip().upper()
        computed = hashlib.sha256(clean.encode('utf-8')).hexdigest()
        return hmac.compare_digest(computed, hashed_key)
    except Exception:
        return False

def generate_session_token() -> str:
    """Generate cryptographically secure 256-bit session token."""
    return secrets.token_hex(32)

def calculate_expiry(remember_me: bool = False) -> str:
    """Calculate expiration ISO timestamp."""
    days = REMEMBER_ME_DAYS if remember_me else DEFAULT_SESSION_DAYS
    expiry = datetime.now(timezone.utc) + timedelta(days=days)
    return expiry.isoformat()

def validate_password_strength(password: str) -> Optional[str]:
    """Validate password requirements."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(c.isalpha() for c in password):
        return "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number."
    return None

def extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    # Also support X-Session-Token header
    token = request.headers.get("X-Session-Token")
    if token:
        return token.strip()
    return None

def get_current_user(request: Request, required: bool = True) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to authenticate the user from session token.
    Raises 401 if required and token is missing, invalid or expired.
    """
    token = extract_token(request)
    if not token:
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return None

    now_iso = get_iso_now()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.token, s.user_id, s.expires_at,
                   u.id, u.name, u.email, u.created_at
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now_iso))
        row = cursor.fetchone()

        if not row:
            if required:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired or invalid. Please sign in again.",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "created_at": row["created_at"],
            "session_token": row["token"]
        }

def require_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency for strictly protected routes."""
    return get_current_user(request, required=True)

def optional_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for optionally protected routes."""
    return get_current_user(request, required=False)
