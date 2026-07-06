import pytest
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat import instance_registry, p2p_relay
from shadowcypher.chat.models import User, Instance, P2PConnection

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
def test_user(session):
    user = User(username="p2p_test_user", public_key=b"u" * 32)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture
def instances(session, test_user):
    pubkey1 = b"p2p_a" * 6 + b"aa"  # 32 bytes
    pubkey2 = b"p2p_b" * 6 + b"bb"  # 32 bytes
    inst1 = instance_registry.register_instance(session, test_user.id, pubkey1, "127.0.0.1:19999")
    inst2 = instance_registry.register_instance(session, test_user.id, pubkey2, "127.0.0.1:20000")
    return inst1, inst2

def test_p2p_message_serialization():
    """Test P2PMessage JSON serialization."""
    ciphertext = b"encrypted_data"
    nonce = b"nonce_123456789"
    msg = p2p_relay.P2PMessage("inst1", "inst2", ciphertext, nonce)
    json_str = msg.to_json()

    # Deserialize
    msg2 = p2p_relay.P2PMessage.from_json(json_str)
    assert msg2.from_instance_id == "inst1"
    assert msg2.to_instance_id == "inst2"
    assert msg2.ciphertext == ciphertext
    assert msg2.nonce == nonce

def test_send_p2p_offline_instance(session, instances):
    """P2P send to offline instance should fail gracefully."""
    inst1, inst2 = instances
    inst2.is_online = False
    session.commit()

    result = p2p_relay.send_p2p_message(inst1.instance_id, inst2.instance_id, b"msg", b"nonce")
    assert result["status"] == "failed"
