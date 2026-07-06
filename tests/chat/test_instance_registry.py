import pytest
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat import instance_registry
from shadowcypher.chat.models import User, Instance
import time


@pytest.fixture
def session():
    """Create a fresh session for each test."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(session):
    """Create a test user."""
    user = User(username="test_user", public_key=b"x" * 32)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_register_instance(session, test_user):
    """Test registering a new Shadow instance."""
    pubkey = b"x" * 32  # 32-byte fake pubkey
    instance = instance_registry.register_instance(
        session, test_user.id, pubkey, "192.168.1.100:19999"
    )
    assert instance.instance_id is not None
    assert instance.user_id == test_user.id
    assert instance.public_key == pubkey
    assert instance.endpoint == "192.168.1.100:19999"
    assert instance.is_online


def test_heartbeat(session, test_user):
    """Test updating heartbeat for an instance."""
    pubkey = b"y" * 32
    instance = instance_registry.register_instance(session, test_user.id, pubkey)
    initial_hb = instance.last_heartbeat
    time.sleep(1.1)  # Sleep > 1 second to ensure timestamp increases
    success = instance_registry.heartbeat(session, instance.instance_id)
    assert success
    updated = instance_registry.get_instance(session, instance.instance_id)
    assert updated.last_heartbeat > initial_hb


def test_get_instance(session, test_user):
    """Test fetching instance by ID."""
    pubkey = b"z" * 32
    instance = instance_registry.register_instance(
        session, test_user.id, pubkey, "shadow.local"
    )
    fetched = instance_registry.get_instance(session, instance.instance_id)
    assert fetched.instance_id == instance.instance_id
    assert fetched.endpoint == "shadow.local"


def test_list_online_instances(session, test_user):
    """Test listing all online instances for a user."""
    pubkey1 = b"a" * 32
    pubkey2 = b"b" * 32
    instance_registry.register_instance(session, test_user.id, pubkey1, "instance1.local")
    instance_registry.register_instance(session, test_user.id, pubkey2, "instance2.local")
    online = instance_registry.list_online_instances(session, test_user.id)
    assert len(online) == 2
