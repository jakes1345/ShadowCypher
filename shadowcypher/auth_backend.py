"""Authentication backend with JWT and password hashing."""
from datetime import datetime, timedelta
from typing import Optional
import os
import secrets
import bcrypt
import jwt
from pydantic import BaseModel

# Secret key for JWT — MUST be set via SC_JWT_SECRET env var in production
JWT_SECRET = os.environ.get("SC_JWT_SECRET") or os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    import warnings
    JWT_SECRET = secrets.token_hex(32)  # Random per-process fallback — tokens won't survive restart
    warnings.warn(
        "SC_JWT_SECRET not set — using ephemeral random secret. Set SC_JWT_SECRET in production!",
        RuntimeWarning,
        stacklevel=1,
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

class User(BaseModel):
    id: str
    email: str
    username: str
    password_hash: str
    created_at: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str
    expires_in: int

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

class TokenPayload(BaseModel):
    sub: str  # user_id
    email: str
    username: str
    iat: int
    exp: int

# In-memory user store (replace with database) — intentionally empty on startup.
# Users registered here exist only for the lifetime of the process.
# For production, migrate to a persistent DB backend.
USERS_DB: dict[str, "User"] = {}

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hash: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hash.encode())

def create_jwt_token(user_id: str, email: str, username: str) -> tuple[str, int]:
    """Create JWT token."""
    now = datetime.utcnow()
    exp = now + timedelta(hours=JWT_EXPIRY_HOURS)

    payload = {
        "sub": user_id,
        "email": email,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    expires_in = int((exp - now).total_seconds())
    return token, expires_in

def verify_jwt_token(token: str) -> Optional[TokenPayload]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.InvalidTokenError:
        return None

def register_user(email: str, username: str, password: str) -> Optional[User]:
    """Register a new user."""
    # Check if user exists
    for user in USERS_DB.values():
        if user.email == email or user.username == username:
            return None

    user_id = secrets.token_hex(8)
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash=hash_password(password),
        created_at=datetime.utcnow().isoformat()
    )
    USERS_DB[user_id] = user
    return user

def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password."""
    for user in USERS_DB.values():
        if user.email == email and verify_password(password, user.password_hash):
            return user
    return None

def get_user(user_id: str) -> Optional[User]:
    """Get user by ID."""
    return USERS_DB.get(user_id)
