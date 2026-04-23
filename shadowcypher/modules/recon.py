"""
Recon Module — Enterprise Sovereign Build.
High-fidelity cross-platform discovery and service mapping.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.sanitize import validate_target
import re
import subprocess

class Recon(BaseModule):
    """The 'Signal' engine of ShadowCypher."""
    
    def __init__(self):
        super().__init__(module_name="recon")
        self.gateway = self._detect_gateway()

    def _detect_gateway(self):
        try:
            cmd = platform_engine.get_net_info_cmd()
            res = subprocess.check_output(cmd, text=True)
            
            # Platform-Specific Parsing
            if platform_engine.IS_LINUX:
                match = re.search(r"default via ([\d\.]+)", res)
            elif platform_engine.IS_MACOS:
                match = re.search(r"default\s+([\d\.]+)", res)
            elif platform_engine.IS_WINDOWS:
                match = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+([\d\.]+)", res)
            else: match = None
            
            return match.group(1) if match else "127.0.0.1"
        except (subprocess.CalledProcessError, OSError, AttributeError):
            return "127.0.0.1"

    def pulse_target(self, target, stype="Quick Port Scan", on_output=None):
        if not validate_target(target): return
        self.log(f"PULSING_TARGET: {target} [OS={platform_engine.SYSTEM}]")
        
        nmap = platform_engine.get_cmd("nmap")
        
        flag_map = {
            "Quick Port Scan": ["-F"],
            "Full Port Scan": ["-p-"],
            "OS Detection": ["-O"],
            "Service Fingerprint": ["-sV"],
            "Deep Recon": ["-Pn", "-sV", "-sC", "-O"]
        }
        flags = flag_map.get(stype, [])
        return self.execute(f"PULSE_{target}", [nmap] + flags + [target], callback=on_output)

    def quick_scan(self, target, on_output=None):
        """Standard AI-driven quick scan."""
        return self.pulse_target(target, "Quick Port Scan", on_output=on_output)

    def deep_recon(self, target, on_output=None):
        """High-intensity service and script enumeration."""
        return self.pulse_target(target, "Deep Recon", on_output=on_output)

    def ai_recon(self, target, on_output=None):
        from shadowcypher.core.hub import hub
        return hub.dispatch_mission(f"Map the network surface of {target}. Use OS-specific reconnaissance tools for {platform_engine.SYSTEM}.")
