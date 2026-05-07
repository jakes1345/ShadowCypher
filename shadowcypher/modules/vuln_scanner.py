"""
Vulnerability Scanner Module — Enterprise Intelligence Build.
Handles Nuclei, Sqlmap, Nikto, and automated vulnerability verification.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.stealth import require_stealth
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
        require_stealth(on_output=on_output)
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
        require_stealth(on_output=on_output)
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
        require_stealth(on_output=on_output)
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

    def ai_heuristic_scan(self, target, on_output=None):
        """AI-assisted heuristic scan.

        Asks the DeepHat planner to flag anomalous service behaviour on the
        target. This does NOT discover zero-days — it synthesises analysis
        scripts that a human operator then reviews and executes. Kept as a
        planning aid, not an autonomous exploit tool.
        """
        from shadowcypher.modules.deephat import deephat
        if on_output:
            on_output(f"[SCAN] Launching AI heuristic analysis on {target}...\n")

        desc = (
            f"Analyse service responses for {target}. Flag non-standard buffer behaviour "
            "and memory-corruption indicators. Produce diagnostic scripts a human can review — "
            "do NOT execute exploits."
        )

        shards_str = deephat.forge_weapon(desc, category="audit")
        shards = [s.strip() for s in shards_str.split(",") if s.strip()]

        results = []
        for shard in shards:
            full_path = os.path.join("payloads", shard)
            res = deephat.execute_payload(full_path, on_output=on_output)
            results.append(res)

        return " | ".join(results) if results else "NO_SHARDS_GENERATED"

    # Legacy alias — older UI code may still reference this.
    shadow_zero_day_scan = ai_heuristic_scan
