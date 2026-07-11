from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    username: str
    public_key: str  # Hex-encoded 32 bytes
    password: Optional[str] = None  # Optional bcrypt-hashed password for login auth

class RegisterResponse(BaseModel):
    user_id: int
    public_key: str
    token: str

class LoginRequest(BaseModel):
    username: str
    password: str  # Plain-text password to be verified against bcrypt hash
    device_id: Optional[str] = "web"

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

class P2PSendRequest(BaseModel):
    to_instance_id: str
    encrypted_message: str  # hex-encoded ciphertext
    nonce: str  # hex-encoded nonce

class P2PSendResponse(BaseModel):
    status: str  # "delivered" | "failed"
    via: str  # "p2p" | "relay"

class GroupCreate(BaseModel):
    name: str

class GroupAddMember(BaseModel):
    user_id: int

class GroupResponse(BaseModel):
    id: str
    creator_id: int  # User ID of group creator
    name: str
    group_key: str  # Hex-encoded current 32-byte AES-256 key
    key_version: int  # Current key rotation version
    new_group_key_hex: Optional[str] = None  # Rotated key (null = no pending rotation, sent via P2P DM instead)
    created_at: int

class GroupMemberResponse(BaseModel):
    id: str
    user_id: int
    joined_at: int

class GroupMemberRemovalResponse(BaseModel):
    status: str  # "ok"
    new_key_version: int
    new_group_key_hex: str  # Creator gets new key to send to remaining members via P2P DM

class GroupMessageRequest(BaseModel):
    encrypted_message: str  # hex-encoded AES-256-GCM ciphertext
    nonce: str  # hex-encoded 96-bit nonce

class GroupMessageResponse(BaseModel):
    id: str
    group_id: str
    sender_id: int
    encrypted_message: str
    nonce: str
    created_at: int
    key_version: int

class VaultUnlockRequest(BaseModel):
    vault_password: str

class VaultUnlockResponse(BaseModel):
    status: str  # "unlocked"
    vault_key: str  # Derived from vault password using PBKDF2
