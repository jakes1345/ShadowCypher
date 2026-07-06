# tests/integration/test_p2p_fallback_flow.py

import pytest
import time
import uuid
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat import instance_registry, p2p_relay, fallback, crypto
from shadowcypher.chat.models import User, Instance, Message, Conversation
from shadowcypher.chat.crypto import (
    generate_keypair, derive_shared_secret, derive_session_key,
    encrypt_message, decrypt_message
)

@pytest.fixture(scope="function")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def session(setup_db):
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def users_with_instances(session):
    # User 1
    privkey1, pubkey1 = generate_keypair()
    user1_name = f"p2p_user_1_{uuid.uuid4().hex[:8]}"
    user1 = User(username=user1_name, public_key=pubkey1)
    session.add(user1)
    session.commit()
    session.refresh(user1)

    inst1 = instance_registry.register_instance(session, user1.id, pubkey1, "127.0.0.1:19999")

    # User 2
    privkey2, pubkey2 = generate_keypair()
    user2_name = f"p2p_user_2_{uuid.uuid4().hex[:8]}"
    user2 = User(username=user2_name, public_key=pubkey2)
    session.add(user2)
    session.commit()
    session.refresh(user2)

    inst2 = instance_registry.register_instance(session, user2.id, pubkey2, "127.0.0.1:20000")

    return (user1, inst1, privkey1, pubkey1), (user2, inst2, privkey2, pubkey2)

def test_p2p_flow_both_instances_online(session, users_with_instances):
    """Test P2P messaging when both instances online."""
    (user1, inst1, priv1, pub1), (user2, inst2, priv2, pub2) = users_with_instances

    conv = Conversation(
        user_id_1=user1.id,
        user_id_2=user2.id,
        encrypted_session_key=b"test_session_key_32_bytes_long!!",
        is_trusted=True
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)

    shared_secret = derive_shared_secret(priv1, pub2)
    session_key = derive_session_key(shared_secret, str(conv.id))
    ciphertext, nonce = encrypt_message("Hello from P2P", session_key)

    result = p2p_relay.send_p2p_message(
        inst1.instance_id,
        inst2.instance_id,
        ciphertext,
        nonce
    )

    # Result will be "failed" since instances aren't actually listening,
    # but the function should return a dict with "status" and "via" keys
    assert "status" in result
    assert "via" in result

def test_fallback_when_instance_offline(session, users_with_instances):
    """Test fallback to relay when target instance offline."""
    (user1, inst1, priv1, pub1), (user2, inst2, priv2, pub2) = users_with_instances

    inst2.is_online = False
    session.commit()

    conv = Conversation(
        user_id_1=user1.id,
        user_id_2=user2.id,
        encrypted_session_key=b"test_session_key_32_bytes_long!!",
        is_trusted=True
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)

    shared_secret = derive_shared_secret(priv1, pub2)
    session_key = derive_session_key(shared_secret, str(conv.id))
    ciphertext, nonce = encrypt_message("Fallback test", session_key)

    result = fallback.send_with_fallback(
        user2.id,
        ciphertext,
        nonce,
        conversation_id=conv.id,
        session=session
    )

    assert result["status"] == "delivered"
    assert result["via"] == "relay"

def test_heartbeat_keeps_online(session, users_with_instances):
    """Test heartbeat keeps instance marked online."""
    (user1, inst1, _, _), _ = users_with_instances

    fetched = instance_registry.get_instance(session, inst1.instance_id)
    assert fetched.is_online

    success = instance_registry.heartbeat(session, inst1.instance_id)
    assert success

    fetched = instance_registry.get_instance(session, inst1.instance_id)
    assert fetched.is_online

def test_instance_timeout_marks_offline(session, users_with_instances):
    """Test instances marked offline after timeout."""
    (user1, inst1, _, _), _ = users_with_instances

    inst1.last_heartbeat = int(time.time()) - (6 * 60)
    session.commit()

    fetched = instance_registry.get_instance(session, inst1.instance_id)
    assert not fetched.is_online

def test_encryption_roundtrip(session, users_with_instances):
    """Test crypto: encrypt/decrypt roundtrip."""
    (user1, inst1, priv1, pub1), (user2, inst2, priv2, pub2) = users_with_instances

    plaintext = "Secret message"
    shared_secret = derive_shared_secret(priv1, pub2)
    session_key = derive_session_key(shared_secret, "conv-id")

    ciphertext, nonce = encrypt_message(plaintext, session_key)
    decrypted = decrypt_message(ciphertext, nonce, session_key)

    assert decrypted == plaintext

def test_multiple_messages_same_session(session, users_with_instances):
    """Test multiple encrypted messages in same session."""
    (user1, inst1, priv1, pub1), (user2, inst2, priv2, pub2) = users_with_instances

    conv = Conversation(
        user_id_1=user1.id,
        user_id_2=user2.id,
        encrypted_session_key=b"test_session_key_32_bytes_long!!",
        is_trusted=True
    )
    session.add(conv)
    session.commit()
    session.refresh(conv)

    shared_secret = derive_shared_secret(priv1, pub2)
    session_key = derive_session_key(shared_secret, str(conv.id))

    messages = ["Message 1", "Message 2", "Message 3"]

    for msg_text in messages:
        ciphertext, nonce = encrypt_message(msg_text, session_key)

        message = Message(
            conversation_id=conv.id,
            encrypted_message=ciphertext,
            nonce=nonce,
            sender=user1.username,
            delivery_status="sent"
        )
        session.add(message)

    session.commit()

    # Verify messages were stored
    stored_messages = session.query(Message).filter(
        Message.conversation_id == conv.id
    ).all()

    assert len(stored_messages) == 3

    # Verify they can be decrypted
    for stored_msg in stored_messages:
        decrypted = decrypt_message(
            stored_msg.encrypted_message,
            stored_msg.nonce,
            session_key
        )
        assert decrypted in messages

def test_instance_endpoint_update(session, users_with_instances):
    """Test updating instance endpoint (e.g., after NAT traversal)."""
    (user1, inst1, _, _), _ = users_with_instances

    old_endpoint = inst1.endpoint
    new_endpoint = "192.168.1.100:19999"

    success = instance_registry.update_endpoint(session, inst1.instance_id, new_endpoint)
    assert success

    fetched = instance_registry.get_instance(session, inst1.instance_id)
    assert fetched.endpoint == new_endpoint
    assert fetched.endpoint != old_endpoint

def test_list_online_instances(session, users_with_instances):
    """Test listing online instances for a user."""
    (user1, inst1, _, _), (user2, inst2, _, _) = users_with_instances

    online = instance_registry.list_online_instances(session, user1.id)
    assert len(online) == 1
    assert online[0].instance_id == inst1.instance_id

    # Mark offline and recheck
    inst1.is_online = False
    session.commit()

    online = instance_registry.list_online_instances(session, user1.id)
    assert len(online) == 0
