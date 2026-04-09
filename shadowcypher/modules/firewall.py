"""
Firewall Module — Apex Sovereign Build.
High-fidelity cross-platform defense (iptables / pfctl / netsh).
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_ip, validate_port


class Firewall(BaseModule):
    """The 'Shield' engine of ShadowCypher."""

    def __init__(self):
        super().__init__(module_name="firewall")
        self.backend = platform_engine.get_firewall_backend()

    # ── Detection ──

    @staticmethod
    def detect_backend():
        """Detect and return the active firewall backend for this OS."""
        return platform_engine.get_firewall_backend()

    # ── Rule Viewing ──

    @staticmethod
    def get_rules(on_output=None, on_complete=None):
        """List all active firewall rules."""
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-L", "-n", "--line-numbers"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "pfctl", "-sr"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task("GET_RULES", cmd, callback=on_output)

    @staticmethod
    def ipt_save(on_output=None, on_complete=None):
        """Save current firewall rules to persistent storage."""
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables-save"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "pfctl", "-sr"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "export", "C:\\firewall_backup.wfw"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task("SAVE_RULES", cmd, callback=on_output)

    # ── Flush ──

    @staticmethod
    def ipt_flush(on_output=None, on_complete=None):
        """Flush ALL firewall rules (dangerous)."""
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-F"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "pfctl", "-F", "all"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "reset"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task("FLUSH_RULES", cmd, callback=on_output)

    # ── IP Rules ──

    @staticmethod
    def ipt_block_ip(ip, on_output=None, on_complete=None):
        """Block all traffic from a specific IP."""
        if not validate_ip(ip):
            return
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "bash", "-c", f"echo 'block drop from {ip} to any' | pfctl -a shadowcypher -f -"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name=SC_Block_{ip}", "dir=in", "action=block", f"remoteip={ip}"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task(f"BLOCK_{ip}", cmd, callback=on_output)

    # ── Port Rules ──

    @staticmethod
    def ipt_block_port(port, protocol="tcp", on_output=None, on_complete=None):
        """Block a specific port."""
        if not validate_port(port):
            return
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-A", "INPUT", "-p", protocol, "--dport", str(port), "-j", "DROP"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "bash", "-c", f"echo 'block drop proto {protocol} to any port {port}' | pfctl -a shadowcypher -f -"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name=SC_BlockPort_{port}", "dir=in", "action=block",
                   f"protocol={protocol}", f"localport={port}"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task(f"BLOCK_PORT_{port}", cmd, callback=on_output)

    @staticmethod
    def ipt_allow_port(port, protocol="tcp", on_output=None, on_complete=None):
        """Allow a specific port."""
        if not validate_port(port):
            return
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-A", "INPUT", "-p", protocol, "--dport", str(port), "-j", "ACCEPT"]
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "bash", "-c", f"echo 'pass in proto {protocol} to any port {port}' | pfctl -a shadowcypher -f -"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name=SC_AllowPort_{port}", "dir=in", "action=allow",
                   f"protocol={protocol}", f"localport={port}"]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task(f"ALLOW_PORT_{port}", cmd, callback=on_output)

    # ── Custom Rules ──

    @staticmethod
    def ipt_add_rule(chain, rule_str, on_output=None, on_complete=None):
        """Add a custom iptables/firewall rule."""
        from shadowcypher.core.runner import runner
        import shlex
        if platform_engine.IS_LINUX:
            parts = shlex.split(rule_str)
            cmd = ["sudo", "iptables", "-A", chain] + parts
        elif platform_engine.IS_MACOS:
            cmd = ["sudo", "bash", "-c", f"echo '{rule_str}' | pfctl -a shadowcypher -f -"]
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name=SC_Custom_{chain}", rule_str]
        else:
            cmd = ["echo", "Unsupported platform"]
        return runner.execute_task(f"ADD_RULE_{chain}", cmd, callback=on_output)

    # ── Instance methods (legacy compat) ──

    def block_ip(self, ip, on_output=None):
        return Firewall.ipt_block_ip(ip, on_output)

    def flush_rules(self, on_output=None):
        return Firewall.ipt_flush(on_output)
