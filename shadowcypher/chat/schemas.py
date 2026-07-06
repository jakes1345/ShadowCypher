from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    username: str
    public_key: str  # Hex-encoded 32 bytes

class RegisterResponse(BaseModel):
    user_id: int
    public_key: str
    token: str

class LoginRequest(BaseModel):
    username: str
    device_id: str

class LoginResponse(BaseModel):
    token: str

class AddContactRequest(BaseModel):
    contact_username: str
    contact_pubkey: str  # Hex-encoded
    fingerprint: str  # 8 chars

class AddContactResponse(BaseModel):
    contact_id: int
    contact_username: str

class SendMessageRequest(BaseModel):
    conversation_id: int
    encrypted_message: str  # Hex-encoded ciphertext
    nonce: str  # Hex-encoded nonce

class SendMessageResponse(BaseModel):
    message_id: int
    delivery_status: str

class ConversationSummary(BaseModel):
    conversation_id: int
    contact_username: str
    last_message: Optional[str]

class MessageResponse(BaseModel):
    id: int
    sender: str
    timestamp: int
    encrypted_message: str  # Hex-encoded
    nonce: str  # Hex-encoded

class InstanceRegisterRequest(BaseModel):
    public_key: str  # Hex-encoded X25519 pubkey
    endpoint: Optional[str] = None  # "IP:port" or "onion.local"

class InstanceResponse(BaseModel):
    instance_id: str
    public_key: str  # Hex
    endpoint: Optional[str]
    is_online: bool
    last_heartbeat: int
