"""Minimal FastAPI chat backend for ShadowCypher."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ShadowCypher Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://shadowcypher.site", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy data
ROOMS = [
    {"id": "global", "name": "global", "display_name": "Global", "room_type": "global", "team_id": None, "created_at": "2026-07-07T00:00:00Z"},
    {"id": "team-1", "name": "team-1", "display_name": "Team 1", "room_type": "team", "team_id": "team-1", "created_at": "2026-07-07T00:00:00Z"},
]

MESSAGES = [
    {"id": "1", "room_id": "global", "user_id": "test", "nick": "tester", "content": "Welcome to encrypted chat!", "created_at": "2026-07-07T03:00:00Z"},
    {"id": "2", "room_id": "global", "user_id": "test", "nick": "tester", "content": "Messages are AES-256-GCM encrypted", "created_at": "2026-07-07T03:01:00Z"},
]

PRESENCE = {}

@app.get("/v1/chat/rooms")
async def list_rooms():
    """List available chat rooms."""
    return {"rooms": ROOMS}

@app.get("/v1/chat/messages")
async def get_messages(room: str = "global", limit: int = 50, before: str = None):
    """Get message history for a room."""
    room_msgs = [m for m in MESSAGES if m["room_id"] == room]
    if before:
        room_msgs = [m for m in room_msgs if m["created_at"] < before]
    return {"room": room, "messages": room_msgs[-limit:]}

@app.post("/v1/chat/send")
async def send_message(body: dict):
    """Send a message to a room."""
    room = body.get("room", "global")
    content = body.get("content", "")
    if not content:
        return {"error": "content_required"}, 400
    msg = {
        "id": str(len(MESSAGES) + 1),
        "room_id": room,
        "user_id": "test",
        "nick": "tester",
        "content": content,
        "created_at": "2026-07-07T03:05:00Z"
    }
    MESSAGES.append(msg)
    return {"ok": True, "message": msg}

@app.post("/v1/chat/presence")
async def update_presence(body: dict):
    """Update user presence in a room."""
    room = body.get("room", "global")
    PRESENCE[room] = {"nick": "tester", "seen_at": "2026-07-07T03:05:00Z"}
    return {"ok": True}

@app.get("/v1/chat/online")
async def get_online_users(room: str = "global"):
    """Get online users in a room."""
    online = [PRESENCE.get(room, {"nick": "tester", "seen_at": "2026-07-07T03:05:00Z"})]
    return {"room": room, "online": online}

@app.get("/docs")
async def docs():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
