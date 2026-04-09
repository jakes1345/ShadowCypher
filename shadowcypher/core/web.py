"""
Web Research Module — Apex Sovereign Build.
High-fidelity stealth fetching, anti-bot research, and search automation.
"""

from shadowcypher.core.module import BaseModule
from shadowcypher.core.undercover import Undercover
import requests
import random
import time
import re

class WebResearcher(BaseModule):
    """The 'Specter' web engine of ShadowCypher."""
    
    def __init__(self):
        super().__init__(module_name="web")
        self.session = requests.Session()
        self._rotate_identity()

    def _rotate_identity(self):
        self.session.cookies.clear()
        self.session.headers.update(Undercover.get_stealth_headers())

    def fetch(self, url, timeout=15):
        self.log(f"STEALTH_FETCH: {url}")
        try:
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                return self._extract_text(resp.text)
            self.log(f"FETCH_FAILED: HTTP_{resp.status_code}", "ERROR")
            return None
        except Exception as e:
            self.log(f"FETCH_CRASH: {e}", "CRITICAL")
            return None

    def search_intel(self, query):
        self.log(f"PERFORMING_STEALTH_SEARCH: {query}")
        # Search via DDG (simplified for build)
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        try:
            resp = self.session.get(search_url)
            return self._extract_text(resp.text)[:5000]
        except: return "SEARCH_FAILED"

    def _extract_text(self, html):
        # Human-readable content extractor
        text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()
