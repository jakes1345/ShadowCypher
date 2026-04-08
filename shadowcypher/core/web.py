"""Stealth Research Engine — Anti-fingerprint web fetching and search."""

import random
import time
import re
import requests
from typing import Optional
from shadowcypher.core.undercover import Undercover
from shadowcypher.core.logger import logger


_MAX_RETRIES = 3


class StealthDrifter:
    """Web research engine with rotating browser profiles to avoid bot detection."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(Undercover.get_stealth_headers())

    def fetch(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch a URL with stealth headers. Returns cleaned text content."""
        logger.info("web", f"Fetching: {url}")
        for attempt in range(_MAX_RETRIES):
            try:
                # Human-like jitter between retries
                if attempt > 0:
                    time.sleep(random.uniform(1.0, 3.0))
                    self._rotate()

                resp = self.session.get(url, timeout=timeout, allow_redirects=True)

                if resp.status_code == 403 or "cf-browser-verification" in resp.text.lower():
                    logger.info("web", f"Blocked (attempt {attempt + 1}/{_MAX_RETRIES}), rotating...")
                    continue

                if resp.status_code == 429:
                    logger.info("web", f"Rate limited, backing off...")
                    time.sleep(random.uniform(3.0, 8.0))
                    continue

                if resp.status_code >= 400:
                    logger.info("web", f"HTTP {resp.status_code} for {url}")
                    return None

                return self._extract_text(resp.text)

            except requests.Timeout:
                logger.info("web", f"Timeout on attempt {attempt + 1}")
            except requests.ConnectionError as e:
                logger.info("web", f"Connection error: {e}")
                return None
            except Exception as e:
                logger.info("web", f"Fetch error: {e}")
                return None

        logger.info("web", f"All {_MAX_RETRIES} attempts failed for {url}")
        return None

    def search(self, query: str) -> Optional[str]:
        """Search via DuckDuckGo HTML endpoint with stealth headers.
        Returns raw text results."""
        logger.info("web", f"Searching: {query}")
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

        for attempt in range(_MAX_RETRIES):
            try:
                if attempt > 0:
                    time.sleep(random.uniform(1.5, 4.0))
                    self._rotate()

                resp = self.session.get(search_url, timeout=15)

                if resp.status_code == 403 or resp.status_code == 429:
                    logger.info("web", f"Search blocked (attempt {attempt + 1}), rotating...")
                    continue

                if resp.status_code >= 400:
                    return None

                # Extract search result snippets from DDG HTML
                return self._parse_ddg_results(resp.text)

            except requests.Timeout:
                logger.info("web", f"Search timeout attempt {attempt + 1}")
            except Exception as e:
                logger.info("web", f"Search error: {e}")
                return None

        return None

    def _rotate(self):
        """Full identity rotation — new headers, new session cookies."""
        self.session.cookies.clear()
        self.session.headers.update(Undercover.get_stealth_headers())

    @staticmethod
    def _extract_text(html: str) -> str:
        """Strip HTML tags and extract readable text content."""
        # Remove script and style blocks entirely
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Convert block elements to newlines
        text = re.sub(r'<(?:br|p|div|h[1-6]|li|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
        # Strip remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        # Collapse whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()[:8000]

    @staticmethod
    def _parse_ddg_results(html: str) -> str:
        """Parse DuckDuckGo HTML results page into readable text."""
        results = []

        # DDG wraps each result in <div class="result ...">
        # Extract result titles and snippets
        title_matches = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippet_matches = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        url_matches = re.findall(r'<a[^>]+class="result__url"[^>]*href="([^"]*)"', html, re.DOTALL)

        for i in range(min(len(title_matches), 10)):
            title = re.sub(r'<[^>]+>', '', title_matches[i]).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_matches[i]).strip() if i < len(snippet_matches) else ""
            url = url_matches[i] if i < len(url_matches) else ""

            results.append(f"[{i+1}] {title}")
            if url:
                results.append(f"    URL: {url}")
            if snippet:
                results.append(f"    {snippet}")
            results.append("")

        if not results:
            # Fallback: just extract all text
            return StealthDrifter._extract_text(html)[:4000]

        return "\n".join(results)[:6000]


def search_stealth(query: str) -> Optional[str]:
    """Convenience function for one-shot stealth search."""
    return StealthDrifter().search(query)


def fetch_stealth(url: str) -> Optional[str]:
    """Convenience function for one-shot stealth fetch."""
    return StealthDrifter().fetch(url)
