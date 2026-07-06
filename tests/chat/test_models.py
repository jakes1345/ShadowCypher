import pytest
from shadowcypher.chat.models import User, Contact, Conversation, Message
from shadowcypher.chat.db import Base, engine

def test_user_model_creates_with_username_and_pubkey():
    """User model stores username and X25519 public key"""
    user = User(username="alice", public_key=b"x"*32)
    assert user.username == "alice"
    assert len(user.public_key) == 32

def test_contact_model_stores_user_and_fingerprint():
    """Contact links user to contact with fingerprint"""
    user = User(username="alice", public_key=b"x"*32)
    contact = Contact(user_id=user.id, contact_username="bob", contact_pubkey=b"y"*32, fingerprint="a3f7d2e1")
    assert contact.contact_username == "bob"
    assert contact.fingerprint == "a3f7d2e1"

def test_conversation_model_links_two_users():
    """Conversation stores encrypted session key and user pair"""
    user1 = User(username="alice", public_key=b"x"*32)
    user2 = User(username="bob", public_key=b"y"*32)
    conv = Conversation(user_id_1=user1.id, user_id_2=user2.id, encrypted_session_key=b"key")
    assert conv.user_id_1 == user1.id
    assert conv.user_id_2 == user2.id

def test_message_model_stores_encrypted_blob_and_metadata():
    """Message stores encrypted AES-GCM ciphertext, nonce, timestamp"""
    msg = Message(conversation_id=1, encrypted_message=b"ciphertext", nonce=b"nonce", sender="alice", timestamp=1234567890)
    assert msg.encrypted_message == b"ciphertext"
    assert msg.sender == "alice"
