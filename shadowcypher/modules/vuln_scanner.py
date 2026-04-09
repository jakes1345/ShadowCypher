"""
Vulnerability Scanner Module — Apex Intelligence Build.
Handles Nuclei, Sqlmap, Nikto, and automated vulnerability verification.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target

class VulnScanner(BaseModule):
    """The 'Spectre' engine for vulnerability detection."""
    
    def __init__(self):
        super().__init__(module_name="vuln_scanner")

    def nuclei_scan(self, target, tags=None, on_output=None):
        if not validate_target(target): return
        
        self.log(f"INITIATING_NUCLEI_SCAN: {target}")
        nuclei = self.get_tool_path("nuclei")
        args = [nuclei, "-u", target, "-nc"] # -nc for no-color in terminal
        if tags:
            args.extend(["-tags", tags])
        
        return self.execute(f"NUCLEI_{target}", args, callback=on_output)

    def sqlmap_scan(self, target, on_output=None):
        if not validate_target(target): return
        
        self.log(f"INITIATING_SQLMAP_SCAN: {target}")
        sqlmap = self.get_tool_path("sqlmap")
        # Run in batch mode for autonomous flow
        args = [sqlmap, "-u", target, "--batch", "--random-agent", "--level=2"]
        return self.execute(f"SQLMAP_{target}", args, callback=on_output)

    def nikto_scan(self, target, on_output=None):
        if not validate_target(target): return
        
        self.log(f"INITIATING_NIKTO_SCAN: {target}")
        nikto = self.get_tool_path("nikto")
        args = [nikto, "-h", target]
        return self.execute(f"NIKTO_{target}", args, callback=on_output)

    def audit_target(self, target, on_output=None):
        """Perform a complete autonomous audit of a target."""
        from shadowcypher.core.hub import hub
        self.log(f"AUDIT_REQUESTED: {target}", "SYSTEM")
        return hub.register_mission(f"Execute a high-intensity vulnerability audit and exploit verification on {target}")
