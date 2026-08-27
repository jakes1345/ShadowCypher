"""
Vulnerability Scanner Module — Apex Intelligence Build.
Handles Nuclei, Sqlmap, Nikto, and automated vulnerability verification.
"""


try:
    from ai_engine.autoagent.registry import register_tool
except ImportError as _ai_engine_err:
    def register_tool(name):
        def _decorator(func):
            def _missing(*args, **kwargs):
                raise ImportError(
                    f"Tool '{name}' requires the ai_engine package which is not installed. "
                    "Install ai_engine to use tool registration."
                ) from _ai_engine_err
            return _missing
        return _decorator

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target


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
        """Combined nikto + nuclei + nmap service scan for vulnerability detection."""
        import shutil
        if on_output: on_output(f"[SCAN] FULL_AUDIT: {target}\n")
        out = lambda x: on_output(x.strip() + "\n") if on_output and x.strip() else None
        if shutil.which("nikto"):
            self.nikto_scan(target, on_output=out)
        else:
            if on_output: on_output("[WARN] nikto not found\n")
        if shutil.which("nuclei"):
            self.nuclei_scan(target, tags="cve,vuln", on_output=out)
        else:
            if on_output: on_output("[WARN] nuclei not found\n")
        if shutil.which("nmap"):
            from shadowcypher.modules.network import Network
            Network.service_fingerprint(target, on_output=out)
