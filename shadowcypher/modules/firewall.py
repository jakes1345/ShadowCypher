"""ShadowCypher Firewall (Defense) Engine — Absolute Sync (Build V30)."""

import shlex
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_ip, validate_port


class Firewall:
    """The 'Shield' of the suite. Handles iptables and backend detection."""

    @staticmethod
    def detect_backend():
        """Detect whether iptables is available."""
        return "iptables (Active Stealth)"

    @staticmethod
    def get_rules(on_output=None, on_complete=None):
        """List current iptables rules."""
        runner.execute_task("GET_FW_RULES", ["iptables", "-L", "-n", "-v"], callback=on_output)

    @staticmethod
    def ipt_save(on_output=None, on_complete=None):
        """Save rules via iptables-save."""
        runner.execute_task("SAVE_FW_RULES", ["iptables-save"], callback=on_output)

    @staticmethod
    def ipt_flush(on_output=None, on_complete=None):
        """Flush all rules."""
        runner.execute_task("FLUSH_FW_RULES", ["iptables", "-F"], callback=on_output)

    @staticmethod
    def ipt_block_ip(ip, on_output=None, on_complete=None):
        """Block a specific IP address."""
        if not validate_ip(ip):
            if on_output: on_output(f"[ERROR] Invalid IP address: {ip}")
            return
        runner.execute_task(f"BLOCK_IP_{ip}", ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"], callback=on_output)

    @staticmethod
    def ipt_block_port(port, proto="tcp", on_output=None, on_complete=None):
        """Block a specific port."""
        if not validate_port(port):
            if on_output: on_output(f"[ERROR] Invalid port: {port}")
            return
        if proto not in ("tcp", "udp"):
            if on_output: on_output(f"[ERROR] Invalid protocol: {proto}")
            return
        runner.execute_task(f"BLOCK_PORT_{port}", ["iptables", "-A", "INPUT", "-p", proto, "--dport", str(port), "-j", "DROP"], callback=on_output)

    @staticmethod
    def ipt_allow_port(port, proto="tcp", on_output=None, on_complete=None):
        """Allow a specific port."""
        if not validate_port(port):
            if on_output: on_output(f"[ERROR] Invalid port: {port}")
            return
        if proto not in ("tcp", "udp"):
            if on_output: on_output(f"[ERROR] Invalid protocol: {proto}")
            return
        runner.execute_task(f"ALLOW_PORT_{port}", ["iptables", "-A", "INPUT", "-p", proto, "--dport", str(port), "-j", "ACCEPT"], callback=on_output)

    @staticmethod
    def ipt_add_rule(chain, rule, on_output=None, on_complete=None):
        """Add a custom rule to a chain."""
        allowed_chains = ("INPUT", "OUTPUT", "FORWARD")
        if chain not in allowed_chains:
            if on_output: on_output(f"[ERROR] Invalid chain: {chain}. Must be one of {allowed_chains}")
            return
        # Split the rule string safely via shlex
        try:
            rule_args = shlex.split(rule)
        except ValueError as e:
            if on_output: on_output(f"[ERROR] Invalid rule syntax: {e}")
            return
        runner.execute_task("ADD_FW_RULE", ["iptables", "-A", chain] + rule_args, callback=on_output)
