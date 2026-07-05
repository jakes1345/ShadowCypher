"""
Fail2Ban Management Module — Enterprise Defensive Build.
Views jail status, banned IPs, and log-scan activity for the fail2ban
service already running on the operator's machine. Read-mostly by design —
unban/ban actions are explicit, logged, and never touch jails you didn't
name.
"""

import re
import shutil
from typing import Callable, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_ip


class Fail2BanManager(BaseModule):
    """The 'Warden' engine — visibility and control over fail2ban jails."""

    def __init__(self):
        super().__init__(module_name="fail2ban")

    def _client(self) -> Optional[str]:
        client = self.get_tool_path("fail2ban_client")
        if not shutil.which(client):
            return None
        return client

    def status(self, on_output: Callable = None) -> Optional[str]:
        """List all active jails and their current state."""
        client = self._client()
        if not client:
            if on_output:
                on_output(
                    "[FAIL2BAN] fail2ban-client not found — install: "
                    "pacman -S fail2ban / apt install fail2ban\n"
                )
            return None
        self.log("FAIL2BAN_STATUS")
        return self.execute("F2B_STATUS", ["sudo", client, "status"], callback=on_output)

    def jail_status(self, jail: str, on_output: Callable = None) -> Optional[str]:
        """List banned IPs, current/total failures, and ban time for a
        specific jail (e.g. 'sshd')."""
        client = self._client()
        if not client:
            if on_output:
                on_output("[FAIL2BAN] fail2ban-client not found.\n")
            return None
        if not re.match(r'^[a-zA-Z0-9_\-]+$', jail):
            if on_output:
                on_output(f"[FAIL2BAN] Invalid jail name: {jail}\n")
            return None
        self.log(f"FAIL2BAN_JAIL_STATUS: {jail}")
        return self.execute(f"F2B_JAIL_{jail}", ["sudo", client, "status", jail], callback=on_output)

    def unban(self, ip: str, jail: str = None, on_output: Callable = None) -> Optional[str]:
        """Unban an IP — from a specific jail, or every jail if none given.
        Explicit, logged action; never runs on unvalidated input."""
        client = self._client()
        if not client:
            return None
        if not validate_ip(ip):
            if on_output:
                on_output(f"[FAIL2BAN] Invalid IP: {ip}\n")
            return None
        self.log(f"FAIL2BAN_UNBAN: {ip} (jail={jail or 'all'})", level="WARN")
        if jail:
            if not re.match(r'^[a-zA-Z0-9_\-]+$', jail):
                if on_output:
                    on_output(f"[FAIL2BAN] Invalid jail name: {jail}\n")
                return None
            args = ["sudo", client, "set", jail, "unbanip", ip]
        else:
            args = ["sudo", client, "unban", ip]
        return self.execute(f"F2B_UNBAN_{ip}", args, callback=on_output)

    def ban(self, ip: str, jail: str, on_output: Callable = None) -> Optional[str]:
        """Manually ban an IP in a specific jail (e.g. after spotting it in
        threat intel results that fail2ban's own filters wouldn't catch)."""
        client = self._client()
        if not client:
            return None
        if not validate_ip(ip):
            if on_output:
                on_output(f"[FAIL2BAN] Invalid IP: {ip}\n")
            return None
        if not re.match(r'^[a-zA-Z0-9_\-]+$', jail):
            if on_output:
                on_output(f"[FAIL2BAN] Invalid jail name: {jail}\n")
            return None
        self.log(f"FAIL2BAN_BAN: {ip} → {jail}", level="WARN")
        args = ["sudo", client, "set", jail, "banip", ip]
        return self.execute(f"F2B_BAN_{ip}", args, callback=on_output)

    def reload(self, on_output: Callable = None) -> Optional[str]:
        """Reload fail2ban config after editing jail.local / filters."""
        client = self._client()
        if not client:
            return None
        self.log("FAIL2BAN_RELOAD")
        return self.execute("F2B_RELOAD", ["sudo", client, "reload"], callback=on_output)


fail2ban_manager = Fail2BanManager()
