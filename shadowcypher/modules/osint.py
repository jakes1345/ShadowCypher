"""ShadowCypher OSINT (Identity) Engine — High-Fidelity Build (V23.2)."""

import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class OSINT:
    """The 'Identity' engine. Handles WHOIS, DNS, and Shodan probes."""
    
    @staticmethod
    def get_search_types():
        return ["WHOIS Analysis", "DNS Brute", "Subdomain Sweep", "Shodan Core", "Social Intel"]

    @staticmethod
    def locate_target(target, stype="WHOIS Analysis", on_output=None, on_complete=None):
        logger.info("osint", f"LOCATING_TARGET: {target} [TYPE={stype}]")
        
        cmds = {
            "WHOIS Analysis": f"whois {target}",
            "DNS Brute": f"dnsrecon -d {target}",
            "Subdomain Sweep": f"subfinder -d {target}",
            "Shodan Core": f"shodan host {target}"
        }
        
        cmd = cmds.get(stype, f"whois {target}")
        runner.execute_task(f"OSINT_{target}", cmd, callback=on_output)

    @staticmethod
    def identify_identity(query, on_output=None, on_complete=None):
        """Perform a deep-identity search on a username/email."""
        # Simple OSINT-lite logic (searching known leaks or sites)
        cmd = f"sherlock {query}"
        runner.execute_task(f"IDENTITY_SEARCH_{query}", cmd, callback=on_output)
