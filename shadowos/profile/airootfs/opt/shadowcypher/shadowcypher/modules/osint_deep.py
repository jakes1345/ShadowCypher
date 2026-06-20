"""
ShadowCypher Deep OSINT & Identity Correlation Engine.
Integrates Sherlock, Holehe, theHarvester, and custom scrapers.
"""

import os
import re
import shutil
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.stealth import require_stealth

try:
    from ai_engine.autoagent.registry import register_tool
except ImportError:
    def register_tool(*a, **kw):
        return a[0] if len(a) == 1 and callable(a[0]) else (lambda fn: fn)


class DeepOSINT:
    """The 'Omniscience' engine. Cross-correlates digital shadows."""

    @staticmethod
    def _resolve_python():
        from shadowcypher.core.config import config
        root = str(config.project_root)
        for p in [
            os.path.join(root, "ai_engine", "meta-venv", "bin", "python3"),
            os.path.join(root, "venv", "bin", "python3"),
            "python3",
        ]:
            if p == "python3" or os.path.exists(p):
                return p
        return "python3"

    # ── Username / Social Footprint ──

    @staticmethod
    @register_tool("osint_social_footprint")
    def social_footprint(username: str, on_output=None):
        """
        Search for social media accounts across 300+ platforms using the Sherlock engine.
        Args:
            username: The target username to investigate.
        """
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        sherlock_root = os.path.join(str(config.project_root), "tools", "sherlock")
        if not os.path.exists(sherlock_root):
            if on_output:
                on_output("[OSINT] SHERLOCK_NOT_STAGED. Run tools/install_osint.sh\n")
            return None
        python_bin = DeepOSINT._resolve_python()
        args = [python_bin, "-m", "sherlock_project", username, "--timeout", "10", "--no-color"]
        return runner.execute_task(f"SHERLOCK_{username}", args, callback=on_output)

    # ── Email Intelligence ──

    @staticmethod
    @register_tool("osint_email_audit")
    def email_audit(email: str, on_output=None):
        """
        Check if an email address is registered on 100+ websites using the Holehe engine.
        Args:
            email: The target email address to audit.
        """
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        holehe_path = os.path.join(str(config.project_root), "tools", "holehe")
        if not os.path.exists(holehe_path):
            if on_output:
                on_output("[OSINT] HOLEHE_NOT_STAGED. Run tools/install_osint.sh\n")
            return None
        python_bin = DeepOSINT._resolve_python()
        args = [python_bin, os.path.join(holehe_path, "holehe", "core.py"), email]
        return runner.execute_task(f"HOLEHE_{email}", args, callback=on_output)

    @staticmethod
    @register_tool("osint_leak_check")
    def leak_check(query: str, on_output=None):
        """
        Check if an email/username appears in known public data breaches via HaveIBeenPwned API.
        Args:
            query: The email address to search for in public breach databases.
        """
        require_stealth(on_output=on_output)
        import hashlib
        import urllib.request
        if on_output:
            on_output(f"[OSINT] BREACH_CHECK: {query}\n")

        # Use k-Anonymity model: only send first 5 chars of SHA-1 hash
        sha1 = hashlib.sha1(query.encode()).hexdigest().upper()  # nosec B324
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            req = urllib.request.Request(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "ShadowCypher-OSINT/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                body = resp.read().decode()
            found = next((ln for ln in body.splitlines() if ln.split(":")[0] == suffix), None)
            if found:
                count = found.split(":")[1]
                msg = f"[BREACH] FOUND: {query} appears in {count} known breach(es).\n"
            else:
                msg = f"[BREACH] CLEAN: {query} not found in known breach databases.\n"
            if on_output:
                on_output(msg)
            return msg
        except Exception as e:
            msg = f"[BREACH] API_ERROR: {e}\n"
            if on_output:
                on_output(msg)
            return msg

    # ── Domain / Email Harvesting ──

    @staticmethod
    @register_tool("osint_harvest_domain")
    def harvest_domain(domain: str, sources: str = "all", on_output=None):
        """
        Harvest emails, names, hosts, and URLs associated with a domain using theHarvester.
        Args:
            domain: Target domain to investigate.
            sources: Comma-separated source list (all, google, bing, linkedin, etc.)
        """
        require_stealth(on_output=on_output)
        harvester = shutil.which("theHarvester")
        if not harvester:
            if on_output:
                on_output("[OSINT] theHarvester not found — install: pip install theHarvester\n")
            return None
        logger.info("osint", f"theHarvester: {domain} (sources={sources})")
        args = [harvester, "-d", domain, "-b", sources, "-l", "200"]
        return runner.execute_task(f"HARVEST_{domain}", args, callback=on_output)

    # ── Google Ecosystem ──

    @staticmethod
    def ghunt_pivot(email, on_output=None):
        """Perform Google ecosystem OSINT using GHunt."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        path = os.path.join(str(config.project_root), "tools", "elite", "GHunt", "main.py")
        if not os.path.exists(path):
            if on_output:
                on_output("[OSINT] GHUNT_NOT_STAGED. Clone: tools/elite/GHunt\n")
            return None
        args = ["python3", path, "email", email]
        logger.info("osint", f"GHunt Pivot: {email}")
        return runner.execute_task(f"GHUNT_{email}", args, callback=on_output)

    # ── Passive DNS / Wayback ──

    @staticmethod
    def wayback_recon(domain, on_output=None):
        """Passive recon using Wayback Machine CDX API — surfaces subdomains and endpoints."""
        require_stealth(on_output=on_output)
        import urllib.request
        import json
        if on_output:
            on_output(f"[OSINT] WAYBACK_RECON: {domain}\n")
        url = (
            f"http://web.archive.org/cdx/search/cdx"
            f"?url=*.{domain}/*&output=json&collapse=urlkey&limit=2000&fl=original"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ShadowCypher-OSINT/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
                data = json.loads(resp.read())
            if len(data) <= 1:
                if on_output:
                    on_output("[OSINT] No Wayback data found.\n")
                return
            subdomains = set()
            endpoints = set()
            for row in data[1:]:
                original = row[0]
                m = re.search(r"https?://([^/]+)((/[^?#]*)?)", original)
                if m:
                    subdomains.add(m.group(1))
                    if m.group(2) and m.group(2) != "/":
                        endpoints.add(m.group(2).split("?")[0])
            if on_output:
                on_output(f"[OSINT] Subdomains ({len(subdomains)}):\n")
                for s in sorted(subdomains)[:25]:
                    on_output(f"  [+] {s}\n")
                on_output(f"\n[OSINT] Unique Endpoints ({len(endpoints)}):\n")
                for e in sorted(endpoints)[:25]:
                    on_output(f"  [>] {e}\n")
        except Exception as exc:
            if on_output:
                on_output(f"[OSINT] Wayback API error: {exc}\n")

    # ── Alias ──

    @staticmethod
    def steam_correlate(steam_id, on_output=None):
        return DeepOSINT.social_footprint(steam_id, on_output=on_output)
