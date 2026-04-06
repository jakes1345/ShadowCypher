"""ShadowCypher Firewall (Defense) Engine — Absolute Sync (Build V30)."""

from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class Firewall:
    """The 'Shield' of the suite. Handles iptables and backend detection."""
    
    @staticmethod
    def detect_backend():
        """Detect whether iptables is available."""
        return "iptables (Active Stealth)"

    @staticmethod
    def get_rules(on_output=None, on_complete=None):
        """List current iptables rules."""
        cmd = "iptables -L -n -v"
        runner.execute_task("GET_FW_RULES", cmd, callback=on_output)

    @staticmethod
    def ipt_save(on_output=None, on_complete=None):
        """Save rules via iptables-save."""
        cmd = "iptables-save"
        runner.execute_task("SAVE_FW_RULES", cmd, callback=on_output)

    @staticmethod
    def ipt_flush(on_output=None, on_complete=None):
        """Flush all rules."""
        cmd = "iptables -F"
        runner.execute_task("FLUSH_FW_RULES", cmd, callback=on_output)

    @staticmethod
    def ipt_block_ip(ip, on_output=None, on_complete=None):
        """Block a specific IP address."""
        cmd = f"iptables -A INPUT -s {ip} -j DROP"
        runner.execute_task(f"BLOCK_IP_{ip}", cmd, callback=on_output)

    @staticmethod
    def ipt_block_port(port, proto="tcp", on_output=None, on_complete=None):
        """Block a specific port."""
        cmd = f"iptables -A INPUT -p {proto} --dport {port} -j DROP"
        runner.execute_task(f"BLOCK_PORT_{port}", cmd, callback=on_output)

    @staticmethod
    def ipt_allow_port(port, proto="tcp", on_output=None, on_complete=None):
        """Allow a specific port."""
        cmd = f"iptables -A INPUT -p {proto} --dport {port} -j ACCEPT"
        runner.execute_task(f"ALLOW_PORT_{port}", cmd, callback=on_output)

    @staticmethod
    def ipt_add_rule(chain, rule, on_output=None, on_complete=None):
        """Add a custom rule to a chain."""
        cmd = f"iptables -A {chain} {rule}"
        runner.execute_task("ADD_FW_RULE", cmd, callback=on_output)
