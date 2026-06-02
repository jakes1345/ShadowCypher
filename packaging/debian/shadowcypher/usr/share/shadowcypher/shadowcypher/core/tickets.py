"""
ShadowCypher Ticket Core — Programmatic support ticket generation.
Enables autonomous agents (Bots) to escalate issues to the SHADOW_ADMIN.
"""

import os
import json
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

def create_support_ticket(handle: str, message: str, hostmask: str = "Unknown", reason: str = "Unspecified") -> Optional[str]:
    """
    Encrypt and save a support ticket with forensic metadata.
    """
    tickets_dir = config.project_root / "tickets"
    tickets_dir.mkdir(exist_ok=True)
    
    pub_key_path = config.project_root / "shadowcypher" / "core" / "admin_public.pem"
    
    if not pub_key_path.exists():
        logger.error("tickets", "Admin public key missing. Cannot create ticket.")
        return None
        
    try:
        # Full forensic payload
        full_report = {
            "origin": "ShadowSentinel_Audit",
            "culprit_handle": handle,
            "hostmask": hostmask,
            "failure_reason": reason,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        report_json = json.dumps(full_report)

        # 1. RSA-OAEP Encryption
        with open(pub_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
            
        ciphertext = public_key.encrypt(
            report_json.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        
        b64_cipher = base64.b64encode(ciphertext).decode()
        
        # 2. Persistence
        ts = int(time.time())
        ticket_filename = f"culprit_{ts}_{handle}.json"
        ticket_path = tickets_dir / ticket_filename
        
        with open(ticket_path, "w") as f:
            json.dump({
                "handle": handle,
                "timestamp": full_report["timestamp"],
                "encrypted_message": b64_cipher,
                "forensic_flag": True
            }, f, indent=2)
            
        logger.warning("tickets", f"CULPRIT_LOGGED: {handle} at {hostmask}")
        
        # 3. Broadcast to System Bus
        bus.publish("new_ticket", {
            "path": str(ticket_filename),
            "handle": handle,
            "forensic": True
        })
        
        return str(ticket_path)
        
    except Exception as e:
        logger.error("tickets", f"TICKET_GEN_FAILED: {e}")
        return None
