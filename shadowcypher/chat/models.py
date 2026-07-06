from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import time
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    public_key = Column(LargeBinary(32), nullable=False)  # X25519 pubkey
    created_date = Column(DateTime, default=datetime.utcnow)

    contacts = relationship("Contact", back_populates="user")
    conversations_as_user1 = relationship("Conversation", foreign_keys="Conversation.user_id_1", back_populates="user1")
    conversations_as_user2 = relationship("Conversation", foreign_keys="Conversation.user_id_2", back_populates="user2")

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_username = Column(String(255), nullable=False)
    contact_pubkey = Column(LargeBinary(32), nullable=False)
    fingerprint = Column(String(8), nullable=False)  # SHA256(pubkey)[:8]
    is_trusted = Column(Boolean, default=False)
    added_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="contacts")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id_1 = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_id_2 = Column(Integer, ForeignKey("users.id"), nullable=False)
    encrypted_session_key = Column(LargeBinary, nullable=False)  # AES-256 encrypted
    last_message_timestamp = Column(DateTime, default=datetime.utcnow)
    is_trusted = Column(Boolean, default=False)

    user1 = relationship("User", foreign_keys=[user_id_1], back_populates="conversations_as_user1")
    user2 = relationship("User", foreign_keys=[user_id_2], back_populates="conversations_as_user2")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    encrypted_message = Column(LargeBinary, nullable=False)  # AES-256-GCM ciphertext
    nonce = Column(LargeBinary(12), nullable=False)  # GCM nonce
    sender = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    delivery_status = Column(String(20), default="pending")  # "pending", "sent", "delivered"

    conversation = relationship("Conversation", back_populates="messages")

class Instance(Base):
    """Shadow instance registry for P2P discovery."""
    __tablename__ = "instances"

    instance_id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    public_key = Column(LargeBinary, nullable=False)  # X25519 pubkey (32 bytes)
    endpoint = Column(String(255), nullable=True)  # "IP:port" or "onion.local" or None
    last_heartbeat = Column(Integer, nullable=False)  # Unix timestamp
    is_online = Column(Boolean, default=True, nullable=False)
    created_at = Column(Integer, nullable=False)

    def __init__(self, user_id, pubkey, endpoint=None):
        self.instance_id = str(uuid.uuid4())
        self.user_id = user_id
        self.public_key = pubkey
        self.endpoint = endpoint
        self.last_heartbeat = int(time.time())
        self.is_online = True
        self.created_at = int(time.time())

class P2PConnection(Base):
    """Tracks active P2P connections between instances."""
    __tablename__ = "p2p_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_instance_id = Column(String(36), ForeignKey("instances.instance_id"), nullable=False)
    to_instance_id = Column(String(36), ForeignKey("instances.instance_id"), nullable=False)
    status = Column(String(20), nullable=False)  # "active", "closed", "failed"
    created_at = Column(Integer, nullable=False)
    last_activity = Column(Integer, nullable=False)
    messages_sent = Column(Integer, default=0, nullable=False)
