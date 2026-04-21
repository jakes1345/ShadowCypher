"""
ShadowCypher Deep OSINT & Identity Correlation Engine.
Integrates Sherlock, Holehe, and Custom Scrapers for Multi-Platform Traversal.
"""

import os
import subprocess
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

from ai_engine.autoagent.registry import register_tool

class DeepOSINT:
    """The 'Omniscience' engine. Cross-correlates digital shadows."""

    @staticmethod
    @register_tool("osint_social_footprint")
    def social_footprint(username: str, on_output=None):
        """
        Search for social media accounts across 300+ platforms using the Sherlock engine.
        Args:
            username: The target username to investigate.
        """
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        # Resolve Tactical VENV Python
        python_bin = os.path.join(project_root, "ai_engine", "meta-venv", "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = os.path.join(project_root, "venv", "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = "python3"

        sherlock_root = os.path.join(project_root, "tools", "sherlock")
        
        # Check if dir exists
        if not os.path.exists(sherlock_root):
             return "[ERROR] SHERLOCK_NOT_STAGED. Run tools/install_osint.sh"

        args = [python_bin, "-m", "sherlock_project", username, "--timeout", "10", "--no-color"]
        return runner.execute_task(f"SHERLOCK_{username}", args, callback=on_output)

    @staticmethod
    @register_tool("osint_email_audit")
    def email_audit(email: str, on_output=None):
        """
        Check if an email address is registered on 100+ websites using the Holehe engine.
        Args:
            email: The target email address to audit.
        """
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        # Resolve Tactical VENV Python
        python_bin = os.path.join(project_root, "ai_engine", "meta-venv", "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = os.path.join(project_root, "venv", "bin", "python3")
        if not os.path.exists(python_bin):
            python_bin = "python3"

        holehe_path = os.path.join(project_root, "tools", "holehe")
        
        if not os.path.exists(holehe_path):
            return "[ERROR] HOLEHE_NOT_STAGED."

        args = [python_bin, os.path.join(holehe_path, "holehe", "core.py"), email]
        return runner.execute_task(f"HOLEHE_{email}", args, callback=on_output)

    @staticmethod
    @register_tool("osint_leak_check")
    def leak_check(query: str, on_output=None):
        """
        Check for publicly leaked credentials in local databases.
        Args:
            query: The email or username to search for in leaks.
        """
        if on_output: on_output(f"[INTEL] SEARCHING_LOCAL_LEAK_DATABASE: {query}")
        from shadowcypher.modules.credentials import Credentials
        creds = Credentials()
        result = creds.identify_hash(query)
        if on_output: on_output(f"[INTEL] RESULT: {result}")
        return result

    @staticmethod
    def steam_correlate(steam_id, on_output=None):
        """Correlate SteamID to other platform aliases (Scraper)."""
        if on_output: on_output(f"[OSINT] CORRELATING_STEAM_ID: {steam_id}")
        return DeepOSINT.social_footprint(steam_id, on_output=on_output)

    @staticmethod
    def ghunt_pivot(email, on_output=None):
        """Perform elite Google ecosystem OSINT using GHunt."""
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        path = os.path.join(project_root, "tools", "elite", "GHunt", "main.py")
        
        if not os.path.exists(path):
            if on_output: on_output("[ERROR] GHUNT_NOT_STAGED.")
            return

        args = ["python3", path, "email", email]
        logger.info("osint", f"GHunt Pivot: {email}")
        return runner.execute_task(f"GHUNT_{email}", args, callback=on_output)

    @staticmethod
    def wayback_recon(domain, on_output=None):
        """Perform passive reconnaissance using the Wayback Machine CDX API."""
        import requests
        import re
        if on_output: on_output(f"[OSINT] INITIATING_WAYBACK_RECON: {domain}")
        
        url = f"http://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&collapse=urlkey&limit=1000"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                if on_output: on_output(f"Wayback Error: {response.status_code}")
                return
            
            data = response.json()
            if len(data) <= 1:
                if on_output: on_output("No historical data found.")
                return
            
            subdomains = set()
            for entry in data[1:]:
                original_url = entry[2]
                match = re.search(r'https?://([^/]+)', original_url)
                if match: subdomains.add(match.group(1))
            
            if on_output:
                on_output(f"Wayback Recon for {domain}:\n")
                on_output(f"- Subdomains Found: {len(subdomains)}\n")
                for s in list(subdomains)[:15]:
                    on_output(f"  [+] {s}\n")
        except Exception as e:
            if on_output: on_output(f"Wayback API Error: {e}")
