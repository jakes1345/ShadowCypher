"""ShadowCypher Recon (Signal) Engine — Absolute Sync (Build V29.1)."""

import os
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class Recon:
    """The 'Signal' engine. Handles port scanning, discovery, and path tracing."""
    
    def __init__(self):
        self.gateway = "192.168.1.1" # Dynamic detection hook
        self.scans = []

    @staticmethod
    def get_scan_types():
        return ["Quick Port Scan", "Full Port Scan", "UDP Scan", "OS Detection", "Service Fingerprint"]

    @staticmethod
    def pulse_target(target, stype="Quick Port Scan", on_output=None, on_complete=None):
        logger.info("recon", f"PULSING_TARGET: {target} [TYPE={stype}]")
        
        cmds = {
            "Quick Port Scan": f"nmap -F {target}",
            "Full Port Scan": f"nmap -p- {target}",
            "UDP Scan": f"nmap -sU {target}",
            "OS Detection": f"nmap -O {target}",
            "Service Fingerprint": f"nmap -sV {target}"
        }
        
        cmd = cmds.get(stype, f"nmap {target}")
        runner.execute_task(f"RECON_{target}", cmd, callback=on_output)

    @staticmethod
    def traceroute(target, on_output=None, on_complete=None):
        cmd = f"traceroute {target}"
        runner.execute_task(f"TRACE_{target}", cmd, callback=on_output)

    # UI Backend Hooks
    def discover_hosts(self, on_output=None, on_complete=None):
        cmd = "nmap -sn 192.168.1.0/24"
        runner.execute_task("HOST_DISCOVERY", cmd, callback=on_output)
