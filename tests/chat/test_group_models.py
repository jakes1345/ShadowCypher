import pytest
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat.models import User, Group, GroupMember, GroupMessage

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
    user = User(username="group_test_user", public_key=b"x"*32)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def test_create_group(session, test_user):
    group = Group(user_id=test_user.id, name="Test Group")
    session.add(group)
    session.commit()
    session.refresh(group)

    assert group.id is not None
    assert group.user_id == test_user.id
    assert group.name == "Test Group"
    assert group.group_key_version == 1

def test_add_group_member(session, test_user):
    group = Group(user_id=test_user.id, name="Test Group")
    session.add(group)
    session.commit()
    session.refresh(group)

    member = GroupMember(group_id=group.id, user_id=test_user.id)
    session.add(member)
    session.commit()
    session.refresh(member)

    assert member.group_id == group.id
    assert member.user_id == test_user.id

def test_add_group_message(session, test_user):
    group = Group(user_id=test_user.id, name="Test Group")
    session.add(group)
    session.commit()
    session.refresh(group)

    msg = GroupMessage(
        group_id=group.id,
        sender_id=test_user.id,
        encrypted_message=b"encrypted_text",
        nonce=b"nonce_96bit",
        group_key_version=1
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)

    assert msg.group_id == group.id
    assert msg.sender_id == test_user.id
    assert msg.encrypted_message == b"encrypted_text"

def test_group_key_version_tracking(session, test_user):
    group = Group(user_id=test_user.id, name="Version Test")
    session.add(group)
    session.commit()
    session.refresh(group)

    assert group.group_key_version == 1

    group.group_key_version = 2
    session.commit()
    session.refresh(group)

    assert group.group_key_version == 2
