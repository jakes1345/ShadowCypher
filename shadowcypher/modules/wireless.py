"""
Wireless Module — interface management and network scanning.
"""

import logging

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_interface

logger = logging.getLogger(__name__)



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

    # ── Scanning ──

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
