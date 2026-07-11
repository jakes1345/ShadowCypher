# shadowcypher/chat/fallback.py

import time
import logging
from shadowcypher.chat.db import SessionLocal
from shadowcypher.chat import p2p_relay
from shadowcypher.chat.models import Message
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)
MAX_P2P_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

def send_with_fallback(to_user_id: str, encrypted_message: bytes, nonce: bytes,
                       conversation_id: str = None, from_instance_id: str = None,
                       sender_username: str = "unknown",
                       session: Session = None) -> dict:
    """
    Send message with P2P preference, fall back to server relay if P2P fails.

    Returns: {status: "delivered", via: "p2p" | "relay", attempts: N}
    """
    if not session:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        # Try P2P with retries (if from_instance_id provided)
        if from_instance_id:
            attempts = 0
            for attempt in range(MAX_P2P_RETRIES):
                attempts += 1
                result = p2p_relay.send_p2p_message(
                    from_instance_id,
                    to_user_id,  # Note: this is actually instance_id in P2P context
                    encrypted_message,
                    nonce
                )
                if result["status"] == "delivered":
                    return {"status": "delivered", "via": "p2p", "attempts": attempts}

                if attempt < MAX_P2P_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        # Fall back to server relay (Phase 1 mechanism)
        return _relay_via_server(to_user_id, encrypted_message, nonce, conversation_id, sender_username, session)
    finally:
        if close_session:
            session.close()

def _relay_via_server(to_user_id: str, encrypted_message: bytes, nonce: bytes,
                      conversation_id: str, sender_username: str, session: Session) -> dict:
    """Fall back to Phase 1 server relay (store message for recipient)."""
    try:
        message = Message(
            conversation_id=conversation_id,
            encrypted_message=encrypted_message,
            nonce=nonce,
            sender=sender_username,  # Use actual username from JWT claims
            delivery_status="queued"
        )
        session.add(message)
        session.commit()

        return {"status": "delivered", "via": "relay", "attempts": 1}
    except Exception as e:
        log.error("Relay fallback failed: %s", e, exc_info=True)
        return {"status": "failed", "via": "relay", "error": str(e), "attempts": 1}
