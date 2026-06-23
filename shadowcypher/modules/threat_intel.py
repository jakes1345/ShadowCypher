"""
Threat Intelligence — OTX AlienVault + AbuseIPDB integration.

Provides IP, domain, and file hash reputation lookups from two
best-in-class free threat intel feeds. Keys are read from config.json
or environment variables; graceful no-key fallback is built in.

Usage:
    from shadowcypher.modules.threat_intel import threat_intel
    result = threat_intel.lookup_ip("1.2.3.4", on_output=print)
    result = threat_intel.lookup_domain("malicious.example.com")
    result = threat_intel.lookup_hash("d41d8cd98f00b204e9800998ecf8427e")
    summary = threat_intel.lookup("1.2.3.4")  # combined, auto-detects type
"""

from __future__ import annotations
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Callable
from shadowcypher.core.logger import logger
from shadowcypher.core.module import BaseModule

# ── Constants ─────────────────────────────────────────────────────────────────

OTX_BASE       = "https://otx.alienvault.com/api/v1"
ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2"
CACHE_DIR      = os.path.expanduser("~/.shadowcypher/threat_cache")
CACHE_TTL      = 3600  # 1 hour


# ── Result Types ──────────────────────────────────────────────────────────────

class ThreatResult:
    def __init__(self, target: str, target_type: str):
        self.target      = target
        self.target_type = target_type          # ip / domain / hash
        self.malicious   = False
        self.confidence  = 0                    # 0–100
        self.tags: list[str] = []
        self.pulses: int = 0                    # OTX pulse count
        self.abuse_score: int = 0               # AbuseIPDB confidence score
        self.country: str = ""
        self.isp: str = ""
        self.last_seen: str = ""
        self.sources: list[str] = []            # which feeds returned data
        self.raw: dict = {}

    def summary(self) -> str:
        verdict = "MALICIOUS" if self.malicious else "CLEAN"
        lines = [
            f"[TI] {self.target_type.upper()} {self.target}  →  {verdict}  (confidence: {self.confidence}%)",
        ]
        if self.country or self.isp:
            lines.append(f"     Location: {self.country}  ISP: {self.isp}")
        if self.abuse_score:
            lines.append(f"     AbuseIPDB score: {self.abuse_score}/100")
        if self.pulses:
            lines.append(f"     OTX pulses: {self.pulses}")
        if self.tags:
            lines.append(f"     Tags: {', '.join(self.tags[:8])}")
        if self.last_seen:
            lines.append(f"     Last seen: {self.last_seen}")
        lines.append(f"     Sources: {', '.join(self.sources) or 'none'}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "type": self.target_type,
            "malicious": self.malicious,
            "confidence": self.confidence,
            "abuse_score": self.abuse_score,
            "otx_pulses": self.pulses,
            "country": self.country,
            "isp": self.isp,
            "tags": self.tags,
            "sources": self.sources,
        }


# ── Main Module ───────────────────────────────────────────────────────────────

class ThreatIntel(BaseModule):
    """
    Multi-source threat intelligence aggregator.
    Queries OTX and AbuseIPDB in parallel, merges results.
    """

    def __init__(self):
        super().__init__(module_name="threat_intel")
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._cache: dict[str, tuple[float, ThreatResult]] = {}  # key → (ts, result)
        self._lock = threading.Lock()
        self._otx_key      = self._load_key("OTX_API_KEY", "otx_api_key")
        self._abuseipdb_key = self._load_key("ABUSEIPDB_API_KEY", "abuseipdb_api_key")

    def _load_key(self, env_var: str, config_key: str) -> str:
        val = os.environ.get(env_var, "")
        if val:
            return val
        try:
            from shadowcypher.core.config import config
            return getattr(config.intel, config_key, "") or ""
        except Exception:
            return ""

    # ── Public API ────────────────────────────────────────────────────────────

    def lookup(self, target: str, on_output: Callable = None) -> ThreatResult:
        """Auto-detect target type and run the appropriate lookup(s)."""
        t = target.strip()
        # IPv4
        if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", t):
            return self.lookup_ip(t, on_output=on_output)
        # CVE / hash — sha256/sha1/md5
        if re.match(r"^[a-fA-F0-9]{32,64}$", t):
            return self.lookup_hash(t, on_output=on_output)
        # URL → extract domain
        if t.startswith("http://") or t.startswith("https://"):
            parsed = urllib.parse.urlparse(t)
            t = parsed.hostname or t
        return self.lookup_domain(t, on_output=on_output)

    def lookup_ip(self, ip: str, on_output: Callable = None) -> ThreatResult:
        """Query OTX + AbuseIPDB for an IP address."""
        cached = self._get_cache(f"ip:{ip}")
        if cached:
            if on_output:
                on_output(cached.summary() + "\n")
            return cached

        if on_output:
            on_output(f"[TI] Querying threat intel for IP: {ip}\n")

        result = ThreatResult(ip, "ip")

        otx_done     = threading.Event()
        abuse_done   = threading.Event()

        def _otx():
            try:
                self._otx_ip(ip, result)
            except Exception as e:
                logger.warning("threat_intel", f"OTX IP lookup failed: {e}")
            finally:
                otx_done.set()

        def _abuse():
            try:
                self._abuseipdb_check(ip, result)
            except Exception as e:
                logger.warning("threat_intel", f"AbuseIPDB lookup failed: {e}")
            finally:
                abuse_done.set()

        t1 = threading.Thread(target=_otx,   daemon=True)
        t2 = threading.Thread(target=_abuse, daemon=True)
        t1.start()
        t2.start()
        otx_done.wait(timeout=15)
        abuse_done.wait(timeout=15)

        self._merge_verdict(result)
        self._set_cache(f"ip:{ip}", result)

        if on_output:
            on_output(result.summary() + "\n")
        return result

    def lookup_domain(self, domain: str, on_output: Callable = None) -> ThreatResult:
        """Query OTX for a domain or hostname."""
        cached = self._get_cache(f"domain:{domain}")
        if cached:
            if on_output:
                on_output(cached.summary() + "\n")
            return cached

        if on_output:
            on_output(f"[TI] Querying threat intel for domain: {domain}\n")

        result = ThreatResult(domain, "domain")
        try:
            self._otx_domain(domain, result)
        except Exception as e:
            logger.warning("threat_intel", f"OTX domain lookup failed: {e}")

        self._merge_verdict(result)
        self._set_cache(f"domain:{domain}", result)
        if on_output:
            on_output(result.summary() + "\n")
        return result

    def lookup_hash(self, file_hash: str, on_output: Callable = None) -> ThreatResult:
        """Query OTX for a file hash (MD5 / SHA1 / SHA256)."""
        cached = self._get_cache(f"hash:{file_hash}")
        if cached:
            if on_output:
                on_output(cached.summary() + "\n")
            return cached

        if on_output:
            on_output(f"[TI] Querying threat intel for hash: {file_hash[:16]}...\n")

        result = ThreatResult(file_hash, "hash")
        try:
            self._otx_file(file_hash, result)
        except Exception as e:
            logger.warning("threat_intel", f"OTX hash lookup failed: {e}")

        self._merge_verdict(result)
        self._set_cache(f"hash:{file_hash}", result)
        if on_output:
            on_output(result.summary() + "\n")
        return result

    # ── OTX AlienVault ───────────────────────────────────────────────────────

    def _otx_request(self, path: str) -> Optional[dict]:
        """Make an OTX API request. Works with or without API key (anonymous = limited)."""
        url = f"{OTX_BASE}/{path.lstrip('/')}"
        headers = {"User-Agent": "ShadowCypher-ThreatIntel/2.0"}
        if self._otx_key:
            headers["X-OTX-API-KEY"] = self._otx_key
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:  # nosec B310
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                logger.warning("threat_intel", "OTX: API key required or rate-limited")
            return None
        except Exception:
            return None

    def _otx_ip(self, ip: str, result: ThreatResult):
        data = self._otx_request(f"indicators/IPv4/{ip}/general")
        if not data:
            return
        result.sources.append("OTX")
        result.country   = data.get("country_name", "")
        result.pulses    = data.get("pulse_info", {}).get("count", 0)
        result.last_seen = data.get("pulse_info", {}).get("references", [""])[0][:30] if data.get("pulse_info", {}).get("references") else ""
        for pulse in data.get("pulse_info", {}).get("pulses", []):
            result.tags.extend(pulse.get("tags", []))
        # Reputation sub-request
        rep = self._otx_request(f"indicators/IPv4/{ip}/reputation")
        if rep and rep.get("reputation"):
            result.malicious = True

    def _otx_domain(self, domain: str, result: ThreatResult):
        data = self._otx_request(f"indicators/domain/{domain}/general")
        if not data:
            return
        result.sources.append("OTX")
        result.pulses = data.get("pulse_info", {}).get("count", 0)
        for pulse in data.get("pulse_info", {}).get("pulses", []):
            result.tags.extend(pulse.get("tags", []))
        # Malicious check from alexa rank absence + pulse count
        alexa = data.get("alexa", "")
        if result.pulses > 0 and not alexa:
            result.malicious = True

    def _otx_file(self, file_hash: str, result: ThreatResult):
        # OTX normalizes hash size to determine type
        if len(file_hash) == 32:
            indicator_type = "file"
            section = f"indicators/file/{file_hash}/general"
        elif len(file_hash) == 40:
            section = f"indicators/file/{file_hash}/general"
        else:
            section = f"indicators/file/{file_hash}/general"

        data = self._otx_request(section)
        if not data:
            return
        result.sources.append("OTX")
        result.pulses = data.get("pulse_info", {}).get("count", 0)
        for pulse in data.get("pulse_info", {}).get("pulses", []):
            result.tags.extend(pulse.get("tags", []))
        analysis = data.get("analysis", {})
        malware = analysis.get("malware", False) or analysis.get("metadata", {}).get("malware", False)
        if malware or result.pulses > 0:
            result.malicious = True

    # ── AbuseIPDB ────────────────────────────────────────────────────────────

    def _abuseipdb_check(self, ip: str, result: ThreatResult):
        if not self._abuseipdb_key:
            logger.debug("threat_intel", "AbuseIPDB key not configured — skipping")
            return
        url = f"{ABUSEIPDB_BASE}/check?ipAddress={urllib.parse.quote(ip)}&maxAgeInDays=90&verbose"
        headers = {
            "Key": self._abuseipdb_key,
            "Accept": "application/json",
            "User-Agent": "ShadowCypher-ThreatIntel/2.0",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
            abuse_data = data.get("data", {})
            result.sources.append("AbuseIPDB")
            result.abuse_score = abuse_data.get("abuseConfidenceScore", 0)
            result.country     = result.country or abuse_data.get("countryCode", "")
            result.isp         = abuse_data.get("isp", "")
            if result.abuse_score > 25:
                result.malicious = True
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.warning("threat_intel", "AbuseIPDB: invalid API key")
            elif e.code == 429:
                logger.warning("threat_intel", "AbuseIPDB: rate limited")
        except Exception as e:
            logger.warning("threat_intel", f"AbuseIPDB error: {e}")

    # ── Verdict merger ────────────────────────────────────────────────────────

    def _merge_verdict(self, result: ThreatResult):
        """Compute final confidence score from all sources."""
        score = 0
        if result.malicious:
            score += 50
        if result.abuse_score >= 75:
            score += 40
        elif result.abuse_score >= 25:
            score += 20
        if result.pulses >= 5:
            score += 20
        elif result.pulses >= 1:
            score += 10
        result.confidence = min(score, 100)
        result.tags = list(dict.fromkeys(result.tags))[:20]  # dedupe

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _get_cache(self, key: str) -> Optional[ThreatResult]:
        with self._lock:
            entry = self._cache.get(key)
        if entry and (time.time() - entry[0]) < CACHE_TTL:
            return entry[1]
        return None

    def _set_cache(self, key: str, result: ThreatResult):
        with self._lock:
            self._cache[key] = (time.time(), result)


# Global singleton
threat_intel = ThreatIntel()
