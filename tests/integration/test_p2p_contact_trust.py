# tests/integration/test_p2p_contact_trust.py
"""Tests for P2P route contact trust authorization."""

import pytest
import uuid
from fastapi.testclient import TestClient
from shadowcypher.main import app
from shadowcypher.chat.db import SessionLocal, engine, Base
from shadowcypher.chat.models import User, Contact, Instance
from shadowcypher.chat.crypto import generate_keypair
from shadowcypher.chat import instance_registry

client = TestClient(app)


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
def users_with_contacts_and_instances(session):
    """Create two users with a contact relationship and instances."""
    # User 1
    _, pubkey1 = generate_keypair()
    user1_name = f"test_user_1_{uuid.uuid4().hex[:8]}"

    user1_reg = client.post("/chat/register", json={
        "username": user1_name,
        "public_key": pubkey1.hex(),
    }).json()
    user1_token = user1_reg["token"]

    # Fetch user1 from DB
    user1 = session.query(User).filter(User.username == user1_name).first()
    inst1 = instance_registry.register_instance(session, user1.id, pubkey1, "127.0.0.1:19999")

    # User 2
    _, pubkey2 = generate_keypair()
    user2_name = f"test_user_2_{uuid.uuid4().hex[:8]}"

    user2_reg = client.post("/chat/register", json={
        "username": user2_name,
        "public_key": pubkey2.hex(),
    }).json()
    user2_token = user2_reg["token"]

    # Fetch user2 from DB
    user2 = session.query(User).filter(User.username == user2_name).first()
    inst2 = instance_registry.register_instance(session, user2.id, pubkey2, "127.0.0.1:20000")

    # User 3 (untrusted)
    _, pubkey3 = generate_keypair()
    user3_name = f"test_user_3_{uuid.uuid4().hex[:8]}"

    user3_reg = client.post("/chat/register", json={
        "username": user3_name,
        "public_key": pubkey3.hex(),
    }).json()
    user3_token = user3_reg["token"]

    # Fetch user3 from DB
    user3 = session.query(User).filter(User.username == user3_name).first()
    inst3 = instance_registry.register_instance(session, user3.id, pubkey3, "127.0.0.1:20001")

    # User1 adds User2 as trusted contact
    contact_1_to_2 = Contact(
        user_id=user1.id,
        contact_username=user2_name,
        contact_pubkey=pubkey2,
        fingerprint="abcd1234",
        is_trusted=True
    )
    session.add(contact_1_to_2)

    # User1 adds User3 as untrusted contact
    contact_1_to_3 = Contact(
        user_id=user1.id,
        contact_username=user3_name,
        contact_pubkey=pubkey3,
        fingerprint="efgh5678",
        is_trusted=False
    )
    session.add(contact_1_to_3)
    session.commit()

    return {
        "user1": (user1, inst1, user1_token, pubkey1),
        "user2": (user2, inst2, user2_token, pubkey2),
        "user3": (user3, inst3, user3_token, pubkey3),
    }


def test_send_p2p_to_trusted_contact_succeeds(users_with_contacts_and_instances):
    """POST /instances/send-p2p succeeds when target's owner is a trusted contact."""
    user1_data = users_with_contacts_and_instances["user1"]
    user2_data = users_with_contacts_and_instances["user2"]

    user1, inst1, user1_token, pubkey1 = user1_data
    user2, inst2, user2_token, pubkey2 = user2_data

    # User1 sends P2P message to User2's instance (User2 is trusted)
    response = client.post(
        "/chat/instances/send-p2p",
        json={
            "to_instance_id": inst2.instance_id,
            "encrypted_message": "abcd" * 16,  # 64 hex chars
            "nonce": "1234" * 3,  # 12 hex chars
        },
        headers={"Authorization": f"Bearer {user1_token}"}
    )

    # Should succeed (or at least not 403 due to trust)
    # It may fail with 500 if instances aren't listening, but trust check should pass
    assert response.status_code in [200, 500, 400], \
        f"Expected 200/500/400, got {response.status_code}: {response.text}"
    assert response.status_code != 403, "Should not get 403 (trust check should pass)"


def test_send_p2p_to_untrusted_contact_fails(users_with_contacts_and_instances):
    """POST /instances/send-p2p fails with 403 when target's owner is not trusted."""
    user1_data = users_with_contacts_and_instances["user1"]
    user3_data = users_with_contacts_and_instances["user3"]

    user1, inst1, user1_token, pubkey1 = user1_data
    user3, inst3, user3_token, pubkey3 = user3_data

    # User1 sends P2P message to User3's instance (User3 is NOT trusted)
    response = client.post(
        "/chat/instances/send-p2p",
        json={
            "to_instance_id": inst3.instance_id,
            "encrypted_message": "abcd" * 16,
            "nonce": "1234" * 3,
        },
        headers={"Authorization": f"Bearer {user1_token}"}
    )

    # Should fail with 403 because User3 is not a trusted contact
    assert response.status_code == 403
    assert "trusted contact" in response.json()["detail"]


def test_send_p2p_to_unknown_contact_fails(users_with_contacts_and_instances):
    """POST /instances/send-p2p fails with 403 when target's owner is not in contacts."""
    user1_data = users_with_contacts_and_instances["user1"]
    user2_data = users_with_contacts_and_instances["user2"]

    user1, inst1, user1_token, pubkey1 = user1_data
    user2, inst2, user2_token, pubkey2 = user2_data

    # Create a new user that user1 doesn't have as a contact
    _, pubkey_unknown = generate_keypair()
    unknown_name = f"unknown_{uuid.uuid4().hex[:8]}"

    unknown_reg = client.post("/chat/register", json={
        "username": unknown_name,
        "public_key": pubkey_unknown.hex(),
    }).json()

    # Get the instance for the unknown user
    session = SessionLocal()
    try:
        unknown_user = session.query(User).filter(User.username == unknown_name).first()
        unknown_inst = instance_registry.register_instance(
            session, unknown_user.id, pubkey_unknown, "127.0.0.1:20002"
        )
        unknown_inst_id = unknown_inst.instance_id
    finally:
        session.close()

    # User1 sends P2P message to unknown user's instance
    response = client.post(
        "/chat/instances/send-p2p",
        json={
            "to_instance_id": unknown_inst_id,
            "encrypted_message": "abcd" * 16,
            "nonce": "1234" * 3,
        },
        headers={"Authorization": f"Bearer {user1_token}"}
    )

    # Should fail with 403 because user is not in contacts
    assert response.status_code == 403
    assert "trusted contact" in response.json()["detail"]


def test_send_p2p_nonexistent_instance_fails(users_with_contacts_and_instances):
    """POST /instances/send-p2p fails with 404 when instance doesn't exist."""
    user1_data = users_with_contacts_and_instances["user1"]
    user1, inst1, user1_token, pubkey1 = user1_data

    fake_instance_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        "/chat/instances/send-p2p",
        json={
            "to_instance_id": fake_instance_id,
            "encrypted_message": "abcd" * 16,
            "nonce": "1234" * 3,
        },
        headers={"Authorization": f"Bearer {user1_token}"}
    )

    # Should fail with 404 instance not found
    assert response.status_code == 404
    assert "instance" in response.json()["detail"].lower()
