"""
Credentials Module — Apex Intelligence Build.
Handles brute-force operations (hydra), hash cracking (hashcat/john),
hash identification, and macOS Keychain auditing.
"""

import tempfile
import os
from shadowcypher.core.module import BaseModule
from shadowcypher.core.platform import platform_engine


class Credentials(BaseModule):
    """The 'Identity' engine of ShadowCypher."""

    def __init__(self):
        super().__init__(module_name="credentials")

    # ── Hashcat Mode Mapping ──

    HASHCAT_MODES = {
        "md5": "0",
        "sha1": "100",
        "sha256": "1400",
        "sha512": "1700",
        "ntlm": "1000",
        "bcrypt": "3200",
        "sha512crypt": "1800",
        "md5crypt": "500",
        "wpa": "22000",
        "mysql": "300",
        "kerberos_tgs": "13100",
    }

    # ── Hydra (Brute Force) ──

    @staticmethod
    def hydra_attack(target, service, username="admin", passlist=None,
                     extra_args="", on_output=None, on_complete=None):
        """Launch a Hydra brute-force attack against a target service."""
        from shadowcypher.core.runner import runner
        wordlist = passlist or "/usr/share/wordlists/rockyou.txt"
        args = ["hydra", "-l", username, "-P", wordlist, "-t", "4"]
        if extra_args:
            import shlex
            args += shlex.split(extra_args)
        args += [target, service]
        return runner.execute_task(f"HYDRA_{target}", args, callback=on_output)

    def brute_force(self, target, service, user, wordlist, on_output=None):
        """Instance-method wrapper for hydra_attack."""
        return Credentials.hydra_attack(target, service, user, wordlist, on_output=on_output)

    # ── Hash Identification ──

    @staticmethod
    def identify_hash(hash_str):
        """Identify a hash format using hashid or nth."""
        import subprocess
        try:
            return subprocess.check_output(["hashid", hash_str], text=True, timeout=10)
        except FileNotFoundError:
            try:
                return subprocess.check_output(["nth", "--no-banner", "-t", hash_str], text=True, timeout=10)
            except Exception:
                return "HASH_ID_TOOLS_NOT_FOUND. Install hashid: pip install hashid"
        except Exception:
            return "HASHID_FAILED. AI identification recommended."

    # ── Hashcat (GPU Cracking) ──

    @staticmethod
    def hashcat_crack(hash_file, hash_type, wordlist=None, on_output=None, on_complete=None):
        """Crack a hash file using hashcat (GPU-accelerated)."""
        from shadowcypher.core.runner import runner
        wordlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        mode = Credentials.HASHCAT_MODES.get(hash_type, "0")
        args = ["hashcat", "-m", mode, "-a", "0", hash_file, wordlist, "--force", "--status"]
        return runner.execute_task("HASHCAT", args, callback=on_output)

    @staticmethod
    def hashcat_crack_string(hash_str, hash_type, wordlist=None, on_output=None, on_complete=None):
        """Crack a single hash string using hashcat."""
        # Write hash to temp file then crack
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hash") as tf:
            tf.write(hash_str)
            hash_file = tf.name
        return Credentials.hashcat_crack(hash_file, hash_type, wordlist, on_output, on_complete)

    @staticmethod
    def hashcat_benchmark(on_output=None, on_complete=None):
        """Run hashcat GPU benchmark to measure cracking speed."""
        from shadowcypher.core.runner import runner
        args = ["hashcat", "-b", "--force"]
        return runner.execute_task("HASHCAT_BENCH", args, callback=on_output)

    # ── John the Ripper (CPU Cracking) ──

    @staticmethod
    def john_crack(hash_file, wordlist=None, on_output=None, on_complete=None):
        """Crack a hash file using John the Ripper."""
        from shadowcypher.core.runner import runner
        wordlist = wordlist or "/usr/share/wordlists/rockyou.txt"
        args = ["john", f"--wordlist={wordlist}", hash_file]
        return runner.execute_task("JOHN", args, callback=on_output)

    @staticmethod
    def john_crack_string(hash_str, on_output=None, on_complete=None):
        """Crack a single hash string using John the Ripper."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hash") as tf:
            tf.write(hash_str)
            hash_file = tf.name
        return Credentials.john_crack(hash_file, on_output=on_output, on_complete=on_complete)

    # ── Instance methods (legacy compat) ──

    def crack_hash(self, hash_str, htype, wordlist=None, on_output=None):
        """Instance method for john cracking."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hash") as tf:
            tf.write(hash_str)
            t_path = tf.name
        args = ["john", f"--format={htype}", f"--wordlist={wordlist or self.get_tool_path('rockyou')}", t_path]
        return self.execute("JOHN", args, callback=on_output)

    def audit_macos_keychain(self, on_output=None):
        """macOS Specific: List or dump keychain details if permissions allow."""
        if not platform_engine.IS_MACOS:
            return "ERROR: Keychain audit only available on Darwin (macOS)."
        self.log("AUDITING_MACOS_KEYCHAIN", "AI")
        return self.execute("KEYCHAIN_ENUM", ["security", "list-keychains"], callback=on_output)

    def ai_crack(self, hash_str, on_output=None):
        """Escalate hash cracking to the Swarm for pattern-based attacks."""
        from shadowcypher.core.hub import hub
        self.log("AI_HASH_RECOVERY_ENGAGED", "AI")
        return hub.register_mission(
            f"Recover the plaintext for the following hash: {hash_str}. "
            "Identify the format and perform semantic wordlist mutation."
        )
