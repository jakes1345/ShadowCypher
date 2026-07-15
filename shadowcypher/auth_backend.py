"""Authentication backend with JWT and password hashing."""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from pydantic import BaseModel


def _load_or_create_jwt_secret() -> str:
    """Load JWT secret from env, then from file, else generate and persist."""
    val = os.environ.get("SC_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if val:
        return val
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    secret_path = os.path.join(xdg, "shadowcypher", "jwt.secret")
    if os.path.exists(secret_path):
        try:
            with open(secret_path) as f:
                stored = f.read().strip()
            if stored:
                return stored
        except Exception:
            pass
    new_secret = secrets.token_hex(32)
    try:
        os.makedirs(os.path.dirname(secret_path), exist_ok=True)
        with open(secret_path, "w") as f:
            f.write(new_secret)
        os.chmod(secret_path, 0o600)
    except Exception:
        import warnings
        warnings.warn(
            "SC_JWT_SECRET not set and could not persist secret to disk — tokens won't survive restart.",
            RuntimeWarning,
            stacklevel=2,
        )
    return new_secret

# Secret key for JWT — set SC_JWT_SECRET env var or it persists to ~/.config/shadowcypher/jwt.secret
JWT_SECRET = _load_or_create_jwt_secret()
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
