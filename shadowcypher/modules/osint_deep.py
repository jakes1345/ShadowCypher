"""
ShadowCypher Deep OSINT & Identity Correlation Engine.
Integrates Sherlock, Holehe, and Custom Scrapers for Multi-Platform Traversal.
"""

import os
import subprocess
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class DeepOSINT:
    """The 'Omniscience' engine. Cross-correlates digital shadows."""

    @staticmethod
    def social_footprint(username, on_output=None):
        """Search for social media accounts via Sherlock."""
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        sherlock_path = os.path.join(project_root, "tools", "sherlock", "sherlock")
        
        # Check if dir exists
        if not os.path.exists(sherlock_path):
             return "[ERROR] SHERLOCK_NOT_STAGED. Run tools/install_osint.sh"

        args = ["python3", "-m", "sherlock", username, "--timeout", "10", "--no-color"]
        # We need to run from the sherlock dir for it to work as a module sometimes
        cwd = os.path.join(project_root, "tools", "sherlock")
        return runner.execute_task(f"SHERLOCK_{username}", args, callback=on_output)

    @staticmethod
    def email_audit(email, on_output=None):
        """Check if an email is registered on 100+ sites via Holehe."""
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        holehe_path = os.path.join(project_root, "tools", "holehe")
        
        if not os.path.exists(holehe_path):
            return "[ERROR] HOLEHE_NOT_STAGED."

        args = ["python3", os.path.join(holehe_path, "holehe", "core.py"), email]
        return runner.execute_task(f"HOLEHE_{email}", args, callback=on_output)

    @staticmethod
    def steam_correlate(steam_id, on_output=None):
        """Correlate SteamID to other platform aliases (Scraper)."""
        if on_output: on_output(f"[OSINT] CORRELATING_STEAM_ID: {steam_id}")
        # Custom Logic: Scrape steamid.uk or similar if possible
        # For now, we search for the ID / Username in general OSINT
        return DeepOSINT.social_footprint(steam_id, on_output=on_output)

    @staticmethod
    def leak_check(query, on_output=None):
        """Check for publicly leaked credentials (Local-DB check)."""
        if on_output: on_output(f"[INTEL] SEARCHING_LOCAL_LEAK_DATABASE: {query}")
        from shadowcypher.modules.credentials import Credentials
        creds = Credentials()
        result = creds.identify_hash(query)
        if on_output: on_output(f"[INTEL] RESULT: {result}")
        return result
