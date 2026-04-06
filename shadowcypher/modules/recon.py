"""ShadowCypher Network Recon — Auto-Inspect Router Module."""

import subprocess
import shutil
import re
from shadowcypher.core.logger import logger

class RouterInspector:
    """Pro-grade network inspector for gateway discovery and OS fingerprinting."""
    def __init__(self):
        self.gateway = self._find_gateway()

    def _find_gateway(self):
        """Discover the default gateway [Router IP]."""
        try:
            # High-fidelity discovery via ip route
            result = subprocess.check_output(["ip", "route", "show", "default"]).decode()
            match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", result)
            if match:
                gw = match.group(1)
                logger.info("recon", f"Gateway discovered: {gw}")
                return gw
        except Exception:
            logger.error("recon", "Failed to discover default gateway.")
        return None

    def auto_inspect(self):
        """Perform a deep-pulse scan of the router for OS and specs."""
        if not self.gateway:
            return "ERROR: GATEWAY_NOT_FOUND"

        if not shutil.which("nmap"):
            return "ERROR: NMAP_NOT_INSTALLED"

        # TACTICAL: Service Fingerprinting [Fast pass]
        logger.info("recon", f"Auto-inspecting Gateway: {self.gateway}")
        try:
            # -sV: version, -T4: fast, --top-ports 20
            cmd = ["nmap", "-sV", "-T4", "--top-ports", "20", self.gateway]
            output = subprocess.check_output(cmd).decode()
            
            # Extract vital components
            summary = self._parse_nmap(output)
            return summary
        except Exception as e:
            return f"ERROR: SCAN_FAILURE [{str(e)}]"

    def _parse_nmap(self, output):
        """Extract OS and hardware signatures from nmap output."""
        # Simple extraction for now - could be a more complex parser
        lines = output.split('\n')
        services = []
        os_guess = "Linux/Embedded"
        
        for line in lines:
            if "/tcp" in line and "open" in line:
                services.append(line.strip())
            if "Service Info: OS:" in line:
                match = re.search(r"OS: ([^;]+)", line)
                if match: os_guess = match.group(1)

        summary = f"TARGET: {self.gateway}\n"
        summary += f"ESTIMATED OS: {os_guess}\n"
        summary += f"VITAL_SERVICES:\n" + "\n".join(services) if services else "No open common ports."
        return summary
