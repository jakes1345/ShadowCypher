import subprocess
import shlex
import os
import tempfile
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger


class Credentials:
    """The 'Identity' engine. Handles hash identification, cracking, and Hydra brute force."""

    @staticmethod
    def hydra_brute_force(
        target, service, username, wordlist, port=None, on_output=None, on_complete=None
    ):
        """Perform a targeted brute force scan via Hydra."""
        # Use standard hydra or medusa based on availability
        args = ["hydra", "-l", username, "-P", wordlist]
        if port and port != "auto":
            args += ["-s", str(port)]
        args += [target, service, "-t", "4", "-vV"]
        return runner.execute_task(f"HYDRA_{target}", args, callback=on_output)

    @staticmethod
    def identify_hash(hstring):
        """Identify the hash type using 'hashid' or 'hash-identifier'."""
        try:
            # We must quote hstring properly to avoid shell injection if using check_output
            # But here we pass it as a direct argument which is safer.
            result = subprocess.check_output(
                ["hashid", "-m", "-j", hstring], text=True, timeout=10
            )
            return result
        except FileNotFoundError:
            return "Local hash-identification library (hashid) missing. AI fallback initiated."
        except Exception as e:
            return f"ID_FAILURE: {e}"

    @staticmethod
    def crack_hash(hstring, htype, wordlist=None, on_output=None, on_complete=None):
        """John The Ripper bridge with automatic temp file lifecycle management."""
        wlist = wordlist or "/usr/share/wordlists/rockyou.txt"

        temp_hash = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".hash")
        temp_hash.write(hstring)
        temp_hash.close()
        temp_path = temp_hash.name

        if on_output:
            on_output(f"[IDENTITY] ISO_HASH_STREAM_CREATED: {temp_path}")

        def _cleanup_callback(line):
            if on_output:
                on_output(line)
            if "[MISSION_EXIT_CODE:" in line:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

        args = ["john", f"--format={htype}", f"--wordlist={wlist}", temp_path]
        return runner.execute_task(
            f"HASH_CRACK_{htype}", args, callback=_cleanup_callback
        )

    @staticmethod
    def hunt_credentials(query, on_output=None, on_complete=None):
        """Search for compromised credentials in local wordlists/leaks."""
        wordlist_path = "/usr/share/wordlists/"
        if not os.path.exists(wordlist_path):
            wordlist_path = "wordlists/"

        cmd = f"grep -ri {shlex.quote(query)} {wordlist_path} 2>/dev/null || echo 'No matches found in standard wordlists.'"
        return runner.execute_task_shell(f"CRED_HUNT_{query}", cmd, callback=on_output)

    @staticmethod
    def get_services():
        return [
            "ssh",
            "ftp",
            "telnet",
            "mysql",
            "mssql",
            "rdp",
            "vnc",
            "http-get",
            "http-post",
            "smtp",
        ]

    @staticmethod
    def get_hash_formats():
        return [
            "md5",
            "sha1",
            "sha256",
            "sha512",
            "ntlm",
            "raw-md5",
            "raw-sha1",
            "crypt",
        ]

    @staticmethod
    def hashcat_benchmark(on_output=None, on_complete=None):
        return runner.execute_task(
            "HASHCAT_BENCH", ["hashcat", "-b"], callback=on_output
        )
