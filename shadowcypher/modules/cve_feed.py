"""
Live CVE Intelligence Feed — NIST NVD API v2.0 Integration.

Auto-polls the National Vulnerability Database for fresh CVEs,
correlates them against your active scan results and service banners,
and scores each match by CVSS severity. Zero external dependencies
beyond the standard library (uses urllib). Fully sovereign — no telemetry.

Usage:
    from shadowcypher.modules.cve_feed import cve_feed
    results = cve_feed.correlate_target("192.168.1.1", services=["apache 2.4.51", "openssh 8.2"])
    cve_feed.start_background_poll()   # fetch new CVEs every 6h
"""

import json
import time
import threading
import urllib.request
import urllib.parse
import urllib.error
import os
import re
from typing import Optional, Callable
from dataclasses import dataclass, field
from shadowcypher.core.logger import logger
from shadowcypher.core.module import BaseModule

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CACHE_DIR = os.path.expanduser("~/.shadowcypher/cve_cache")
CACHE_TTL_HOURS = 6


@dataclass
class CVEMatch:
    cve_id: str
    description: str
    cvss_score: float
    cvss_severity: str        # CRITICAL / HIGH / MEDIUM / LOW
    cvss_vector: str
    published: str
    matched_service: str      # which banner/service triggered this match
    references: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cve_id": self.cve_id,
            "severity": self.cvss_severity,
            "score": self.cvss_score,
            "service": self.matched_service,
            "description": self.description[:200],
            "published": self.published,
            "references": self.references[:3],
        }

    def __str__(self) -> str:
        bar = "█" * int(self.cvss_score) + "░" * (10 - int(self.cvss_score))
        return (f"[{self.cvss_severity:8s}] {self.cve_id}  CVSS:{self.cvss_score:4.1f}  "
                f"{bar}  → {self.matched_service}\n"
                f"           {self.description[:120]}...")


class CVEFeed(BaseModule):
    """
    Real-time CVE intelligence engine. Polls NVD, caches results locally,
    and correlates raw service banners against active vulnerabilities.
    """

    def __init__(self):
        super().__init__(module_name="cve_feed")
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._cache: dict = {}           # keyword → [CVE dicts]
        self._cache_ts: dict = {}        # keyword → fetch timestamp
        self._lock = threading.Lock()
        self._poll_thread: Optional[threading.Thread] = None
        self._polling = False
        self._on_new_cve: Optional[Callable] = None
        self._load_disk_cache()

    # ── Public API ────────────────────────────────────────────────────────────

    def correlate_target(
        self,
        target: str,
        services: list = None,
        on_output: Callable = None,
    ) -> list[CVEMatch]:
        """
        Correlate a target's service banners against the live CVE database.

        Args:
            target:   IP or hostname (for logging only).
            services: List of service strings e.g. ["apache 2.4.51", "openssh 8.2p1"].
                      If None, auto-extracts keywords from nmap-style banners.
        Returns:
            List of CVEMatch sorted by CVSS score descending.
        """
        if not services:
            if on_output:
                on_output(f"[CVE] No services provided for {target} — nothing to correlate.\n")
            return []

        if on_output:
            on_output(f"[CVE] Correlating {len(services)} services against NVD for {target}...\n")

        all_matches: list[CVEMatch] = []
        seen_cves: set = set()

        for banner in services:
            keywords = self._extract_keywords(banner)
            for kw in keywords:
                cves = self._fetch_cves(kw, on_output=on_output)
                for cve in cves:
                    cid = cve.get("id", "")
                    if cid in seen_cves:
                        continue
                    seen_cves.add(cid)
                    match = self._score_match(cve, banner)
                    if match:
                        all_matches.append(match)

        # Sort: CRITICAL first, then by score
        all_matches.sort(key=lambda x: x.cvss_score, reverse=True)

        if on_output:
            on_output(f"[CVE] Found {len(all_matches)} CVE(s) for {target}\n")
            crit = [m for m in all_matches if m.cvss_severity == "CRITICAL"]
            high = [m for m in all_matches if m.cvss_severity == "HIGH"]
            if crit:
                on_output(f"[CVE] ⚠️  CRITICAL: {len(crit)} CVE(s) require immediate attention\n")
            if high:
                on_output(f"[CVE] 🔴 HIGH: {len(high)} CVE(s)\n")
            for m in all_matches[:10]:
                on_output(str(m) + "\n")

        return all_matches

    def fetch_recent(self, days: int = 7, on_output: Callable = None) -> list[dict]:
        """Fetch CVEs published in the last N days from NVD."""
        import datetime
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(days=days)
        fmt = "%Y-%m-%dT%H:%M:%S.000"
        params = {
            "pubStartDate": start.strftime(fmt),
            "pubEndDate": end.strftime(fmt),
            "resultsPerPage": 100,
        }
        if on_output:
            on_output(f"[CVE] Fetching CVEs published in the last {days} days...\n")
        data = self._nvd_request(params, on_output=on_output)
        cves = data.get("vulnerabilities", []) if data else []
        if on_output:
            on_output(f"[CVE] Retrieved {len(cves)} recent CVE(s) from NVD\n")
        return cves

    def search(self, keyword: str, on_output: Callable = None) -> list[dict]:
        """Search NVD for CVEs matching a keyword."""
        return self._fetch_cves(keyword, force_refresh=True, on_output=on_output)

    def start_background_poll(self, interval_hours: int = 6,
                               on_new_cve: Callable = None):
        """Start background thread that re-fetches CVE data periodically."""
        if self._polling:
            return
        self._polling = True
        self._on_new_cve = on_new_cve

        def _loop():
            while self._polling:
                logger.info("cve_feed", "BACKGROUND_POLL: refreshing CVE cache from NVD...")
                self._refresh_all_cache()
                time.sleep(interval_hours * 3600)

        self._poll_thread = threading.Thread(target=_loop, daemon=True, name="CVEFeedPoller")
        self._poll_thread.start()
        logger.info("cve_feed", f"CVE background poll started (every {interval_hours}h)")

    def stop_background_poll(self):
        self._polling = False

    def get_cache_summary(self) -> dict:
        with self._lock:
            return {
                "keywords_cached": len(self._cache),
                "total_cves": sum(len(v) for v in self._cache.values()),
                "oldest_entry_hours": self._oldest_cache_age(),
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _extract_keywords(self, banner: str) -> list[str]:
        """
        Extract searchable CPE/product keywords from a service banner.
        e.g. "Apache httpd 2.4.51 (Debian)" → ["apache httpd 2.4.51", "apache"]
        """
        banner = banner.strip().lower()
        keywords = []

        # Pattern: "product version"
        version_match = re.match(r"([\w\s\-\.]+?)\s+([\d]+\.[\d]+[\.\d]*)", banner)
        if version_match:
            full = f"{version_match.group(1).strip()} {version_match.group(2)}"
            keywords.append(full)
            keywords.append(version_match.group(1).strip())

        # Fallback: first word(s)
        words = banner.split()
        if words and words[0] not in keywords:
            keywords.append(words[0])
        if len(words) >= 2:
            keywords.append(" ".join(words[:2]))

        return list(dict.fromkeys(kw for kw in keywords if len(kw) >= 3))

    def _fetch_cves(self, keyword: str, force_refresh: bool = False,
                    on_output: Callable = None) -> list[dict]:
        """Fetch CVEs for a keyword, using cache if fresh enough."""
        with self._lock:
            cached_ts = self._cache_ts.get(keyword, 0)
            age_hours = (time.time() - cached_ts) / 3600
            if not force_refresh and keyword in self._cache and age_hours < CACHE_TTL_HOURS:
                return self._cache[keyword]

        if on_output:
            on_output(f"[CVE] Querying NVD: {keyword!r}...\n")

        data = self._nvd_request({"keywordSearch": keyword, "resultsPerPage": 50},
                                  on_output=on_output)
        cves = []
        if data:
            for vuln in data.get("vulnerabilities", []):
                cve_obj = vuln.get("cve", {})
                if cve_obj:
                    cves.append(self._normalize_cve(cve_obj))

        with self._lock:
            self._cache[keyword] = cves
            self._cache_ts[keyword] = time.time()
            self._save_disk_cache(keyword, cves)

        return cves

    def _nvd_request(self, params: dict, on_output: Callable = None) -> Optional[dict]:
        """Make a rate-limited request to NVD API v2."""
        url = f"{NVD_API_BASE}?{urllib.parse.urlencode(params)}"
        headers = {"User-Agent": "ShadowCypher-CVEFeed/2.0"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                time.sleep(0.6)  # NVD rate limit: 5 req/30s without API key
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"vulnerabilities": []}
            if e.code == 429:
                if on_output:
                    on_output("[CVE] NVD rate limit hit — waiting 30s...\n")
                time.sleep(30)
                return None
            logger.warning("cve_feed", f"NVD HTTP error: {e.code}")
            return None
        except Exception as e:
            logger.warning("cve_feed", f"NVD request failed: {e}")
            return None

    def _normalize_cve(self, cve: dict) -> dict:
        """Flatten NVD CVE v2 object to a simple dict."""
        cve_id = cve.get("id", "CVE-UNKNOWN")
        desc = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")
                break

        # Extract CVSS score (v3.1 preferred, fallback v2)
        score, vector, severity = 0.0, "", "UNKNOWN"
        metrics = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                m = metrics[key][0]
                cvss_data = m.get("cvssData", m)
                score = float(cvss_data.get("baseScore", 0))
                vector = cvss_data.get("vectorString", "")
                severity = cvss_data.get("baseSeverity", m.get("baseSeverity", "UNKNOWN")).upper()
                break

        refs = [r.get("url", "") for r in cve.get("references", [])[:5]]
        published = cve.get("published", "")[:10]

        return {
            "id": cve_id, "desc": desc, "score": score,
            "vector": vector, "severity": severity,
            "published": published, "refs": refs,
        }

    def _score_match(self, cve: dict, banner: str) -> Optional[CVEMatch]:
        """Determine if a CVE matches a service banner and return a CVEMatch."""
        if not cve.get("id"):
            return None
        return CVEMatch(
            cve_id=cve["id"],
            description=cve.get("desc", "No description"),
            cvss_score=cve.get("score", 0.0),
            cvss_severity=cve.get("severity", "UNKNOWN"),
            cvss_vector=cve.get("vector", ""),
            published=cve.get("published", ""),
            matched_service=banner,
            references=cve.get("refs", []),
        )

    def _refresh_all_cache(self):
        with self._lock:
            keywords = list(self._cache.keys())
        for kw in keywords:
            self._fetch_cves(kw, force_refresh=True)

    def _save_disk_cache(self, keyword: str, cves: list):
        safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", keyword)
        path = os.path.join(CACHE_DIR, f"{safe}.json")
        try:
            with open(path, "w") as f:
                json.dump({"ts": time.time(), "cves": cves}, f)
        except Exception:
            pass

    def _load_disk_cache(self):
        if not os.path.isdir(CACHE_DIR):
            return
        for fname in os.listdir(CACHE_DIR):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(CACHE_DIR, fname)) as f:
                    data = json.load(f)
                keyword = fname[:-5].replace("_", " ")
                age = (time.time() - data.get("ts", 0)) / 3600
                if age < CACHE_TTL_HOURS * 2:  # accept up to 2x TTL for cold start
                    self._cache[keyword] = data.get("cves", [])
                    self._cache_ts[keyword] = data.get("ts", 0)
            except Exception:
                pass
        if self._cache:
            logger.info("cve_feed", f"Loaded {len(self._cache)} keyword(s) from disk cache")

    def _oldest_cache_age(self) -> float:
        if not self._cache_ts:
            return 0.0
        oldest = min(self._cache_ts.values())
        return round((time.time() - oldest) / 3600, 1)


cve_feed = CVEFeed()
