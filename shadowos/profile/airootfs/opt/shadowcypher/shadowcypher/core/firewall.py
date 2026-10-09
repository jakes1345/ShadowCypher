"""
Firewall bridge — connects the forensic registry to the local OS firewall.
Issues DROP rules for hosts flagged via IRC audit or the threat registry.
Requires passwordless sudo (or pkexec) for the iptables/nft invocation;
without elevation the call fails with a logged error and the ban stays
in-memory only.
"""

import shutil
import subprocess
from typing import List

from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_target


class FirewallBridge:
    def __init__(self):
        self.active_bans: set[str] = set()
        self.backend = platform_engine.get_firewall_backend()

    def _build_cmd(self, target: str, add: bool) -> List[str]:
        """Assemble the platform-appropriate block/unblock command."""
        if self.backend == "NFTABLES" and shutil.which("nft"):
            # Expect a table/chain 'inet shadowcypher/input' to exist; create on demand.
            action = "add" if add else "delete"
            return [
                "sudo", "nft", action, "rule", "inet", "shadowcypher", "input",
                "ip", "saddr", target, "drop",
            ]
        # Default to iptables (works for IPTABLES and GENERIC_LINUX).
        flag = "-A" if add else "-D"
        return ["sudo", "iptables", flag, "INPUT", "-s", target, "-j", "DROP"]

    def _ensure_nft_table(self) -> None:
        """Create the inet shadowcypher table/chain if using nftables."""
        if self.backend != "NFTABLES" or not shutil.which("nft"):
            return
        try:
            subprocess.run(
                ["sudo", "nft", "add", "table", "inet", "shadowcypher"],
                check=False, capture_output=True, timeout=5,
            )
            subprocess.run(
                ["sudo", "nft", "add", "chain", "inet", "shadowcypher", "input",
                 "{ type filter hook input priority 0 ; }"],
                check=False, capture_output=True, timeout=5,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.debug("network", f"nft table ensure skipped: {e}")

    def block_host(self, hostmask: str) -> bool:
        """Extract IP/host from hostmask and execute a drop rule."""
        if hostmask in self.active_bans:
            return True

        target = hostmask.split("@")[-1] if "@" in hostmask else hostmask
        if not target or target == "Unknown":
            return False
        if not validate_target(target):
            logger.error("network", f"LOCKDOWN_REJECTED: Invalid target '{target}'")
            return False

        self._ensure_nft_table()
        cmd = self._build_cmd(target, add=True)
        logger.warning("network", f"APPLYING_LOCKDOWN: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("network", f"LOCKDOWN_FAILED ({target}): {e}")
            return False

        if result.returncode != 0:
            logger.error(
                "network",
                f"LOCKDOWN_FAILED ({target}): rc={result.returncode} stderr={result.stderr.strip()}",
            )
            return False

        self.active_bans.add(hostmask)
        logger.info("network", f"QUARANTINE_ACTIVE: {target} blocked via {self.backend}")
        return True

    def unblock_host(self, hostmask: str) -> bool:
        """Remove a previously installed drop rule."""
        if hostmask not in self.active_bans:
            return True
        target = hostmask.split("@")[-1] if "@" in hostmask else hostmask
        if not validate_target(target):
            return False
        cmd = self._build_cmd(target, add=False)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.error("network", f"UNBLOCK_FAILED ({target}): {e}")
            return False
        if result.returncode == 0:
            self.active_bans.discard(hostmask)
            logger.info("network", f"QUARANTINE_LIFTED: {target}")
            return True
        logger.warning("network", f"UNBLOCK_NONZERO ({target}): rc={result.returncode}")
        self.active_bans.discard(hostmask)
        return False

    def purge_bans(self) -> None:
        """Lift all active bans installed by this session."""
        logger.info("network", f"PURGING_BANS: {len(self.active_bans)} rules")
        for hostmask in list(self.active_bans):
            self.unblock_host(hostmask)
        self.active_bans.clear()


firewall = FirewallBridge()
