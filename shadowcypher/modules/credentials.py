"""
Credentials Module — Apex Intelligence Build.
Handles brute-force operations, hash identification, and macOS Keychain auditing.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine
import tempfile
import os

class Credentials(BaseModule):
    """The 'Identity' engine of ShadowCypher."""
    
    def __init__(self):
        super().__init__(module_name="credentials")

    def brute_force(self, target, service, user, wordlist, on_output=None):
        self.log(f"INITIATING_BRUTE_FORCE: {target} [{service}]")
        
        hydra = platform_engine.get_cmd("hydra")
        args = [hydra, "-l", user, "-P", wordlist, "-t", "4", target, service]
        return self.execute(f"HYDRA_{target}", args, callback=on_output)

    def identify_hash(self, hash_str):
        self.log("IDENTIFYING_HASH...")
        # Local tool attempt
        try:
            import subprocess
            return subprocess.check_output(["hashid", hash_str], text=True)
        except:
            return "HASHID_NOT_FOUND. AI_IDENTIFICATION_RECOMMENDED."

    def crack_hash(self, hash_str, htype, wordlist=None, on_output=None):
        wordlist = wordlist or self.get_tool_path("rockyou")
        self.log(f"HASH_CRACKING_MISSION: {htype}")
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hash") as tf:
            tf.write(hash_str)
            t_path = tf.name
            
        args = ["john", f"--format={htype}", f"--wordlist={wordlist}", t_path]
        return self.execute("JOHN", args, callback=on_output)

    def audit_macos_keychain(self, on_output=None):
        """macOS Specific: List or dump keychain details if permissions allow."""
        if not platform_engine.IS_MACOS:
            return "ERROR: Keychain audit only available on Darwin (macOS)."
            
        self.log("AUDITING_MACOS_KEYCHAIN", "AI")
        # 'security' is the macOS binary for keychain access
        return self.execute("KEYCHAIN_ENUM", ["security", "list-keychains"], callback=on_output)

    def ai_crack(self, hash_str, on_output=None):
        """Escalate hash cracking to the Swarm for pattern-based attacks."""
        from shadowcypher.core.hub import hub
        self.log("AI_HASH_RECOVERY_ENGAGED", "AI")
        return hub.register_mission(f"Recover the plaintext for the following hash: {hash_str}. Identify the format and perform semantic wordlist mutation.")
