from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from shadowcypher.chat.models import User, Contact, Conversation, Message
from shadowcypher.chat.auth import create_jwt_token, validate_jwt_token
from shadowcypher.chat.crypto import fingerprint
from shadowcypher.chat.schemas import (
    RegisterRequest, RegisterResponse, LoginRequest, LoginResponse,
    AddContactRequest, AddContactResponse, SendMessageRequest, SendMessageResponse,
    ConversationSummary, MessageResponse
)
from shadowcypher.chat.db import SessionLocal
from datetime import datetime
import binascii
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Extract user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ")[1]
    try:
        claims = validate_jwt_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    user = db.query(User).filter(User.id == claims["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register new user with X25519 public key"""
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        public_key = binascii.unhexlify(request.public_key)
        if len(public_key) != 32:
            raise ValueError()
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="Invalid public key (must be 64 hex chars)")

    user = User(username=request.username, public_key=public_key)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_jwt_token(user.id, user.username, "web")

    return RegisterResponse(
        user_id=user.id,
        public_key=request.public_key,
        token=token
    )

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username")

    token = create_jwt_token(user.id, user.username, request.device_id)
    return LoginResponse(token=token)

@router.post("/add-contact", response_model=AddContactResponse, status_code=201)
def add_contact(
    request: AddContactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add contact to user's contact list"""
    try:
        contact_pubkey = binascii.unhexlify(request.contact_pubkey)
        if len(contact_pubkey) != 32:
            raise ValueError()
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="Invalid public key")

    # Find the contact user by username
    contact_user = db.query(User).filter(User.username == request.contact_username).first()
    if not contact_user:
        raise HTTPException(status_code=404, detail="Contact user not found")

    contact = Contact(
        user_id=current_user.id,
        contact_username=request.contact_username,
        contact_pubkey=contact_pubkey,
        fingerprint=request.fingerprint,
        is_trusted=False
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    # Create conversation between current user and contact user
    existing_conv = db.query(Conversation).filter(
        ((Conversation.user_id_1 == current_user.id) & (Conversation.user_id_2 == contact_user.id)) |
        ((Conversation.user_id_1 == contact_user.id) & (Conversation.user_id_2 == current_user.id))
    ).first()

    if not existing_conv:
        # Create empty encrypted session key as placeholder
        conversation = Conversation(
            user_id_1=current_user.id,
            user_id_2=contact_user.id,
            encrypted_session_key=b'\x00' * 32  # Placeholder
        )
        db.add(conversation)
        db.commit()

    return AddContactResponse(
        contact_id=contact.id,
        contact_username=contact.contact_username
    )

@router.post("/send-message", response_model=SendMessageResponse, status_code=201)
def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send encrypted message in conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        ciphertext = binascii.unhexlify(request.encrypted_message)
        nonce = binascii.unhexlify(request.nonce)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="Invalid message encoding")

    message = Message(
        conversation_id=request.conversation_id,
        encrypted_message=ciphertext,
        nonce=nonce,
        sender=current_user.username,
        delivery_status="sent"
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return SendMessageResponse(
        message_id=message.id,
        delivery_status=message.delivery_status
    )

@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's conversations"""
    conversations = db.query(Conversation).filter(
        (Conversation.user_id_1 == current_user.id) |
        (Conversation.user_id_2 == current_user.id)
    ).all()

    result = []
    for conv in conversations:
        other_user_id = conv.user_id_2 if conv.user_id_1 == current_user.id else conv.user_id_1
        other_user = db.query(User).filter(User.id == other_user_id).first()

        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.timestamp.desc()).first()

        result.append(ConversationSummary(
            conversation_id=conv.id,
            contact_username=other_user.username if other_user else "unknown",
            last_message=last_msg.sender if last_msg else None
        ))

    return result

@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get encrypted messages in conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.timestamp.asc()).all()

    return [
        MessageResponse(
            id=msg.id,
            sender=msg.sender,
            timestamp=int(msg.timestamp.timestamp()),
            encrypted_message=binascii.hexlify(msg.encrypted_message).decode(),
            nonce=binascii.hexlify(msg.nonce).decode()
        )
        for msg in messages
    ]
