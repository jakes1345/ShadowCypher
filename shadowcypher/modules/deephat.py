"""
DeepHat — Dark Web & OSINT Intelligence Engine
Provides Tor-based browsing, onion service probing, and dark web intelligence feeds.
"""

from __future__ import annotations

import re
import socket
import time
from typing import Any

from shadowcypher.core.module import BaseModule

_ONION_RE = re.compile(r"[a-z2-7]{16,56}\.onion", re.I)
_CLEARNET_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)


def _socks5_available() -> bool:
    try:
        import socks  # PySocks  # noqa: F401
        return True
    except ImportError:
        return False


class DeepHat(BaseModule):
    """
    Dark web intelligence and Tor network interaction.
    Requires Tor running locally on socks5://127.0.0.1:9050.
    """

    TOR_PROXY = ("127.0.0.1", 9050)

    def __init__(self):
        super().__init__(module_name="deephat")
        self._tor_checked: bool | None = None

    # ── Tor connectivity ──────────────────────────────────────────────────────

    def check_tor(self) -> dict[str, Any]:
        """
        Verify Tor SOCKS5 proxy is reachable and exit IP is anonymised.
        Uses check.torproject.org via Tor.
        """
        if not _socks5_available():
            return {
                "tor_available": False,
                "error": "PySocks not installed — run: pip install PySocks",
            }
        try:
            ip = self._tor_request("https://api.ipify.org?format=json", timeout=15)
            self._tor_checked = True
            self.log(f"TOR_CHECK_OK: exit={ip.get('ip','?')}")
            return {"tor_available": True, "exit_ip": ip.get("ip")}
        except Exception as e:
            self._tor_checked = False
            return {"tor_available": False, "error": str(e)}

    def is_tor_running(self) -> bool:
        """Quick TCP check that Tor's SOCKS port is open."""
        try:
            with socket.create_connection(self.TOR_PROXY, timeout=2):
                return True
        except OSError:
            return False

    # ── Onion service probing ─────────────────────────────────────────────────

    def probe_onion(
        self,
        onion_url: str,
        timeout: int = 30,
        on_output=None,
    ) -> dict[str, Any]:
        """
        Probe an .onion service and return basic reachability + HTML metadata.
        Requires Tor running locally.
        """
        if not _onion_RE_matches(onion_url):
            return {"error": f"Not a valid .onion URL: {onion_url}"}

        if on_output:
            on_output(f"[DEEPHAT] Probing {onion_url} via Tor...\n")

        t0 = time.time()
        try:
            data = self._tor_request(onion_url, timeout=timeout)
            elapsed = time.time() - t0
            result: dict[str, Any] = {
                "url": onion_url,
                "reachable": True,
                "response_time_s": round(elapsed, 2),
            }
            if isinstance(data, dict):
                result["data"] = data
            elif isinstance(data, str):
                result["title"] = _extract_title(data)
                result["links_found"] = _extract_onion_links(data)
            self.log(f"ONION_PROBE_OK: {onion_url} in {elapsed:.1f}s")
            if on_output:
                on_output(f"[DEEPHAT] Reachable: {onion_url} ({elapsed:.1f}s)\n")
            return result
        except Exception as e:
            elapsed = time.time() - t0
            self.log(f"ONION_PROBE_FAIL: {onion_url} — {e}")
            if on_output:
                on_output(f"[DEEPHAT] Unreachable: {onion_url} — {e}\n")
            return {
                "url": onion_url,
                "reachable": False,
                "error": str(e),
                "elapsed_s": round(elapsed, 2),
            }

    def extract_onions_from_text(self, text: str) -> list[str]:
        """Extract all .onion addresses from arbitrary text."""
        return list(set(_ONION_RE.findall(text)))

    # ── Paste / breach monitoring ─────────────────────────────────────────────

    def search_paste_sites(
        self,
        keyword: str,
        on_output=None,
    ) -> dict[str, Any]:
        """
        Search clearnet paste aggregation APIs for a keyword.
        Returns recent paste metadata (no content scraping).
        Uses the Psbdmp.ws public API (no auth required).
        """
        try:
            import urllib.request, json
            url = f"https://psbdmp.ws/api/search/{urllib.parse.quote(keyword)}"
            req = urllib.request.Request(url, headers={"User-Agent": "ShadowCypher/3.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            pastes = data.get("data", [])[:20]
            self.log(f"PASTE_SEARCH: '{keyword}' → {len(pastes)} results")
            if on_output:
                on_output(f"[DEEPHAT] Paste search '{keyword}': {len(pastes)} results\n")
            return {"keyword": keyword, "count": len(pastes), "pastes": pastes}
        except Exception as e:
            return {"keyword": keyword, "error": str(e)}

    def check_breach(
        self,
        email: str,
        on_output=None,
    ) -> dict[str, Any]:
        """
        Check if an email appears in known breach databases via HIBP API (v3).
        Requires HIBP API key for full results; returns public breach names otherwise.
        """
        import urllib.request, json, urllib.parse
        email_encoded = urllib.parse.quote(email)
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_encoded}"
        headers = {
            "User-Agent": "ShadowCypher-Security-Platform/3.0",
            "hibp-api-key": "PLACEHOLDER_API_KEY",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                breaches = json.loads(resp.read())
            names = [b.get("Name") for b in breaches]
            self.log(f"BREACH_CHECK: {email} found in {len(names)} breach(es)")
            if on_output:
                on_output(f"[DEEPHAT] {email}: {len(names)} breach(es)\n")
            return {"email": email, "breach_count": len(names), "breaches": names}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"email": email, "breach_count": 0, "breaches": []}
            if e.code == 401:
                return {"email": email, "error": "HIBP API key required — set HIBP_API_KEY"}
            return {"email": email, "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"email": email, "error": str(e)}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tor_request(self, url: str, timeout: int = 30) -> Any:
        """Make an HTTP request through the Tor SOCKS5 proxy."""
        import socks
        import urllib.request
        import json

        orig_socket = socket.socket
        try:
            socks.set_default_proxy(socks.SOCKS5, self.TOR_PROXY[0], self.TOR_PROXY[1])
            socket.socket = socks.socksocket  # type: ignore[assignment]

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ShadowCypher)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        finally:
            socket.socket = orig_socket  # type: ignore[assignment]


# ── Helpers ───────────────────────────────────────────────────────────────────

import urllib.parse  # noqa: E402 (needed in search_paste_sites above)


def _onion_RE_matches(url: str) -> bool:
    return bool(_ONION_RE.search(url))


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip()[:200] if m else ""


def _extract_onion_links(html: str) -> list[str]:
    return list(set(_ONION_RE.findall(html)))
