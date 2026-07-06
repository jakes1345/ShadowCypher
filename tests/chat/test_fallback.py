# tests/chat/test_fallback.py

import pytest
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat import fallback
from shadowcypher.chat.models import User, Conversation, Message


@pytest.fixture(scope="module")
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
def test_users(session):
    user1 = User(username="fallback_user_1", public_key=b'\x00' * 32)
    user2 = User(username="fallback_user_2", public_key=b'\x01' * 32)
    session.add(user1)
    session.add(user2)
    session.commit()
    session.refresh(user1)
    session.refresh(user2)
    return user1, user2


def test_fallback_relay_no_p2p(session, test_users):
    """Fallback to relay when P2P not available (Phase 1 scenario)."""
    user1, user2 = test_users
    conv = Conversation(user_id_1=user1.id, user_id_2=user2.id, encrypted_session_key=b'\x00' * 32, is_trusted=True)
    session.add(conv)
    session.commit()
    session.refresh(conv)

    result = fallback.send_with_fallback(
        user2.id,
        b"encrypted_msg",
        b"nonce123",
        conversation_id=conv.id,
        session=session
    )

    assert result["via"] == "relay"
    assert result["status"] == "delivered"


def test_fallback_message_stored(session, test_users):
    """Fallback stores message in queue when P2P unavailable."""
    user1, user2 = test_users
    conv = Conversation(user_id_1=user1.id, user_id_2=user2.id, encrypted_session_key=b'\x00' * 32, is_trusted=True)
    session.add(conv)
    session.commit()
    session.refresh(conv)

    fallback.send_with_fallback(
        user2.id,
        b"test_message",
        b"nonce456",
        conversation_id=conv.id,
        session=session
    )

    # Verify message was stored
    msg = session.query(Message).filter(Message.conversation_id == conv.id).first()
    assert msg is not None
    assert msg.encrypted_message == b"test_message"
    assert msg.nonce == b"nonce456"
