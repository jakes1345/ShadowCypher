"""FastAPI chat backend with authentication and AES-256-GCM encryption."""
import secrets
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shadowcypher.auth_backend import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    authenticate_user,
    create_jwt_token,
    register_user,
    verify_jwt_token,
)
from shadowcypher.crypto_backend import create_group_key, rotate_and_store_group_key, store_user_key

app = FastAPI(title="ShadowCypher Chat")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with proper JSON serialization."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://shadowcypher.site", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class EncryptedChatMessage(BaseModel):
    room: str
    ciphertext: str
    nonce: str
    tag: str

# Data stores
ROOMS = [
    {"id": "global", "name": "global", "display_name": "Global", "room_type": "global", "team_id": None, "created_at": "2026-07-07T00:00:00Z"},
]
MESSAGES = []
PRESENCE = {}

def get_current_user(authorization: str = Header(None)):
    """Extract and verify JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    token = authorization[7:]  # Remove "Bearer " prefix
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# Authentication endpoints
@app.post("/v1/auth/register")
async def register(req: RegisterRequest):
    """Register a new user."""
    try:
        user = register_user(req.email, req.username, req.password)
        if not user:
            raise HTTPException(status_code=400, detail="User already exists")

        # Store encryption key derived from password
        store_user_key(user.id, req.password)

        # Create JWT token
        token, expires_in = create_jwt_token(user.id, user.email, user.username)

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            expires_in=expires_in
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}") from e

@app.post("/v1/auth/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT token."""
    try:
        user = authenticate_user(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token, expires_in = create_jwt_token(user.id, user.email, user.username)

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.id,
            username=user.username,
            expires_in=expires_in
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}") from e

# Chat endpoints (protected)
@app.get("/v1/chat/rooms")
async def list_rooms(authorization: str = Header(None)):
    """List available chat rooms."""
    get_current_user(authorization)
    return {"rooms": ROOMS}

@app.get("/v1/chat/messages")
async def get_messages(room: str = "global", limit: int = 50, before: str = None, authorization: str = Header(None)):
    """Get encrypted message history for a room."""
    get_current_user(authorization)
    room_msgs = [m for m in MESSAGES if m["room_id"] == room]
    if before:
        room_msgs = [m for m in room_msgs if m["created_at"] < before]
    return {"room": room, "messages": room_msgs[-limit:]}

@app.post("/v1/chat/send")
async def send_message(msg: EncryptedChatMessage, authorization: str = Header(None)):
    """Send an encrypted message to a room."""
    user = get_current_user(authorization)

    message = {
        "id": secrets.token_hex(8),
        "room_id": msg.room,
        "user_id": user.sub,
        "username": user.username,
        "ciphertext": msg.ciphertext,
        "nonce": msg.nonce,
        "tag": msg.tag,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    MESSAGES.append(message)
    return {"ok": True, "message": message}

@app.post("/v1/chat/presence")
async def update_presence(body: dict, authorization: str = Header(None)):
    """Update user presence in a room."""
    user = get_current_user(authorization)
    room = body.get("room", "global")
    PRESENCE[room] = {"user_id": user.sub, "username": user.username, "seen_at": datetime.utcnow().isoformat() + "Z"}
    return {"ok": True}

@app.get("/v1/chat/online")
async def get_online_users(room: str = "global", authorization: str = Header(None)):
    """Get online users in a room."""
    get_current_user(authorization)
    online_users = [p for p in PRESENCE.values() if p.get("seen_at")]
    return {"room": room, "online": online_users}

# Group encryption endpoints
@app.post("/v1/chat/groups")
async def create_group(body: dict, authorization: str = Header(None)):
    """Create an encrypted group chat."""
    user = get_current_user(authorization)
    group_id = secrets.token_hex(8)
    create_group_key(group_id)

    group = {
        "id": group_id,
        "name": body.get("name", f"group-{group_id}"),
        "creator_id": user.sub,
        "members": [user.sub],
        "key_version": 1,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    ROOMS.append(group)
    return {"ok": True, "group": group}

@app.post("/v1/chat/groups/{group_id}/rotate-key")
async def rotate_group_key(group_id: str, authorization: str = Header(None)):
    """Rotate encryption key when member is removed."""
    get_current_user(authorization)
    rotate_and_store_group_key(group_id)
    return {"ok": True, "message": "Key rotated"}

@app.get("/docs")
async def docs():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
