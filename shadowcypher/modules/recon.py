import subprocess
import re
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_target

class Recon:
    """The 'Signal' engine. Handles port scanning, discovery, and path tracing."""

    def __init__(self):
        self.gateway = self._detect_gateway()
        self.subnet = self._detect_subnet()
        self.scans = []

    def _detect_gateway(self):
        """Dynamic Gateway Detection — Hardened Logic."""
        try:
            # Parse 'ip route' for default gateway
            res = subprocess.check_output(["ip", "route", "show", "default"], text=True)
            match = re.search(r"default via ([\d\.]+)", res)
            if match:
                return match.group(1)
        except Exception: pass
        return "127.0.0.1"

    def _detect_subnet(self):
        """Dynamic Subnet Detection for host discovery."""
        try:
            res = subprocess.check_output(["ip", "addr", "show"], text=True)
            # Find the primary interface subnet
            match = re.search(r"inet ([\d\.]+/[\d]+) brd", res)
            if match:
                return match.group(1)
        except Exception: pass
        return "192.168.1.0/24"

    @staticmethod
    def get_scan_types():
        return ["Quick Port Scan", "Full Port Scan", "UDP Scan", "OS Detection", "Service Fingerprint"]

    @staticmethod
    def pulse_target(target, stype="Quick Port Scan", on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        logger.info("recon", f"PULSING_TARGET: {target} [TYPE={stype}]")

        flag_map = {
            "Quick Port Scan": ["-F"],
            "Full Port Scan": ["-p-"],
            "UDP Scan": ["-sU"],
            "OS Detection": ["-O"],
            "Service Fingerprint": ["-sV"],
        }
        flags = flag_map.get(stype, [])
        return runner.execute_task(f"RECON_{target}", ["nmap"] + flags + [target], callback=on_output)

    @staticmethod
    def traceroute(target, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        return runner.execute_task(f"TRACE_{target}", ["traceroute", target], callback=on_output)

    def discover_hosts(self, on_output=None, on_complete=None):
        """Dynamic Subnet Host Discovery."""
        target_subnet = self.subnet
        if on_output: on_output(f"[RECON] INITIATING_NETWORK_SWEEP_ON: {target_subnet}")
        return runner.execute_task("HOST_DISCOVERY", ["nmap", "-sn", target_subnet], callback=on_output)

    def auto_inspect(self):
        """Dynamic nmap service scan on the detected gateway."""
        try:
            return subprocess.check_output(["nmap", "-sV", self.gateway], text=True, timeout=60)
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def ai_recon(target, on_output=None):
        """Advanced AI-Augmented Reconnaissance using the Masterclass loop."""
        from shadowcypher.ai.orchestrator import AIOrchestrator
        logger.info("ai", f"INITIATING_AI_RECON_ON: {target}")
        if on_output: 
            on_output(f"[AI] INITIATING_DEEPHAT_RECON_FOR: {target}")
            on_output("[AI] ACTIVATING_SHADOW_WRAITH_STEALTH_SHIELD...")
        orch = AIOrchestrator()
        query = f"Provide a complete vulnerability analysis and scan for {target}. Start with stealth check."
        return orch.execute_query(query, callback=on_output)
