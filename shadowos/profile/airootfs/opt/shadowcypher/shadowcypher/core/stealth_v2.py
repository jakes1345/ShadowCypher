"""
Stealth Engine v2 Upgrades (T3-2, T3-3, T3-5):
- Domain fronting support
- JA3 TLS fingerprint spoofing via curl-impersonate
- Traffic timing jitter via tc netem

Appended to stealth.py as new methods on StealthEngine.
Import and use:
    from shadowcypher.core.stealth import stealth
    stealth.enable_domain_fronting("cdn.cloudflare.com", "my-c2.example.com")
    stealth.add_timing_jitter(min_ms=500, max_ms=5000)
    stealth.curl_impersonate("https://target.com", browser="chrome120")
"""
import os
import random
import re
import shutil
import socket
import subprocess
import time
from typing import Optional

from shadowcypher.core.logger import logger
from shadowcypher.core.stealth import StealthEngine


def _geofence_check(ip: str, allowed_countries: list) -> bool:
    """Check if an IP is in an allowed country using ip-api.com (no key needed)."""
    import json
    import urllib.request
    try:
        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        with urllib.request.urlopen(url, timeout=5) as r:  # nosec B310
            data = json.loads(r.read())
        cc = data.get("countryCode", "")
        return cc in allowed_countries
    except Exception:
        return True  # fail open if lookup fails


def enable_domain_fronting(self, cdn_host: str, real_host: str):
    """
    Configure domain fronting.
    SNI (TLS ClientHello) = cdn_host  → CDN sees legit traffic
    HTTP Host header     = real_host  → CDN forwards to your server

    Your traffic looks like it's going to a major CDN.
    Use with: stealth.requests_session_fronted(url)
    """
    self._fronting_cdn = cdn_host
    self._fronting_real = real_host
    logger.info("stealth", f"Domain fronting: SNI={cdn_host} → Host={real_host}")


def requests_session_fronted(self, url: Optional[str] = None):
    """
    Return a requests.Session using domain fronting.
    Connects to CDN's IP but sends Host: real_host in the HTTP header.
    """

    import requests
    cdn = getattr(self, "_fronting_cdn", None)
    real = getattr(self, "_fronting_real", None)
    if not cdn or not real:
        logger.warning("stealth", "Domain fronting not configured — call enable_domain_fronting() first")
        return None
    session = requests.Session()
    # Resolve CDN IP and spoof Host header
    try:
        cdn_ip = socket.gethostbyname(cdn)
    except Exception:
        cdn_ip = cdn
    session.headers.update({"Host": real})
    # Route through Tor if active
    if self._check_tor():
        session.proxies = {"http": "socks5h://127.0.0.1:9050",
                           "https": "socks5h://127.0.0.1:9050"}
    session.verify = False  # required for SNI mismatch
    logger.info("stealth", f"Fronted session ready: CDN={cdn_ip} Host={real}")
    return session


def curl_impersonate(self, url: str, browser: str = "chrome120",
                     extra_args: Optional[list] = None, on_output=None) -> str:
    """
    Make a request using curl-impersonate to spoof TLS/JA3 fingerprint.
    Looks exactly like a real browser at the TLS handshake level.

    Browsers: chrome120, chrome116, firefox117, safari17, edge120
    Install: https://github.com/lwthiker/curl-impersonate
    """
    # Look for curl-impersonate variants
    bin_name = f"curl-impersonate-{browser}" if "-" not in browser else browser
    curl_bin = shutil.which(bin_name) or shutil.which("curl-impersonate")

    if not curl_bin:
        # Fall back to regular curl with custom headers to partially mimic browser
        logger.warning("stealth", "curl-impersonate not found — using curl with browser headers")
        curl_bin = "curl"
        browser_headers = [
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.5",
            "-H", "Accept-Encoding: gzip, deflate, br",
            "-H", "Connection: keep-alive",
            "--tlsv1.3",
        ]
        args = ["curl", "-s", "-L"] + browser_headers + (extra_args or []) + [url]
    else:
        args = [curl_bin, "-s", "-L"] + (extra_args or []) + [url]

    # Route through Tor if active
    if self._check_tor():
        args = ["torsocks"] + args if shutil.which("torsocks") else args

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if on_output:
            on_output(f"[STEALTH] curl-impersonate {browser} → {url} ({result.returncode})\n")
        return result.stdout
    except Exception as e:
        if on_output:
            on_output(f"[STEALTH] curl-impersonate error: {e}\n")
        return ""


def add_timing_jitter(self, min_ms: int = 500, max_ms: int = 5000):
    """
    Add random timing jitter to defeat traffic correlation attacks.
    Applies tc netem if available (Linux), otherwise uses sleep.
    Call before outbound operations.
    """
    delay_ms = random.randint(min_ms, max_ms)

    # Try tc netem for kernel-level jitter (Linux only)
    tc = shutil.which("tc")
    if tc and os.name == "posix":
        iface = self._default_interface()
        if iface:
            try:
                # Add jitter to outbound packets on the default interface
                subprocess.run(
                    [tc, "qdisc", "replace", "dev", iface, "root",
                     "netem", "delay", f"{delay_ms}ms", "50ms", "distribution", "normal"],
                    capture_output=True, timeout=5
                )
                logger.info("stealth", f"tc netem jitter: {delay_ms}ms ±50ms on {iface}")
                return
            except Exception:
                pass

    # Fallback: simple sleep-based jitter
    logger.info("stealth", f"Timing jitter: sleeping {delay_ms}ms")
    time.sleep(delay_ms / 1000)


def remove_timing_jitter(self):
    """Remove tc netem jitter rules."""
    tc = shutil.which("tc")
    if tc:
        iface = self._default_interface()
        if iface:
            try:
                subprocess.run([tc, "qdisc", "del", "dev", iface, "root"],
                               capture_output=True, timeout=5)
                logger.info("stealth", f"tc netem jitter removed from {iface}")
            except Exception:
                pass


def _default_interface(self) -> str:
    """Get the default outbound network interface."""
    try:
        result = subprocess.run(["ip", "route", "show", "default"],
                                capture_output=True, text=True, timeout=3)
        for token in result.stdout.split():
            if token not in ("default", "via", "dev", "proto", "metric",
                             "src", "onlink", "linkdown"):
                if re.match(r"^[a-zA-Z]", token):
                    return token
    except Exception:
        pass
    return ""


def geofence_connection(self, peer_ip: str,
                        allowed_countries: Optional[list] = None) -> bool:
    """
    Refuse connections from outside allowed countries.
    Returns True if connection should be ALLOWED.
    Default allowed: US only (change as needed).
    """
    if not allowed_countries:
        allowed_countries = ["US"]
    allowed = _geofence_check(peer_ip, allowed_countries)
    if not allowed:
        logger.warning("stealth",
                       f"GEOFENCE_BLOCK: {peer_ip} not in allowed countries {allowed_countries}")
    return allowed


# Monkey-patch new methods onto StealthEngine
StealthEngine.enable_domain_fronting = enable_domain_fronting  # type: ignore[attr-defined]
StealthEngine.requests_session_fronted = requests_session_fronted  # type: ignore[attr-defined]
StealthEngine.curl_impersonate = curl_impersonate  # type: ignore[attr-defined]
StealthEngine.add_timing_jitter = add_timing_jitter  # type: ignore[attr-defined]
StealthEngine.remove_timing_jitter = remove_timing_jitter  # type: ignore[attr-defined]
StealthEngine._default_interface = _default_interface  # type: ignore[attr-defined]
StealthEngine.geofence_connection = geofence_connection  # type: ignore[attr-defined]
StealthEngine._fronting_cdn = None  # type: ignore[attr-defined]
StealthEngine._fronting_real = None  # type: ignore[attr-defined]

logger.info("stealth", "StealthEngine v2 loaded: domain fronting + JA3 spoofing + traffic jitter")
