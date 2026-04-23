"""
Stealth & Privacy Hardening — Zero-Trace Operational Fabric.
Ensures all outbound tactical traffic is routed through encrypted proxies or Tor.
"""

import os
import subprocess
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

class StealthEngine:
    def __init__(self):
        self.proxy_url = config.get("stealth", "proxy_url")
        self.enforce_privacy = config.get("stealth", "enforce_privacy", default=True)
        self.active = False

    def engage(self) -> bool:
        """Activates the stealth layer by configuring global proxy settings."""
        if not self.proxy_url:
            # Try to find a local Tor proxy if none configured
            if self._check_tor():
                self.proxy_url = "socks5://127.0.0.1:9050"
                logger.info("stealth", "Local Tor detected. Routing through SOCKS5:9050")
            else:
                logger.warning("stealth", "No proxy configured and Tor not found. Privacy NOT enforced.")
                return False

        # Set environment variables for standard tools (curl, etc)
        os.environ["HTTP_PROXY"] = self.proxy_url
        os.environ["HTTPS_PROXY"] = self.proxy_url
        os.environ["ALL_PROXY"] = self.proxy_url
        os.environ["NO_PROXY"] = "localhost,127.0.0.1"
        
        self.active = True
        logger.info("stealth", f"Stealth Layer ENGAGED. Routing through {self.proxy_url}")
        return True

    def _check_tor(self) -> bool:
        """Checks if Tor is running on the default port."""
        try:
            # Quick check for port 9050
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(('127.0.0.1', 9050)) == 0
        except OSError:
            return False

    def wrap_command(self, cmd: list[str]) -> list[str]:
        """Wraps a command with proxychains if active and available."""
        if not self.active:
            return cmd
        
        # Check if proxychains is installed
        import shutil
        pc = shutil.which("proxychains4") or shutil.which("proxychains")
        if pc:
            return [pc, "-q"] + cmd
        
        return cmd

stealth = StealthEngine()
