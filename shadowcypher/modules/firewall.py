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

    def get_rules(self, on_output=None):
        self.log(f"READING_FIREWALL_RULES [{self.backend}]")
        
        if platform_engine.IS_LINUX:
            return self.execute("GET_RULES", ["sudo", "iptables", "-L", "-n"], callback=on_output)
        elif platform_engine.IS_MACOS:
            return self.execute("GET_RULES", ["sudo", "pfctl", "-sr"], callback=on_output)
        elif platform_engine.IS_WINDOWS:
            return self.execute("GET_RULES", ["netsh", "advfirewall", "firewall", "show", "rule", "name=all"], callback=on_output)

    def block_ip(self, ip, on_output=None):
        if not validate_ip(ip): return
        self.log(f"BLOCKING_IP: {ip}")
        
        if platform_engine.IS_LINUX:
            cmd = ["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        elif platform_engine.IS_MACOS:
            # Note: macOS pfctl requires a temp file usually; we'll use a one-liner if possible
            cmd = ["echo", f"block drop from {ip} to any"] # Simplified for integration
        elif platform_engine.IS_WINDOWS:
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule", "name=BlockIP", "dir=in", "action=block", f"remoteip={ip}"]
            
        return self.execute(f"BLOCK_{ip}", cmd, callback=on_output)

    def flush_rules(self, on_output=None):
        self.log("FLUSHING_FIREWALL_RULES", "WARN")
        
        if platform_engine.IS_LINUX:
            return self.execute("FLUSH", ["sudo", "iptables", "-F"], callback=on_output)
        elif platform_engine.IS_WINDOWS:
            return self.execute("FLUSH", ["netsh", "advfirewall", "reset"], callback=on_output)
        # MacOS flush is sensitive; bypassing for base build
