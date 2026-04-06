"""ShadowCypher Identity (Credentials) Engine — Absolute Sync (Build V28)."""

import os
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class Credentials:
    """The 'Identity' engine. Handles hash identification, cracking, and Hydra brute force."""
    
    @staticmethod
    def hydra_brute_force(target, service, username, wordlist, port=None, on_output=None, on_complete=None):
        """Perform a targeted brute force scan via Hydra."""
        port_arg = f"-s {port}" if port and port != "auto" else ""
        cmd = f"hydra -l {username} -P {wordlist} {port_arg} {target} {service}"
        runner.execute_task(f"HYDRA_{target}", cmd, callback=on_output)

    @staticmethod
    def identify_hash(hstring):
        os.system(f"hashid {hstring} > /tmp/hashid.txt")
        with open("/tmp/hashid.txt", "r") as f:
            return f.read()

    @staticmethod
    def crack_hash(hstring, htype, wordlist=None, on_output=None, on_complete=None):
        wlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        cmd = f"john --format={htype} --wordlist={wlist} {hstring}"
        runner.execute_task(f"HASH_CRACK_{htype}", cmd, callback=on_output)

    @staticmethod
    def hunt_credentials(query, on_output=None, on_complete=None):
        cmd = f"grep -r {query} wordlists/ 2>/dev/null || echo 'No matches found in local wordlists.'"
        runner.execute_task(f"CRED_HUNT_{query}", cmd, callback=on_output)

    @staticmethod
    def generate_wordlist(params, on_output=None, on_complete=None):
        cmd = f"cupp -i"
        runner.execute_task("WORDLIST_GEN", cmd, callback=on_output)

    # UI Backwards Compatibility Hooks
    @staticmethod
    def get_services(): return ["ssh", "ftp", "telnet", "mysql", "mssql", "rdp", "vnc", "http-get", "http-post"]
    @staticmethod
    def get_hash_formats(): return ["md5", "sha1", "sha256", "sha512", "ntlm", "raw-md5", "raw-sha1"]
