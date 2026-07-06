import pytest
import os
import time
from fastapi.testclient import TestClient
from shadowcypher.main import app
from shadowcypher.chat.crypto import generate_keypair
from shadowcypher.chat.group_crypto import encrypt_group_message, decrypt_group_message
from shadowcypher.chat.db import SessionLocal, engine, Base

client = TestClient(app)

# ─── Database Setup ───

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Create fresh test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ─── Test Fixtures ───

class UserFixture:
    """Hold user data during test"""
    def __init__(self, username, user_id, token, public_key, private_key):
        self.username = username
        self.user_id = user_id
        self.token = token
        self.public_key = public_key
        self.private_key = private_key


def create_and_register_user(username):
    """Register user and return user fixture"""
    priv, pub = generate_keypair()

    # Use unique username with timestamp to avoid conflicts between test runs
    unique_username = f"{username}_{int(time.time() * 1000000)}"

    response = client.post("/chat/register", json={
        "username": unique_username,
        "public_key": pub.hex(),
    })
    assert response.status_code == 201, f"Failed to register user: {response.text}"
    data = response.json()

    return UserFixture(
        username=unique_username,
        user_id=data["user_id"],
        token=data["token"],
        public_key=pub,
        private_key=priv
    )


def create_group(user, name):
    """Create group and return group data with group_key"""
    response = client.post(
        "/chat/groups",
        json={"name": name},
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 201
    group_data = response.json()

    # Generate group_key (32 bytes) for encryption
    # In production, creator would generate this and distribute via DM
    # For testing, we generate it once and track it
    group_key = os.urandom(32)

    return {
        "id": group_data["id"],
        "user_id": group_data["user_id"],
        "name": group_data["name"],
        "group_key_version": group_data["group_key_version"],
        "created_at": group_data["created_at"],
        "group_key": group_key,  # Track for test
    }


def add_member(user, group_id, member_user_id):
    """Add member to group (creator-only)"""
    response = client.post(
        f"/chat/groups/{group_id}/members",
        json={"user_id": member_user_id},
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 201
    return response.json()


def remove_member(user, group_id, member_id):
    """Remove member from group (triggers key rotation)"""
    # First, we need to find the member ID from the member_id we're trying to remove
    # Actually, looking at the routes, we need the member's ID from GroupMember model
    # Let me get the members first to find the right ID
    response = client.delete(
        f"/chat/groups/{group_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
    return response.json()


def send_group_message(user, group_id, encrypted_message, nonce):
    """Send encrypted message to group"""
    response = client.post(
        f"/chat/groups/{group_id}/messages",
        json={
            "encrypted_message": encrypted_message.hex(),
            "nonce": nonce.hex(),
        },
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 201
    return response.json()


def fetch_group_messages(user, group_id):
    """Fetch all group messages"""
    response = client.get(
        f"/chat/groups/{group_id}/messages",
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
    return response.json()


def get_group(user, group_id):
    """Fetch group metadata"""
    # Note: There's no direct GET endpoint for groups in the routes
    # We'll fetch via list_group_members to get members, but we need to query DB directly
    # For now, we'll track group state in the test
    # This would require a GET /groups/{group_id} endpoint which doesn't exist yet
    pass


def list_members(user, group_id):
    """Fetch group member list"""
    response = client.get(
        f"/chat/groups/{group_id}/members",
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
    return response.json()


def delete_group(user, group_id):
    """Delete group (creator-only)"""
    response = client.delete(
        f"/chat/groups/{group_id}",
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 200
    return response.json()


def get_group_key_version(group_id):
    """Query group key version from database"""
    from shadowcypher.chat.models import Group
    db = SessionLocal()
    try:
        group = db.query(Group).filter(Group.id == group_id).first()
        return group.group_key_version if group else None
    finally:
        db.close()


def get_group_member_id(group_id, user_id):
    """Query group member ID from database"""
    from shadowcypher.chat.models import GroupMember
    db = SessionLocal()
    try:
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        ).first()
        return member.id if member else None
    finally:
        db.close()


# ─── E2E Test ───

def test_group_e2e_flow():
    """E2E: create group → add members → send encrypted messages → decrypt by recipients + key rotation"""

    # ─── Step 1: Register 3 users ───
    alice = create_and_register_user("alice")
    bob = create_and_register_user("bob")
    charlie = create_and_register_user("charlie")

    assert alice.user_id is not None
    assert bob.user_id is not None
    assert charlie.user_id is not None
    assert alice.user_id != bob.user_id != charlie.user_id

    # ─── Step 2: Alice creates group "Team Vault" ───
    group = create_group(alice, name="Team Vault")
    assert group["user_id"] == alice.user_id
    assert group["group_key_version"] == 1
    assert group["name"] == "Team Vault"
    assert len(group["group_key"]) == 32  # Group key is 32 bytes

    # ─── Step 3: Alice adds Bob and Charlie to group ───
    add_member(alice, group_id=group["id"], member_user_id=bob.user_id)
    add_member(alice, group_id=group["id"], member_user_id=charlie.user_id)

    # Alice must be added as well (creator is a member)
    add_member(alice, group_id=group["id"], member_user_id=alice.user_id)

    # Verify membership
    members = list_members(alice, group_id=group["id"])
    assert len(members) == 3
    member_user_ids = {m["user_id"] for m in members}
    assert member_user_ids == {alice.user_id, bob.user_id, charlie.user_id}

    # ─── Step 4: Alice sends encrypted message ───
    alice_msg = "Secret group strategy"
    ciphertext_alice, nonce_alice = encrypt_group_message(
        alice_msg,
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=group["group_key_version"]
    )
    send_group_message(alice, group_id=group["id"], encrypted_message=ciphertext_alice, nonce=nonce_alice)

    # ─── Step 5: Bob sends encrypted message ───
    bob_msg = "Agreed, let's execute"
    ciphertext_bob, nonce_bob = encrypt_group_message(
        bob_msg,
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=group["group_key_version"]
    )
    send_group_message(bob, group_id=group["id"], encrypted_message=ciphertext_bob, nonce=nonce_bob)

    # ─── Step 6: All members fetch and decrypt messages ───
    # Alice fetches messages
    alice_messages = fetch_group_messages(alice, group_id=group["id"])
    assert len(alice_messages) == 2

    # Alice decrypts both messages
    alice_decrypted_1 = decrypt_group_message(
        bytes.fromhex(alice_messages[0]["encrypted_message"]),
        bytes.fromhex(alice_messages[0]["nonce"]),
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=alice_messages[0]["group_key_version"]
    )
    assert alice_decrypted_1 == alice_msg

    alice_decrypted_2 = decrypt_group_message(
        bytes.fromhex(alice_messages[1]["encrypted_message"]),
        bytes.fromhex(alice_messages[1]["nonce"]),
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=alice_messages[1]["group_key_version"]
    )
    assert alice_decrypted_2 == bob_msg

    # Bob fetches and decrypts messages
    bob_messages = fetch_group_messages(bob, group_id=group["id"])
    assert len(bob_messages) == 2

    bob_decrypted_1 = decrypt_group_message(
        bytes.fromhex(bob_messages[0]["encrypted_message"]),
        bytes.fromhex(bob_messages[0]["nonce"]),
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=bob_messages[0]["group_key_version"]
    )
    assert bob_decrypted_1 == alice_msg

    bob_decrypted_2 = decrypt_group_message(
        bytes.fromhex(bob_messages[1]["encrypted_message"]),
        bytes.fromhex(bob_messages[1]["nonce"]),
        group_key=group["group_key"],
        group_id=group["id"],
        key_version=bob_messages[1]["group_key_version"]
    )
    assert bob_decrypted_2 == bob_msg

    # Charlie also can decrypt (same key_version)
    charlie_messages = fetch_group_messages(charlie, group_id=group["id"])
    assert len(charlie_messages) == 2

    # ─── Step 7: Alice removes Charlie (triggers key rotation) ───
    charlie_member_id = get_group_member_id(group["id"], charlie.user_id)
    assert charlie_member_id is not None

    remove_member(alice, group_id=group["id"], member_id=charlie_member_id)

    # Verify key_version incremented
    new_key_version = get_group_key_version(group["id"])
    assert new_key_version == 2

    # ─── Step 8: Generate new group_key for v2 ───
    # In production, this would be distributed via DM
    # For testing, we generate a new key
    new_group_key = os.urandom(32)

    # ─── Step 9: Alice sends new message with key_version 2 ───
    new_msg = "Charlie is out, proceed with new plan"
    ciphertext_new, nonce_new = encrypt_group_message(
        new_msg,
        group_key=new_group_key,
        group_id=group["id"],
        key_version=new_key_version
    )
    send_group_message(alice, group_id=group["id"], encrypted_message=ciphertext_new, nonce=nonce_new)

    # ─── Step 10: Bob (still member) can decrypt new message ───
    fresh_messages = fetch_group_messages(bob, group_id=group["id"])
    assert len(fresh_messages) == 3

    # Verify the new message has key_version 2
    assert fresh_messages[2]["group_key_version"] == 2

    bob_new_decrypted = decrypt_group_message(
        bytes.fromhex(fresh_messages[2]["encrypted_message"]),
        bytes.fromhex(fresh_messages[2]["nonce"]),
        group_key=new_group_key,
        group_id=group["id"],
        key_version=fresh_messages[2]["group_key_version"]
    )
    assert bob_new_decrypted == new_msg

    # ─── Step 11: Charlie (removed) cannot fetch messages anymore ───
    # Verify Charlie is denied access (API enforces membership check)
    response = client.get(
        f"/chat/groups/{group['id']}/messages",
        headers={"Authorization": f"Bearer {charlie.token}"}
    )
    assert response.status_code == 403  # Forbidden - not a member

    # ─── Step 12: Verify Charlie cannot decrypt v2 messages with old key ───
    # Get the v2 message content directly to verify decryption fails
    # We'll create a fresh fetch as a member and store the message, then verify decryption fails
    # Actually, we already fetched the messages as Bob, so we can verify Charlie can't decrypt those
    v2_ciphertext = bytes.fromhex(fresh_messages[2]["encrypted_message"])
    v2_nonce = bytes.fromhex(fresh_messages[2]["nonce"])

    # Try to decrypt v2 message with v1 key (should fail)
    with pytest.raises(Exception):  # cryptography.exceptions.InvalidTag
        decrypt_group_message(
            v2_ciphertext,
            v2_nonce,
            group_key=group["group_key"],  # Old v1 key
            group_id=group["id"],
            key_version=2
        )

    # ─── Step 12: Delete group (creator-only) ───
    delete_group(alice, group_id=group["id"])

    # Verify group no longer exists
    # Try to fetch messages (should fail)
    response = client.get(
        f"/chat/groups/{group['id']}/messages",
        headers={"Authorization": f"Bearer {alice.token}"}
    )
    assert response.status_code == 404
