"""
ShadowCypher Stealth Web Engine — Multi-layered anti-detection fetching.

Levels of stealth (auto-escalates on failure):
  L0: Standard requests with rotated headers
  L1: curl_cffi with TLS fingerprint impersonation (Chrome/Firefox JA3)
  L2: Tor circuit routing via SOCKS5
  L3: Free rotating proxy pool (scraped + validated)
  L4: Headless browser (playwright-stealth or Camoufox)

Each level addresses a specific detection vector:
  L0 → Basic header checks (User-Agent, Accept, etc.)
  L1 → TLS/JA3/JA4 fingerprint analysis (Cloudflare, Akamai)
  L2 → IP reputation + geo-blocking (adds Tor anonymity)
  L3 → IP rotation for rate-limited targets (Instagram, LinkedIn)
  L4 → Full JS rendering + behavioral analysis (Turnstile, reCAPTCHA)
"""

import os
import re
import json
import time
import random
import socket
import threading
import subprocess
from typing import Optional, Callable
from urllib.parse import urlparse

from shadowcypher.core.undercover import Undercover
from shadowcypher.core.logger import logger

# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

TOR_SOCKS = "socks5h://127.0.0.1:9050"
TOR_CONTROL_PORT = 9051

# Free public proxy sources (rotate through these to build pool)
_PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

# TLS impersonation targets (browser fingerprints to mimic)
_TLS_BROWSERS = [
    "chrome120", "chrome119", "chrome124",
    "firefox120", "firefox121",
    "safari17_0", "safari17_2_1",
    "edge101",
]


class StealthFetcher:
    """Multi-layered stealth HTTP client with automatic escalation."""

    def __init__(self):
        self._proxy_pool: list[str] = []
        self._proxy_lock = threading.Lock()
        self._proxy_index = 0
        self._last_proxy_refresh = 0
        self._session = None  # Lazy init

    # ──────────────────────────────────────────────
    # L0: Standard Requests
    # ──────────────────────────────────────────────

    def _get_session(self):
        """Get requests.Session with stealth headers."""
        import requests
        if not self._session:
            self._session = requests.Session()
        self._session.headers.update(Undercover.get_stealth_headers())
        return self._session

    def fetch_l0(self, url: str, timeout: int = 15, **kwargs) -> Optional[str]:
        """L0: Standard requests with rotated headers."""
        import requests
        session = self._get_session()
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True, **kwargs)
            if resp.status_code == 200:
                return resp.text
            logger.info("web", f"L0 HTTP {resp.status_code} for {url}")
            return None
        except Exception as e:
            logger.info("web", f"L0 failed: {e}")
            return None

    # ──────────────────────────────────────────────
    # L1: TLS Fingerprint Impersonation (curl_cffi)
    # ──────────────────────────────────────────────

    @staticmethod
    def _has_curl_cffi() -> bool:
        try:
            import curl_cffi
            return True
        except ImportError:
            return False

    def fetch_l1(self, url: str, timeout: int = 20,
                 impersonate: str = None, **kwargs) -> Optional[str]:
        """L1: curl_cffi with browser TLS fingerprint impersonation.
        This mimics the exact TLS handshake (JA3/JA4) of a real browser,
        which bypasses Cloudflare's TLS fingerprint detection."""
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            logger.info("web", "curl_cffi not installed. Run: pip install curl_cffi")
            return None

        browser = impersonate or random.choice(_TLS_BROWSERS)
        headers = Undercover.get_stealth_headers()

        try:
            resp = cffi_requests.get(
                url,
                headers=headers,
                impersonate=browser,
                timeout=timeout,
                allow_redirects=True,
                **kwargs,
            )
            if resp.status_code == 200:
                logger.info("web", f"L1 OK (impersonate={browser}): {url}")
                return resp.text
            logger.info("web", f"L1 HTTP {resp.status_code} for {url}")
            return None
        except Exception as e:
            logger.info("web", f"L1 failed ({browser}): {e}")
            return None

    # ──────────────────────────────────────────────
    # L2: Tor Routing
    # ──────────────────────────────────────────────

    @staticmethod
    def tor_available() -> bool:
        """Check if Tor SOCKS proxy is running."""
        try:
            s = socket.create_connection(("127.0.0.1", 9050), timeout=2)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def tor_new_circuit():
        """Request a new Tor circuit (new exit node / IP)."""
        try:
            import stem.control
            with stem.control.Controller.from_port(port=TOR_CONTROL_PORT) as ctrl:
                ctrl.authenticate()
                ctrl.signal(stem.Signal.NEWNYM)
                logger.info("web", "Tor circuit rotated")
                time.sleep(3)  # Wait for new circuit
        except ImportError:
            # Fallback: use socat/nc to send NEWNYM signal
            try:
                subprocess.run(
                    ["bash", "-c",
                     f'echo -e "AUTHENTICATE \"\"\r\nSIGNAL NEWNYM\r\n" | nc 127.0.0.1 {TOR_CONTROL_PORT}'],
                    timeout=5, capture_output=True,
                )
                time.sleep(3)
            except Exception:
                pass
        except Exception as e:
            logger.info("web", f"Circuit rotation failed: {e}")

    def fetch_l2(self, url: str, timeout: int = 30, **kwargs) -> Optional[str]:
        """L2: Route through Tor SOCKS5 proxy."""
        import requests
        if not self.tor_available():
            logger.info("web", "Tor not running. Install: sudo apt install tor && sudo systemctl start tor")
            return None

        session = requests.Session()
        session.proxies = {"http": TOR_SOCKS, "https": TOR_SOCKS}
        session.headers.update(Undercover.get_stealth_headers())

        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True, **kwargs)
            if resp.status_code == 200:
                logger.info("web", f"L2 OK (Tor): {url}")
                return resp.text
            return None
        except Exception as e:
            logger.info("web", f"L2 Tor failed: {e}")
            return None

    # ──────────────────────────────────────────────
    # L3: Free Rotating Proxy Pool
    # ──────────────────────────────────────────────

    def refresh_proxy_pool(self, on_status: Callable[[str], None] = None):
        """Scrape free proxy lists and validate them."""
        import requests
        raw_proxies = set()

        for src in _PROXY_SOURCES:
            try:
                resp = requests.get(src, timeout=10)
                if resp.status_code == 200:
                    for line in resp.text.strip().split("\n"):
                        line = line.strip()
                        if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                            raw_proxies.add(line)
            except Exception:
                continue

        if on_status:
            on_status(f"Scraped {len(raw_proxies)} raw proxies. Validating...")

        # Quick validate (test connectivity with 3s timeout)
        valid = []

        def _test(proxy):
            try:
                r = requests.get(
                    "http://httpbin.org/ip",
                    proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
                    timeout=4,
                )
                if r.status_code == 200:
                    valid.append(proxy)
            except Exception:
                pass

        # Test in parallel (20 threads, fast validation)
        threads = []
        for proxy in list(raw_proxies)[:200]:  # Test top 200
            t = threading.Thread(target=_test, args=(proxy,))
            t.start()
            threads.append(t)
            if len(threads) >= 20:
                for t in threads:
                    t.join(timeout=5)
                threads = []

        for t in threads:
            t.join(timeout=5)

        with self._proxy_lock:
            self._proxy_pool = valid
            self._proxy_index = 0
            self._last_proxy_refresh = time.time()

        msg = f"Proxy pool: {len(valid)}/{len(raw_proxies)} valid"
        logger.info("web", msg)
        if on_status:
            on_status(msg)

    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from the rotating pool."""
        with self._proxy_lock:
            if not self._proxy_pool:
                return None
            proxy = self._proxy_pool[self._proxy_index % len(self._proxy_pool)]
            self._proxy_index += 1
            return proxy

    def fetch_l3(self, url: str, timeout: int = 15, **kwargs) -> Optional[str]:
        """L3: Fetch through rotating proxy pool."""
        import requests

        # Auto-refresh if pool is empty or stale (>30 min)
        if not self._proxy_pool or (time.time() - self._last_proxy_refresh) > 1800:
            self.refresh_proxy_pool()

        proxy = self._get_next_proxy()
        if not proxy:
            logger.info("web", "No valid proxies available")
            return None

        session = requests.Session()
        session.proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }
        session.headers.update(Undercover.get_stealth_headers())

        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True, **kwargs)
            if resp.status_code == 200:
                logger.info("web", f"L3 OK (proxy={proxy}): {url}")
                return resp.text
            return None
        except Exception as e:
            logger.info("web", f"L3 proxy {proxy} failed: {e}")
            # Try next proxy
            return self.fetch_l3(url, timeout=timeout, **kwargs) if self._proxy_pool else None

    # ──────────────────────────────────────────────
    # L4: Headless Browser (Playwright Stealth)
    # ──────────────────────────────────────────────

    def fetch_l4(self, url: str, timeout: int = 30,
                 wait_selector: str = None,
                 screenshot: str = None,
                 proxy: str = None) -> Optional[str]:
        """L4: Full headless browser with stealth patches.
        Handles Cloudflare Turnstile, JS challenges, and behavioral analysis.
        Requires: pip install playwright && playwright install chromium"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.info("web", "playwright not installed. Run: pip install playwright && playwright install chromium")
            return None

        try:
            from playwright_stealth import stealth_sync
            has_stealth = True
        except ImportError:
            has_stealth = False

        ua = Undercover.get_stealth_user_agent()

        with sync_playwright() as p:
            launch_opts = {
                "headless": True,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--disable-extensions",
                ],
            }
            if proxy:
                launch_opts["proxy"] = {"server": proxy}

            browser = p.chromium.launch(**launch_opts)
            ctx = browser.new_context(
                user_agent=ua,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme="dark",
                java_script_enabled=True,
            )

            page = ctx.new_page()

            # Apply stealth patches if available
            if has_stealth:
                stealth_sync(page)

            # Manual stealth patches (works without playwright_stealth)
            page.add_init_script("""
                // Override webdriver flag
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Chrome runtime
                window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
                
                // Plugins array
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Permission query
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            try:
                page.goto(url, timeout=timeout * 1000, wait_until="networkidle")

                # Wait for CF challenge to resolve (if present)
                for _ in range(10):
                    title = page.title().lower()
                    if "just a moment" in title or "checking" in title:
                        time.sleep(2)
                    else:
                        break

                if wait_selector:
                    page.wait_for_selector(wait_selector, timeout=10000)

                if screenshot:
                    page.screenshot(path=screenshot, full_page=True)

                content = page.content()
                browser.close()
                logger.info("web", f"L4 OK (headless): {url}")
                return content

            except Exception as e:
                browser.close()
                logger.info("web", f"L4 failed: {e}")
                return None

    # ──────────────────────────────────────────────
    # Master Fetch — tries each level, auto-escalates
    # ──────────────────────────────────────────────

    def fetch(self, url: str, stealth_level: int = None,
              timeout: int = 20, on_status: Callable[[str], None] = None,
              **kwargs) -> Optional[str]:
        """Smart fetch with automatic escalation through stealth levels.

        Args:
            url: Target URL
            stealth_level: Force a specific level (0-4), or None for auto-escalate
            timeout: Request timeout in seconds
            on_status: Callback for status messages
        """
        if stealth_level is not None:
            return self._fetch_level(stealth_level, url, timeout, **kwargs)

        # Auto-escalate: try L0 → L1 → L2/L3 → L4
        for level in [0, 1, 2, 3, 4]:
            if on_status:
                on_status(f"[L{level}] Attempting {url}...")
            result = self._fetch_level(level, url, timeout, **kwargs)
            if result:
                # Quick check: did we get a CF challenge page?
                if self._is_blocked(result):
                    if on_status:
                        on_status(f"[L{level}] Got blocked/challenge page, escalating...")
                    continue
                return result
            if on_status:
                on_status(f"[L{level}] Failed, escalating...")

        if on_status:
            on_status("[FAIL] All stealth levels exhausted.")
        return None

    def _fetch_level(self, level: int, url: str, timeout: int, **kwargs) -> Optional[str]:
        if level == 0:
            return self.fetch_l0(url, timeout, **kwargs)
        elif level == 1:
            return self.fetch_l1(url, timeout, **kwargs)
        elif level == 2:
            return self.fetch_l2(url, timeout, **kwargs)
        elif level == 3:
            return self.fetch_l3(url, timeout, **kwargs)
        elif level == 4:
            return self.fetch_l4(url, timeout, **kwargs)
        return None

    @staticmethod
    def _is_blocked(html: str) -> bool:
        """Detect if we got a Cloudflare/bot challenge instead of real content."""
        lower = html[:3000].lower()
        blocked_sigs = [
            "just a moment",                      # CF challenge page
            "checking your browser",              # CF interstitial
            "enable javascript and cookies",      # CF JS challenge
            "cf-browser-verification",            # CF div id
            "ray id:",                            # CF Ray ID
            "attention required! | cloudflare",   # CF block page
            "access denied | used cloudflare",    # Blocked
            "please complete the security check",  # Generic CAPTCHA
            '<div id="challenge-',                # CF Turnstile
            "are you a robot",                    # Generic bot check
        ]
        return any(sig in lower for sig in blocked_sigs)

    def extract_text(self, html: str) -> str:
        """Extract human-readable text from HTML."""
        text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def get_capabilities(self) -> dict:
        """Report what stealth capabilities are available."""
        caps = {
            "L0_requests": True,
            "L1_curl_cffi": self._has_curl_cffi(),
            "L2_tor": self.tor_available(),
            "L3_proxy_pool": len(self._proxy_pool),
            "L4_playwright": False,
        }
        try:
            import playwright
            caps["L4_playwright"] = True
        except ImportError:
            pass
        return caps


# Global singleton
stealth_web = StealthFetcher()
