import hashlib
import pytest
from fastapi.testclient import TestClient
from shadowcypher.main import app
from shadowcypher.chat.crypto import generate_keypair, derive_shared_secret, derive_session_key, encrypt_message, decrypt_message

client = TestClient(app)

def test_complete_chat_flow():
    """Full flow: register → add contact → send message → decrypt"""

    # 1. Generate keypairs
    alice_priv, alice_pub = generate_keypair()
    bob_priv, bob_pub = generate_keypair()

    # 2. Register Alice
    alice_reg = client.post("/chat/register", json={
        "username": "alice",
        "public_key": alice_pub.hex(),
    }).json()
    alice_token = alice_reg["token"]

    # 3. Register Bob
    bob_reg = client.post("/chat/register", json={
        "username": "bob",
        "public_key": bob_pub.hex(),
    }).json()
    bob_token = bob_reg["token"]

    # 4. Alice adds Bob as contact — fingerprint = SHA256(pubkey)[:8]
    bob_fingerprint = hashlib.sha256(bob_pub).hexdigest()[:8]
    alice_contact = client.post(
        "/chat/add-contact",
        json={
            "contact_username": "bob",
            "contact_pubkey": bob_pub.hex(),
            "fingerprint": bob_fingerprint,
        },
        headers={"Authorization": f"Bearer {alice_token}"}
    ).json()
    assert alice_contact["contact_username"] == "bob"

    # 5. Alice and Bob derive shared secret (ECDH)
    alice_shared = derive_shared_secret(alice_priv, bob_pub)
    bob_shared = derive_shared_secret(bob_priv, alice_pub)
    assert alice_shared == bob_shared

    # 6. Derive session key
    conversation_id = "alice-bob-conv-1"
    session_key = derive_session_key(alice_shared, conversation_id)

    # 7. Alice encrypts message
    plaintext = "Hello Bob! This is a secret message."
    ciphertext, nonce = encrypt_message(plaintext, session_key)

    # 8. Alice sends encrypted message to server
    msg_response = client.post(
        "/chat/send-message",
        json={
            "conversation_id": 1,
            "encrypted_message": ciphertext.hex(),
            "nonce": nonce.hex(),
        },
        headers={"Authorization": f"Bearer {alice_token}"}
    ).json()
    assert "message_id" in msg_response

    # 9. Bob fetches messages
    messages = client.get(
        "/chat/conversations/1/messages",
        headers={"Authorization": f"Bearer {bob_token}"}
    ).json()

    # 10. Bob decrypts message with shared session key
    encrypted_msg = messages[0]
    decrypted = decrypt_message(
        bytes.fromhex(encrypted_msg["encrypted_message"]),
        bytes.fromhex(encrypted_msg["nonce"]),
        session_key
    )
    assert decrypted == plaintext
