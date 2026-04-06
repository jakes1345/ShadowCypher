"""ShadowCypher Identity (Credentials) Engine — High-Fidelity Sync (V23.2)."""

import os
import subprocess
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class Credentials:
    """The 'Identity' engine. Handles hash identification, cracking, and leak searches."""
    
    @staticmethod
    def identify_hash(hstring):
        """Identify a hash format using hashid or similar."""
        try:
            return subprocess.check_output(f"hashid {hstring}", shell=True, text=True)
        except:
            return "Hash format could not be identified automatically."

    @staticmethod
    def crack_hash(hstring, htype, wordlist=None, on_output=None, on_complete=None):
        """Crack a hash using John the Ripper or Hashcat."""
        wlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        cmd = f"john --format={htype} --wordlist={wlist} {hstring}"
        runner.execute_task(f"HASH_CRACK_{htype}", cmd, callback=on_output)

    @staticmethod
    def hunt_credentials(query, on_output=None, on_complete=None):
        """Hunt for credentials in local dbs or searches."""
        cmd = f"grep -r {query} wordlists/ 2>/dev/null || echo 'No matches found in local wordlists.'"
        runner.execute_task(f"CRED_HUNT_{query}", cmd, callback=on_output)

    @staticmethod
    def generate_wordlist(params, on_output=None, on_complete=None):
        """Perform a targeted wordlist generation (e.g. cupp)."""
        cmd = f"cupp -i" # Note: cupp is interactive usually, but runner handles stdin if needed
        runner.execute_task("WORDLIST_GEN", cmd, callback=on_output)
