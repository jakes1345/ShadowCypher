"""ShadowCypher Vulnerability Pulsing Engine — Pure Functional Build (V22.1)."""

import subprocess
import os
import re
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class VulnScanner:
    """The 'Radar' of the suite. Integrates Nmap/Vulners/NSE for real-time sightings."""
    
    @staticmethod
    def get_scan_types():
        return ["Quick Pulse", "Full Service Scan", "Vulnerability Search (Vulners)", "UDP Scan", "Stealth Recon"]

    @staticmethod
    def pulse_target(target, scan_type="Quick Pulse", on_output=None, on_complete=None):
        """Perform a deep-pulse vulnerability scan on a target."""
        logger.info("vuln", f"INITIATING_PULSE: {target} [TYPE={scan_type}]")
        
        # Mapping tactical types to Nmap flags
        flags = {
            "Quick Pulse": "-F",
            "Full Service Scan": "-sV -p-",
            "Vulnerability Search (Vulners)": "-sV --script=vulners",
            "UDP Scan": "-sU -F",
            "Stealth Recon": "-sS -O"
        }
        
        nmap_flag = flags.get(scan_type, "-F")
        cmd = f"nmap {nmap_flag} {target}"
        
        # Use the universal runner for non-blocking execution and UI logging
        runner.execute_task(f"VULN_SCAN_{target}", cmd, callback=on_output)

    @staticmethod
    def extract_cves(text):
        """Parse Nmap/Vulners output for critical CVE sightings."""
        cves = re.findall(r"CVE-\d{4}-\d+", text)
        return list(set(cves))

    @staticmethod
    def generate_report(target, text):
        """Save a tactical report to the reports directory."""
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/vuln_report_{target}.txt"
        with open(report_path, "w") as f:
            f.write(text)
        return report_path
