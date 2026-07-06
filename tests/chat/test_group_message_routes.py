import pytest
from fastapi.testclient import TestClient
from shadowcypher.main import app
import binascii

client = TestClient(app)


@pytest.fixture
def setup_users_and_group():
    """Set up creator, member users and a group"""
    # Register creator
    creator_response = client.post(
        "/chat/register",
        json={"username": "msg_creator", "public_key": "a" * 64}
    )
    creator_id = creator_response.json()["user_id"]
    creator_token = creator_response.json()["token"]
    creator_headers = {"Authorization": f"Bearer {creator_token}"}

    # Register member
    member_response = client.post(
        "/chat/register",
        json={"username": "msg_member", "public_key": "b" * 64}
    )
    member_id = member_response.json()["user_id"]
    member_token = member_response.json()["token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Register non-member
    non_member_response = client.post(
        "/chat/register",
        json={"username": "msg_non_member", "public_key": "c" * 64}
    )
    non_member_token = non_member_response.json()["token"]
    non_member_headers = {"Authorization": f"Bearer {non_member_token}"}

    # Create group
    group_response = client.post(
        "/chat/groups",
        json={"name": "Message Test Group"},
        headers=creator_headers
    )
    group_id = group_response.json()["id"]

    # Add creator as member (creator should be in their own group)
    client.post(
        f"/chat/groups/{group_id}/members",
        json={"user_id": creator_id},
        headers=creator_headers
    )

    # Add member to group
    client.post(
        f"/chat/groups/{group_id}/members",
        json={"user_id": member_id},
        headers=creator_headers
    )

    return {
        "creator_id": creator_id,
        "creator_headers": creator_headers,
        "member_id": member_id,
        "member_headers": member_headers,
        "non_member_headers": non_member_headers,
        "group_id": group_id,
    }


def test_send_group_message_by_member(setup_users_and_group):
    """Test sending a message to a group as a member"""
    setup = setup_users_and_group

    encrypted_msg = binascii.hexlify(b"encrypted_content").decode()
    nonce = binascii.hexlify(b"nonce_12345678").decode()

    response = client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": encrypted_msg, "nonce": nonce},
        headers=setup["member_headers"]
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["group_id"] == setup["group_id"]
    assert data["sender_id"] == setup["member_id"]
    assert data["encrypted_message"] == encrypted_msg
    assert data["nonce"] == nonce
    assert data["timestamp"] > 0
    assert data["group_key_version"] == 1


def test_send_group_message_by_creator(setup_users_and_group):
    """Test sending a message to a group as creator"""
    setup = setup_users_and_group

    encrypted_msg = binascii.hexlify(b"creator_message").decode()
    nonce = binascii.hexlify(b"nonce_87654321").decode()

    response = client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": encrypted_msg, "nonce": nonce},
        headers=setup["creator_headers"]
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sender_id"] == setup["creator_id"]
    assert data["encrypted_message"] == encrypted_msg


def test_send_group_message_non_member_forbidden(setup_users_and_group):
    """Test that non-members cannot send messages to group"""
    setup = setup_users_and_group

    encrypted_msg = binascii.hexlify(b"unauthorized").decode()
    nonce = binascii.hexlify(b"nonce_xxx").decode()

    response = client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": encrypted_msg, "nonce": nonce},
        headers=setup["non_member_headers"]
    )

    assert response.status_code == 403
    assert "not a member" in response.json()["detail"].lower()


def test_send_group_message_invalid_group(setup_users_and_group):
    """Test sending message to non-existent group"""
    setup = setup_users_and_group

    encrypted_msg = binascii.hexlify(b"message").decode()
    nonce = binascii.hexlify(b"nonce").decode()

    response = client.post(
        "/chat/groups/invalid-group-id/messages",
        json={"encrypted_message": encrypted_msg, "nonce": nonce},
        headers=setup["member_headers"]
    )

    assert response.status_code == 404
    assert "group not found" in response.json()["detail"].lower()


def test_send_group_message_invalid_encoding(setup_users_and_group):
    """Test sending message with invalid hex encoding"""
    setup = setup_users_and_group

    response = client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": "not-hex", "nonce": "also-not-hex"},
        headers=setup["member_headers"]
    )

    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_get_group_messages_empty(setup_users_and_group):
    """Test fetching messages from empty group"""
    setup = setup_users_and_group

    response = client.get(
        f"/chat/groups/{setup['group_id']}/messages",
        headers=setup["member_headers"]
    )

    assert response.status_code == 200
    messages = response.json()
    assert messages == []


def test_get_group_messages_multiple(setup_users_and_group):
    """Test fetching multiple messages from group"""
    setup = setup_users_and_group

    # Send first message from member
    msg1_encrypted = binascii.hexlify(b"first_message").decode()
    msg1_nonce = binascii.hexlify(b"nonce_1").decode()
    client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": msg1_encrypted, "nonce": msg1_nonce},
        headers=setup["member_headers"]
    )

    # Send second message from creator
    msg2_encrypted = binascii.hexlify(b"second_message").decode()
    msg2_nonce = binascii.hexlify(b"nonce_2").decode()
    client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": msg2_encrypted, "nonce": msg2_nonce},
        headers=setup["creator_headers"]
    )

    # Fetch messages
    response = client.get(
        f"/chat/groups/{setup['group_id']}/messages",
        headers=setup["member_headers"]
    )

    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 2

    # Verify message order (by timestamp)
    assert messages[0]["sender_id"] == setup["member_id"]
    assert messages[0]["encrypted_message"] == msg1_encrypted
    assert messages[1]["sender_id"] == setup["creator_id"]
    assert messages[1]["encrypted_message"] == msg2_encrypted


def test_get_group_messages_non_member_forbidden(setup_users_and_group):
    """Test that non-members cannot fetch group messages"""
    setup = setup_users_and_group

    response = client.get(
        f"/chat/groups/{setup['group_id']}/messages",
        headers=setup["non_member_headers"]
    )

    assert response.status_code == 403
    assert "not a member" in response.json()["detail"].lower()


def test_get_group_messages_invalid_group(setup_users_and_group):
    """Test fetching messages from non-existent group"""
    setup = setup_users_and_group

    response = client.get(
        "/chat/groups/invalid-group-id/messages",
        headers=setup["member_headers"]
    )

    assert response.status_code == 404
    assert "group not found" in response.json()["detail"].lower()


def test_group_messages_preserve_group_key_version(setup_users_and_group):
    """Test that messages preserve group key version"""
    setup = setup_users_and_group

    encrypted_msg = binascii.hexlify(b"version_test").decode()
    nonce = binascii.hexlify(b"nonce_ver").decode()

    # Send message
    response = client.post(
        f"/chat/groups/{setup['group_id']}/messages",
        json={"encrypted_message": encrypted_msg, "nonce": nonce},
        headers=setup["member_headers"]
    )
    assert response.json()["group_key_version"] == 1

    # Fetch message
    get_response = client.get(
        f"/chat/groups/{setup['group_id']}/messages",
        headers=setup["member_headers"]
    )
    assert get_response.json()[0]["group_key_version"] == 1
