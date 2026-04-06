"""ShadowCypher Firewall (Defense) Engine — High-Fidelity Sync (V23.2)."""

import os
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Firewall:
    """The 'Shield' of the suite. Handles iptables, ufw, and status checks."""
    
    @staticmethod
    def get_status():
        """Retrieve current firewall status."""
        os.system("iptables -L -n > /tmp/fw_status.txt")
        with open("/tmp/fw_status.txt", "r") as f:
            return f.read()

    @staticmethod
    def add_rule(rule, on_output=None, on_complete=None):
        """Inject a custom iptables rule into the active shield."""
        cmd = f"iptables -A {rule}"
        runner.execute_task("ADD_FW_RULE", cmd, callback=on_output)

    @staticmethod
    def block_ip(ip, on_output=None, on_complete=None):
        """Hard-block a specific IP address via iptables."""
        cmd = f"iptables -A INPUT -s {ip} -j DROP"
        runner.execute_task(f"BLOCK_IP_{ip}", cmd, callback=on_output)

    @staticmethod
    def unblock_ip(ip, on_output=None, on_complete=None):
        """Remove a block rule for a specific IP."""
        cmd = f"iptables -D INPUT -s {ip} -j DROP"
        runner.execute_task(f"UNBLOCK_IP_{ip}", cmd, callback=on_output)

    @staticmethod
    def reset_firewall(on_output=None, on_complete=None):
        """Reset the shield to default allow state."""
        cmd = "iptables -F"
        runner.execute_task("RESET_FIREWALL", cmd, callback=on_output)
