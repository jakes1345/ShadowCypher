import pytest

def test_register_endpoint(client):
    """POST /chat/register creates user and returns token"""
    response = client.post("/chat/register", json={
        "username": "alice",
        "public_key": "00"*32,  # Hex-encoded 32 bytes
    })

    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert "token" in data
    assert "public_key" in data

def test_login_endpoint(client):
    """POST /chat/login validates user and returns token"""
    # First register with a password
    client.post("/chat/register", json={
        "username": "bob",
        "public_key": "11"*32,
        "password": "s3cr3tPass!",
    })

    # Then login with the same password
    response = client.post("/chat/login", json={
        "username": "bob",
        "password": "s3cr3tPass!",
        "device_id": "desktop-001",
    })

    assert response.status_code == 200
    data = response.json()
    assert "token" in data

def test_add_contact_endpoint(client):
    """POST /chat/add-contact adds contact to user"""
    import hashlib

    # Register two users
    alice = client.post("/chat/register", json={
        "username": "alice",
        "public_key": "aa"*32,
    }).json()

    bob = client.post("/chat/register", json={
        "username": "bob",
        "public_key": "bb"*32,
    }).json()

    # Compute the correct fingerprint: SHA256(pubkey_bytes)[:8]
    bob_pubkey_bytes = bytes.fromhex("bb"*32)
    bob_fingerprint = hashlib.sha256(bob_pubkey_bytes).hexdigest()[:8]

    # Alice adds Bob as contact
    response = client.post(
        "/chat/add-contact",
        json={
            "contact_username": "bob",
            "contact_pubkey": "bb"*32,
            "fingerprint": bob_fingerprint,
        },
        headers={"Authorization": f"Bearer {alice['token']}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["contact_username"] == "bob"
    assert "contact_id" in data

def test_send_message_endpoint(client):
    """POST /chat/send-message stores encrypted message"""
    from shadowcypher.chat.db import SessionLocal
    from shadowcypher.chat.models import Conversation

    # Register users and create contact
    alice = client.post("/chat/register", json={
        "username": "alice",
        "public_key": "aa"*32,
    }).json()

    bob = client.post("/chat/register", json={
        "username": "bob",
        "public_key": "bb"*32,
    }).json()

    client.post(
        "/chat/add-contact",
        json={
            "contact_username": "bob",
            "contact_pubkey": "bb"*32,
            "fingerprint": "b1b2b3b4",
        },
        headers={"Authorization": f"Bearer {alice['token']}"}
    )

    # Create conversation in database
    db = SessionLocal()
    conversation = Conversation(
        user_id_1=alice["user_id"],
        user_id_2=bob["user_id"],
        encrypted_session_key=b"session_key_123"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    db.close()

    # Send encrypted message
    response = client.post(
        "/chat/send-message",
        json={
            "conversation_id": conversation.id,
            "encrypted_message": "cc"*10,
            "nonce": "dd"*6,
        },
        headers={"Authorization": f"Bearer {alice['token']}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert "message_id" in data

def test_list_conversations_endpoint(client):
    """GET /chat/conversations lists user's conversations"""
    alice = client.post("/chat/register", json={
        "username": "alice",
        "public_key": "aa"*32,
    }).json()

    response = client.get(
        "/chat/conversations",
        headers={"Authorization": f"Bearer {alice['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_messages_in_conversation(client):
    """GET /chat/conversations/{id}/messages lists encrypted messages"""
    from shadowcypher.chat.db import SessionLocal
    from shadowcypher.chat.models import Conversation

    alice = client.post("/chat/register", json={
        "username": "alice",
        "public_key": "aa"*32,
    }).json()

    bob = client.post("/chat/register", json={
        "username": "bob",
        "public_key": "bb"*32,
    }).json()

    # Create conversation in database
    db = SessionLocal()
    conversation = Conversation(
        user_id_1=alice["user_id"],
        user_id_2=bob["user_id"],
        encrypted_session_key=b"session_key_123"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    db.close()

    response = client.get(
        f"/chat/conversations/{conversation.id}/messages",
        headers={"Authorization": f"Bearer {alice['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
