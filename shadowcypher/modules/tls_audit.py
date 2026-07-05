"""
TLS/SSL Configuration Auditor — Enterprise Defensive Build.
Wraps testssl.sh to check certificate validity, protocol/cipher strength,
and known TLS vulnerabilities (Heartbleed, POODLE, BEAST, etc.) on your own
externally-facing services — the same audit a pentester runs before you do.
"""

import shutil
from typing import Callable, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.mitre import mitre


class TlsAudit(BaseModule):
    """The 'Cipher Watch' engine — TLS/SSL hardening audit via testssl.sh."""

    def __init__(self):
        super().__init__(module_name="tls_audit")

    def full_audit(self, target: str, port: int = 443,
                    on_output: Callable = None) -> Optional[str]:
        """Run a full testssl.sh audit: protocol support, cipher strength,
        certificate chain/expiry, and known CVE checks (Heartbleed, POODLE,
        ROBOT, etc.) against a single host."""
        if not validate_target(target):
            if on_output:
                on_output(f"[TLS_AUDIT] Invalid target: {target}\n")
            return None
        testssl = self.get_tool_path("testssl")
        if not shutil.which(testssl):
            if on_output:
                on_output(
                    "[TLS_AUDIT] testssl.sh not found — install: "
                    "git clone https://github.com/drwetter/testssl.sh (or your distro's package)\n"
                )
            return None
        self.log(f"TLS_AUDIT: {target}:{port}")
        if on_output:
            on_output(f"[TLS_AUDIT] ATT&CK: {mitre.format_tags(mitre.tag('nmap_service'))}\n")
        args = [testssl, "--quiet", "--color", "0", f"{target}:{port}"]
        return self.execute(f"TESTSSL_{target}", args, callback=on_output)

    def quick_cert_check(self, target: str, port: int = 443,
                          on_output: Callable = None) -> Optional[str]:
        """Fast certificate-only check (expiry, chain, hostname match) —
        skips the full protocol/cipher sweep for a quick sanity check."""
        if not validate_target(target):
            return None
        testssl = self.get_tool_path("testssl")
        if not shutil.which(testssl):
            if on_output:
                on_output("[TLS_AUDIT] testssl.sh not found.\n")
            return None
        self.log(f"TLS_CERT_CHECK: {target}:{port}")
        args = [testssl, "--quiet", "--color", "0", "-S", "-P", f"{target}:{port}"]
        return self.execute(f"TESTSSL_CERT_{target}", args, callback=on_output)

    def vuln_check(self, target: str, port: int = 443,
                    on_output: Callable = None) -> Optional[str]:
        """Check only for known TLS vulnerabilities (Heartbleed, POODLE,
        BEAST, ROBOT, CRIME, FREAK, LOGJAM, DROWN) — the fastest path to a
        yes/no on whether a service needs urgent patching."""
        if not validate_target(target):
            return None
        testssl = self.get_tool_path("testssl")
        if not shutil.which(testssl):
            if on_output:
                on_output("[TLS_AUDIT] testssl.sh not found.\n")
            return None
        self.log(f"TLS_VULN_CHECK: {target}:{port}")
        args = [testssl, "--quiet", "--color", "0", "-U", f"{target}:{port}"]
        return self.execute(f"TESTSSL_VULN_{target}", args, callback=on_output)


tls_audit = TlsAudit()
