"""Credential attacks module — hydra brute force, john the ripper, hashcat GPU cracking."""

import os
import tempfile
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
from shadowcypher.core.sanitize import quote, validate_target, validate_port, validate_filepath


_NOOP = lambda x: None


class Credentials:
    """Real credential attack implementations using hydra, john, and hashcat."""

    # ──────────────────────────────────────────────────────────────────
    # HYDRA — Network brute force
    # ──────────────────────────────────────────────────────────────────

    HYDRA_SERVICES = frozenset({
        "ssh", "ftp", "http-get", "http-post-form", "rdp", "smb",
        "mysql", "postgres", "vnc", "telnet", "pop3", "imap", "smtp",
    })

    @staticmethod
    def hydra_attack(target: str, service: str, username: str = None,
                     userlist: str = None, passlist: str = None,
                     threads: int = 16, extra_args: str = "",
                     on_output=None, on_complete=None) -> int:
        """Run hydra brute-force attack against a network service."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1

        if service not in Credentials.HYDRA_SERVICES:
            (on_output or _NOOP)(f"[ERROR] Unsupported service: {service}\n")
            (on_complete or _NOOP)(1)
            return -1

        hydra = config.get_tool_path("hydra")
        if passlist is None:
            passlist = config.get_wordlist_path()

        user_arg = ""
        if username:
            user_arg = f"-l {quote(username)}"
        elif userlist:
            user_arg = f"-L {quote(userlist)}"
        else:
            user_arg = "-l admin"

        threads = max(1, min(int(threads), 64))

        cmd = f"{quote(hydra)} {user_arg} -P {quote(passlist)} -t {threads} -f -vV {extra_args} {quote(target)} {service}"
        logger.info("credentials", f"Hydra attack: {service}@{target}", username=username or "list")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def hydra_ssh(target: str, username: str = "root", passlist: str = None,
                  port: int = 22, on_output=None, on_complete=None) -> int:
        """SSH-specific hydra brute force."""
        if not validate_port(port):
            (on_output or _NOOP)(f"[ERROR] Invalid port: {port}\n")
            (on_complete or _NOOP)(1)
            return -1
        return Credentials.hydra_attack(
            target, "ssh", username=username, passlist=passlist,
            extra_args=f"-s {int(port)}", on_output=on_output, on_complete=on_complete
        )

    @staticmethod
    def hydra_ftp(target: str, username: str = "anonymous", passlist: str = None,
                  on_output=None, on_complete=None) -> int:
        """FTP-specific hydra brute force."""
        return Credentials.hydra_attack(
            target, "ftp", username=username, passlist=passlist,
            on_output=on_output, on_complete=on_complete
        )

    @staticmethod
    def hydra_http(target: str, path: str = "/login", method: str = "post",
                   username: str = "admin", passlist: str = None,
                   form_params: str = "username=^USER^&password=^PASS^:Invalid",
                   on_output=None, on_complete=None) -> int:
        """HTTP form brute force."""
        service = f"http-{method}-form"
        extra = f'{quote(path)}:{form_params}'
        return Credentials.hydra_attack(
            target, service, username=username, passlist=passlist,
            extra_args=f'"{extra}"', on_output=on_output, on_complete=on_complete
        )

    # ──────────────────────────────────────────────────────────────────
    # JOHN THE RIPPER — Offline hash cracking
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def john_crack(hash_file: str, wordlist: str = None, format: str = None,
                   rules: str = None, on_output=None, on_complete=None) -> int:
        """Crack hashes with John the Ripper."""
        if not validate_filepath(hash_file):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {hash_file}\n")
            (on_complete or _NOOP)(1)
            return -1

        john = config.get_tool_path("john")
        if wordlist is None:
            wordlist = config.get_wordlist_path()

        args = [quote(john)]
        if wordlist:
            args.append(f"--wordlist={quote(wordlist)}")
        if format:
            args.append(f"--format={quote(format)}")
        if rules:
            args.append(f"--rules={quote(rules)}")
        args.append(quote(hash_file))

        cmd = " ".join(args)
        logger.info("credentials", f"John crack: {hash_file}", format=format)
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def john_crack_string(hash_string: str, format: str = None, wordlist: str = None,
                          on_output=None, on_complete=None) -> int:
        """Crack a single hash string (writes to temp file first)."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".hash", delete=False, prefix="sc_")
        tmp.write(hash_string.strip() + "\n")
        tmp.close()

        def _on_complete(rc):
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            if on_complete:
                on_complete(rc)

        return Credentials.john_crack(
            tmp.name, wordlist=wordlist, format=format,
            on_output=on_output, on_complete=_on_complete
        )

    @staticmethod
    def john_show(hash_file: str) -> str:
        """Show previously cracked passwords."""
        if not validate_filepath(hash_file):
            return f"Invalid file path: {hash_file}"
        john = config.get_tool_path("john")
        output, _ = runner.run_sync(f"{quote(john)} --show {quote(hash_file)}", timeout=10, shell=True)
        return output

    @staticmethod
    def john_unshadow(passwd_file: str, shadow_file: str, output_file: str = None) -> str:
        """Merge /etc/passwd and /etc/shadow for John."""
        if output_file is None:
            output_file = tempfile.mktemp(suffix=".unshadow", prefix="sc_")
        cmd = f"unshadow {quote(passwd_file)} {quote(shadow_file)} > {quote(output_file)}"
        output, rc = runner.run_sync(cmd, timeout=10, shell=True)
        if rc == 0:
            return output_file
        return f"Error: {output}"

    # ──────────────────────────────────────────────────────────────────
    # HASHCAT — GPU-accelerated hash cracking
    # ──────────────────────────────────────────────────────────────────

    HASH_MODES = {
        "md5": 0,
        "sha1": 100,
        "sha256": 1400,
        "sha512": 1800,
        "ntlm": 1000,
        "bcrypt": 3200,
        "sha512crypt": 1800,
        "md5crypt": 500,
        "wpa": 22000,
        "mysql": 300,
        "mssql": 1731,
        "kerberos_tgs": 13100,
        "kerberos_as": 18200,
    }

    @staticmethod
    def hashcat_crack(hash_file: str, hash_type: str = "md5", wordlist: str = None,
                      attack_mode: int = 0, rules: str = None,
                      workload: int = 3, on_output=None, on_complete=None) -> int:
        """GPU-accelerated hash cracking with hashcat.

        attack_mode: 0=dictionary, 1=combination, 3=brute-force, 6=hybrid dict+mask, 7=hybrid mask+dict
        workload: 1=low, 2=default, 3=high, 4=nightmare
        """
        if not validate_filepath(hash_file):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {hash_file}\n")
            (on_complete or _NOOP)(1)
            return -1

        hashcat = config.get_tool_path("hashcat")
        mode = Credentials.HASH_MODES.get(hash_type.lower(), 0)

        if wordlist is None:
            wordlist = config.get_wordlist_path()

        attack_mode = max(0, min(int(attack_mode), 7))
        workload = max(1, min(int(workload), 4))

        args = [
            quote(hashcat),
            f"-m {mode}",
            f"-a {attack_mode}",
            f"-w {workload}",
            "--force",
            "--status",
            "--status-timer=5",
            "-o", quote(f"{hash_file}.cracked"),
            quote(hash_file),
        ]

        if attack_mode == 0:
            args.append(quote(wordlist))
        if rules:
            args.extend(["-r", quote(rules)])

        cmd = " ".join(args)
        logger.info("credentials", f"Hashcat: mode={mode} ({hash_type})", attack=attack_mode)
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def hashcat_crack_string(hash_string: str, hash_type: str = "md5", wordlist: str = None,
                              on_output=None, on_complete=None) -> int:
        """Crack a single hash with hashcat."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".hash", delete=False, prefix="sc_hc_")
        tmp.write(hash_string.strip() + "\n")
        tmp.close()

        def _on_complete(rc):
            cracked_file = f"{tmp.name}.cracked"
            if os.path.exists(cracked_file):
                with open(cracked_file) as f:
                    result = f.read()
                if on_output and result.strip():
                    on_output(f"\n[CRACKED] {result}\n")
                try:
                    os.unlink(cracked_file)
                except OSError:
                    pass
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            if on_complete:
                on_complete(rc)

        return Credentials.hashcat_crack(
            tmp.name, hash_type=hash_type, wordlist=wordlist,
            on_output=on_output, on_complete=_on_complete
        )

    @staticmethod
    def hashcat_benchmark(on_output=None, on_complete=None) -> int:
        """Run hashcat benchmark on all hash types."""
        hashcat = config.get_tool_path("hashcat")
        cmd = f"{quote(hashcat)} -b --force"
        logger.info("credentials", "Hashcat benchmark started")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def identify_hash(hash_string: str) -> str:
        """Try to identify a hash type based on length and format."""
        h = hash_string.strip()
        length = len(h)

        identifications = []
        hex_lower = all(c in "0123456789abcdef" for c in h.lower())
        hex_upper = all(c in "0123456789ABCDEF" for c in h)

        if length == 32 and hex_lower:
            identifications.append("MD5 (hashcat mode: 0)")
        if length == 40 and hex_lower:
            identifications.append("SHA-1 (hashcat mode: 100)")
        if length == 64 and hex_lower:
            identifications.append("SHA-256 (hashcat mode: 1400)")
        if length == 128 and hex_lower:
            identifications.append("SHA-512 (hashcat mode: 1800)")
        if h.startswith("$2a$") or h.startswith("$2b$") or h.startswith("$2y$"):
            identifications.append("bcrypt (hashcat mode: 3200)")
        if h.startswith("$6$"):
            identifications.append("SHA-512 crypt (hashcat mode: 1800)")
        if h.startswith("$5$"):
            identifications.append("SHA-256 crypt (hashcat mode: 7400)")
        if h.startswith("$1$"):
            identifications.append("MD5 crypt (hashcat mode: 500)")
        if length == 32 and hex_upper:
            identifications.append("NTLM (hashcat mode: 1000)")

        if identifications:
            return "Possible hash types:\n" + "\n".join(f"  - {i}" for i in identifications)
        return f"Unknown hash format (length: {length})"
