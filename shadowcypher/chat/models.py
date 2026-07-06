from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

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
