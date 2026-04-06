"""ShadowCypher Signal Recon Engine — High-Fidelity Sync (V23.2)."""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Recon:
    """The 'Radar' of the suite. Handles signal analysis, spectrum scans, and Nmap pulses."""
    
    @staticmethod
    def get_scan_types():
        return ["Signal Pulse", "TCP Discovery", "UDP Stealth", "OS Introspection", "CVE Pulse"]

    @staticmethod
    def pulse_target(target, stype="Signal Pulse", on_output=None, on_complete=None):
        logger.info("recon", f"INITIATING_PULSE: {target} [TYPE={stype}]")
        
        cmds = {
            "Signal Pulse": f"nmap -sn {target}",
            "TCP Discovery": f"nmap -sV -T4 {target}",
            "UDP Stealth": f"nmap -sU {target}",
            "OS Introspection": f"nmap -O {target}",
            "CVE Pulse": f"nmap -sV --script=vulners {target}"
        }
        
        cmd = cmds.get(stype, f"nmap -sn {target}")
        runner.execute_task(f"RECON_{target}", cmd, callback=on_output)

    @staticmethod
    def parse_sighting(line):
        """Monitor logs for suspicious signal sightings."""
        if "up" in line.lower() and "Host" in line:
            return f"ACTVE_HOST_SIGHTED: {line.split(' ')[1]}"
        return None
