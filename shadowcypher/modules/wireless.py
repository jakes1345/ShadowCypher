"""Wireless attacks module — aircrack-ng suite integration."""

import os
import tempfile
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
from shadowcypher.core.sanitize import quote, validate_interface, validate_mac, validate_filepath


_NOOP = lambda x: None


class Wireless:
    """Wireless security operations using the aircrack-ng suite."""

    @staticmethod
    def list_interfaces(on_output=None, on_complete=None) -> int:
        """List wireless interfaces."""
        cmd = "iwconfig 2>/dev/null | grep -E 'IEEE|Mode|ESSID'"
        logger.info("wireless", "Listing wireless interfaces")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def list_interfaces_sync() -> str:
        """List wireless interfaces synchronously."""
        output, _ = runner.run_sync("iwconfig 2>&1 | grep -v 'no wireless'", shell=True, timeout=5)
        return output

    @staticmethod
    def enable_monitor(interface: str, on_output=None, on_complete=None) -> int:
        """Put wireless interface into monitor mode using airmon-ng."""
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"airmon-ng start {quote(interface)}"
        logger.info("wireless", f"Enabling monitor mode: {interface}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def disable_monitor(interface: str, on_output=None, on_complete=None) -> int:
        """Take interface out of monitor mode."""
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"airmon-ng stop {quote(interface)}"
        logger.info("wireless", f"Disabling monitor mode: {interface}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def scan_networks(interface: str, duration: int = 30,
                      on_output=None, on_complete=None) -> int:
        """Scan for wireless networks using airodump-ng."""
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1

        duration = max(5, min(int(duration), 300))
        outfile = tempfile.mktemp(prefix="sc_airodump_")
        cmd = f"timeout {duration} airodump-ng --write {quote(outfile)} --output-format csv {quote(interface)} 2>&1"
        logger.info("wireless", f"Scanning networks on {interface} for {duration}s")

        def _complete(rc):
            csv_file = f"{outfile}-01.csv"
            if os.path.exists(csv_file):
                try:
                    with open(csv_file, "r") as f:
                        data = f.read()
                    if on_output:
                        on_output(f"\n{'='*60}\nScan Results:\n{'='*60}\n{data}\n")
                except OSError:
                    pass
                for ext in ["-01.csv", "-01.cap", "-01.kismet.csv", "-01.kismet.netxml", "-01.log.csv"]:
                    try:
                        os.unlink(outfile + ext)
                    except OSError:
                        pass
            if on_complete:
                on_complete(rc)

        return runner.run(cmd, on_output or _NOOP, _complete, shell=True, sudo=True)

    @staticmethod
    def capture_handshake(interface: str, bssid: str, channel: int,
                          duration: int = 120, on_output=None, on_complete=None) -> int:
        """Capture WPA handshake with airodump-ng."""
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1
        if not validate_mac(bssid):
            (on_output or _NOOP)(f"[ERROR] Invalid BSSID: {bssid}\n")
            (on_complete or _NOOP)(1)
            return -1

        channel = max(1, min(int(channel), 196))
        duration = max(10, min(int(duration), 600))
        outfile = tempfile.mktemp(prefix="sc_handshake_")
        cmd = f"timeout {duration} airodump-ng -c {channel} --bssid {quote(bssid)} --write {quote(outfile)} {quote(interface)} 2>&1"
        logger.info("wireless", f"Capturing handshake: BSSID={bssid} CH={channel}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def deauth(interface: str, bssid: str, client: str = None, count: int = 10,
               on_output=None, on_complete=None) -> int:
        """Send deauthentication frames."""
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1
        if not validate_mac(bssid):
            (on_output or _NOOP)(f"[ERROR] Invalid BSSID: {bssid}\n")
            (on_complete or _NOOP)(1)
            return -1

        client_arg = ""
        if client:
            if not validate_mac(client):
                (on_output or _NOOP)(f"[ERROR] Invalid client MAC: {client}\n")
                (on_complete or _NOOP)(1)
                return -1
            client_arg = f"-c {quote(client)}"

        count = max(1, min(int(count), 100))
        cmd = f"aireplay-ng -0 {count} -a {quote(bssid)} {client_arg} {quote(interface)}"
        logger.info("wireless", f"Deauth: BSSID={bssid}, count={count}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def crack_wpa(cap_file: str, wordlist: str = None,
                  on_output=None, on_complete=None) -> int:
        """Crack WPA/WPA2 handshake with aircrack-ng."""
        if not validate_filepath(cap_file):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {cap_file}\n")
            (on_complete or _NOOP)(1)
            return -1

        aircrack = config.get_tool_path("aircrack")
        if wordlist is None:
            wordlist = config.get_wordlist_path()
        cmd = f"aircrack-ng -w {quote(wordlist)} {quote(cap_file)}"
        logger.info("wireless", f"Cracking WPA: {cap_file}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def crack_wep(cap_file: str, on_output=None, on_complete=None) -> int:
        """Crack WEP key from captured IVs."""
        if not validate_filepath(cap_file):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {cap_file}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"aircrack-ng {quote(cap_file)}"
        logger.info("wireless", f"Cracking WEP: {cap_file}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def check_monitor_mode(interface: str) -> bool:
        """Check if interface is in monitor mode."""
        if not validate_interface(interface):
            return False
        output, _ = runner.run_sync(f"iwconfig {quote(interface)} 2>&1", shell=True, timeout=5)
        return "Monitor" in output
