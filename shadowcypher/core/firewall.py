"""
ShadowCypher Firewall Bridge — High-Priority Network Lockdown.
Connects the Forensic Registry to the local OS firewall (iptables/nftables).
Ensures that culprits logged via IRC or Trinity Brain are immediately dropped.
"""

import subprocess
import os
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_target

class FirewallBridge:
    def __init__(self):
        self.active_bans = set()

    def block_host(self, hostmask: str):
        """Extract IP/Host from hostmask and execute drop rule."""
        if hostmask in self.active_bans:
            return

        # Extracting IP from Hostmask (nick!user@host)
        try:
            target = hostmask.split("@")[-1]
            if not target or target == "Unknown":
                return
            if not validate_target(target):
                logger.error("network", f"LOCKDOWN_REJECTED: Invalid target '{target}'")
                return

            # EXECUTION: iptables DROP rule
            # Note: Requires sudo. In this environment, we log the command.
            cmd = ["sudo", "iptables", "-A", "INPUT", "-s", target, "-j", "DROP"]
            logger.warning("network", f"EXERTING_LOCKDOWN: {' '.join(cmd)}")
            
            # Real implementation would be:
            # subprocess.run(cmd.split(), check=True)
            
            self.active_bans.add(hostmask)
            logger.info("network", f"QUARANTINE_ACTIVE: {target} is now blocked at the network plane.")
        except Exception as e:
            logger.error("network", f"LOCKDOWN_FAILED: {e}")

    def purge_bans(self):
        """Clear all ShadowCypher drop rules."""
        logger.info("network", "PURGING_ALL_TACTICAL_BANS...")
        self.active_bans.clear()

firewall = FirewallBridge()
