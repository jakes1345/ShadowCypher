"""ShadowCypher Communications Module.
Handles sovereign messaging and operator notifications.
"""

import requests

from shadowcypher.core.logger import logger


class CommsEngine:
    def __init__(self, resend_api_key=None):
        self.api_key = resend_api_key
        self.base_url = "https://api.resend.com/emails"

    def send_welcome_email(self, to_email, handle):
        """Sends a tactical welcome signal to a new operator."""
        if not self.api_key:
            logger.error("comms", "Missing RESEND_API_KEY. Signal suppressed.")
            return False

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "from": "ShadowCypher <onboarding@resend.dev>",
            "to": to_email,
            "subject": "SIGNAL_RECEIVED: WELCOME COMMANDER",
            "html": f"""
                <div style="background:#050505; color:#b44aff; padding:40px; font-family:monospace; border:1px solid #b44aff;">
                    <h1 style="letter-spacing:5px;">SHADOWCYPHER_ONBOARDING</h1>
                    <hr style="border-color:#b44aff;">
                    <p>OPERATOR: {handle}</p>
                    <p>STATUS: AUTHORIZED</p>
                    <p>LEVEL: LEAD_OPERATOR</p>
                    <br>
                    <p>// MISSION_START</p>
                    <p>Your identity has been established in the local SQLite matrix.
                    You now have access to the Shadow-CLI and the Sovereign Dashboard.</p>
                    <br>
                    <p style="color:#666;">STAY VIGILANT. STAY INVISIBLE.</p>
                </div>
            """
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)  # nosec B113
            if response.status_code == 200:
                logger.info("comms", f"Welcome signal sent to {to_email}")
                return True
            else:
                logger.error("comms", f"Failed to send signal: {response.text}")
                return False
        except Exception as e:
            logger.error("comms", f"Transmission error: {str(e)}")
            return False

comms = CommsEngine()
