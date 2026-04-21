"""
Vulnerability Scanner Module — Enterprise Intelligence Build.
Handles Nuclei, Sqlmap, Nikto, and automated vulnerability verification.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target
from ai_engine.autoagent.registry import register_tool
import os

class VulnScanner(BaseModule):
    """The 'Spectre' engine for vulnerability detection."""
    
    def __init__(self):
        super().__init__(module_name="vuln_scanner")

    @register_tool("vuln_nuclei_scan")
    def nuclei_scan(self, target: str, tags: str = None, on_output=None):
        """
        Perform a Nuclei vulnerability scan on a target.
        Args:
            target: The target URL or IP.
            tags: Optional tags to filter templates (e.g., 'cve,crit').
        """
        if not validate_target(target): return
        
        self.log(f"INITIATING_NUCLEI_SCAN: {target}")
        nuclei = self.get_tool_path("nuclei")
        args = [nuclei, "-u", target, "-nc"] # -nc for no-color in terminal
        if tags:
            args.extend(["-tags", tags])
        
        return self.execute(f"NUCLEI_{target}", args, callback=on_output)

    @register_tool("vuln_sqlmap_scan")
    def sqlmap_scan(self, target: str, on_output=None):
        """
        Perform an automated SQL injection audit using Sqlmap.
        Args:
            target: The target URL.
        """
        if not validate_target(target): return
        
        self.log(f"INITIATING_SQLMAP_SCAN: {target}")
        sqlmap = self.get_tool_path("sqlmap")
        # Run in batch mode for autonomous flow
        args = [sqlmap, "-u", target, "--batch", "--random-agent", "--level=2"]
        return self.execute(f"SQLMAP_{target}", args, callback=on_output)

    @register_tool("vuln_nikto_scan")
    def nikto_scan(self, target: str, on_output=None):
        """
        Perform a web server vulnerability scan using Nikto.
        Args:
            target: The target host/URL.
        """
        if not validate_target(target): return
        
        self.log(f"INITIATING_NIKTO_SCAN: {target}")
        nikto = self.get_tool_path("nikto")
        args = [nikto, "-h", target]
        return self.execute(f"NIKTO_{target}", args, callback=on_output)

    def audit_target(self, target, on_output=None):
        """Perform a complete autonomous audit of a target."""
        from shadowcypher.core.hub import hub
        self.log(f"AUDIT_REQUESTED: {target}", "SYSTEM")
        return hub.dispatch_mission(f"Execute a high-intensity vulnerability audit and exploit verification on {target}")

    def shadow_zero_day_scan(self, target, on_output=None):
        """2026 Heuristic Scan: AI-driven zero-day detection via abnormal service behavior."""
        from shadowcypher.modules.deephat import deephat
        if on_output: on_output(f"[SCAN] INITIATING_SHADOW_ZERO_DAY_AUDIT: {target}...\n")
        
        desc = f"Analyze service responses for {target}. Detect non-standard buffer behavior and memory corruption indicators. Synthesize a proof-of-concept for discovered anomalies."
        
        # Forge the arsenal shards
        shards_str = deephat.forge_weapon(desc, category="audit")
        shards = [s.strip() for s in shards_str.split(",")]
        
        results = []
        for shard in shards:
            full_path = os.path.join("payloads", shard)
            res = deephat.execute_payload(full_path, on_output=on_output)
            results.append(res)
            
        return " | ".join(results)
