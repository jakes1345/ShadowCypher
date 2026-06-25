"""
Security Situation Assessor — rule-based instant triage.

Adapted from POI's intelligence/assessor.py pattern, re-cast for
offensive/defensive security findings instead of geospatial events.

No LLM required — fires in <1ms from in-memory findings.
Designed to be called after every scan session to give the operator
a structured risk summary before the AI analysis runs.

Usage:
    from shadowcypher.core.assessor import assessor
    summary = assessor.assess_findings(cve_matches, threat_results, open_ports)
    print(summary)
"""

from __future__ import annotations
from typing import Optional

# ── Severity ranking ──────────────────────────────────────────────────────────

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0, "unknown": 0}


def _rank(s: str) -> int:
    return SEVERITY_RANK.get(s.lower(), 0)


# ── Security combination patterns ─────────────────────────────────────────────
# Each entry: (set of condition tags that must ALL be present, advisory text)

SECURITY_COMBINATIONS = [
    (
        {"kev_exploited", "epss_high", "port_open"},
        "CRITICAL CHAIN: Known exploited CVE + high exploitation probability + service exposed — "
        "this is an active attack surface. Patch or isolate immediately.",
    ),
    (
        {"kev_exploited", "port_open"},
        "Active exploit (CISA KEV) on an exposed service — federal patch deadline applies. "
        "Treat as P0 regardless of CVSS score.",
    ),
    (
        {"epss_high", "critical_cvss"},
        "High-probability exploit for a CVSS Critical CVE — likely to be weaponized soon if not already. "
        "Prioritize patching over lower-scoring KEV entries.",
    ),
    (
        {"tor_exit", "malicious_ip"},
        "Tor exit node flagged across multiple threat feeds — possible C2 or exfiltration relay.",
    ),
    (
        {"malicious_domain", "malicious_ip"},
        "Both IP and domain are flagged malicious — indicates coordinated malicious infrastructure.",
    ),
    (
        {"high_cvss", "no_auth_required"},
        "Network-exploitable CVE with no authentication — remotely triggerable without credentials.",
    ),
    (
        {"web_vuln", "critical_cvss"},
        "Critical CVE in a web-facing service — assume external exposure unless firewall verified.",
    ),
    (
        {"credential_finding", "lateral_possible"},
        "Credentials found + lateral movement potential — treat as full network compromise scenario.",
    ),
]


# ── Tag extractors ────────────────────────────────────────────────────────────

def _tags_from_cve_matches(cve_matches: list) -> set[str]:
    tags: set[str] = set()
    for m in cve_matches:
        sev = getattr(m, "cvss_severity", "").lower()
        if sev == "critical":
            tags.add("critical_cvss")
        if sev in ("critical", "high"):
            tags.add("high_cvss")
        if getattr(m, "kev_exploited", False):
            tags.add("kev_exploited")
        epss = getattr(m, "epss_score", 0.0)
        if epss >= 0.5:
            tags.add("epss_high")
        vec = getattr(m, "cvss_vector", "").upper()
        if "AV:N" in vec:
            tags.add("network_reachable")
        if "PR:N" in vec and "UI:N" in vec:
            tags.add("no_auth_required")
        desc = getattr(m, "description", "").lower()
        if any(w in desc for w in ("web", "http", "sql", "xss", "injection", "upload")):
            tags.add("web_vuln")
        if any(w in desc for w in ("privilege", "escalation", "sudo", "root")):
            tags.add("lateral_possible")
    return tags


def _tags_from_threat_results(threat_results: list) -> set[str]:
    tags: set[str] = set()
    for r in threat_results:
        if getattr(r, "malicious", False):
            t = getattr(r, "target_type", "")
            if t == "ip":
                tags.add("malicious_ip")
            elif t == "domain":
                tags.add("malicious_domain")
            elif t == "hash":
                tags.add("malicious_hash")
        if "tor-exit-node" in getattr(r, "tags", []):
            tags.add("tor_exit")
        score = getattr(r, "abuse_score", 0)
        if score >= 50:
            tags.add("malicious_ip")
    return tags


def _tags_from_ports(open_ports: list) -> set[str]:
    tags: set[str] = set()
    if open_ports:
        tags.add("port_open")
    for p in open_ports:
        port = p.get("port", 0) if isinstance(p, dict) else getattr(p, "port", 0)
        if port in (80, 443, 8080, 8443):
            tags.add("web_facing")
    return tags


def _tags_from_extra(extra: dict) -> set[str]:
    tags: set[str] = set()
    if extra.get("credentials_found"):
        tags.add("credential_finding")
    if extra.get("lateral_movement"):
        tags.add("lateral_possible")
    return tags


# ── Assessor ──────────────────────────────────────────────────────────────────

class SecurityAssessor:

    def assess_findings(
        self,
        cve_matches: list = None,
        threat_results: list = None,
        open_ports: list = None,
        target: str = "",
        extra: dict = None,
    ) -> str:
        """
        Produce a structured threat assessment from raw scan findings.
        All parameters are optional — pass whatever you have.

        Returns a human-readable assessment string.
        """
        cve_matches    = cve_matches    or []
        threat_results = threat_results or []
        open_ports     = open_ports     or []
        extra          = extra          or {}

        # Collect condition tags
        active_tags = (
            _tags_from_cve_matches(cve_matches)
            | _tags_from_threat_results(threat_results)
            | _tags_from_ports(open_ports)
            | _tags_from_extra(extra)
        )

        # Threat level
        level = self._threat_level(cve_matches, threat_results, active_tags)

        lines = [
            f"THREAT LEVEL: {level.upper()}",
        ]
        if target:
            lines.append(f"TARGET: {target}")

        # Stats
        crit  = [m for m in cve_matches if getattr(m, "cvss_severity", "") == "CRITICAL"]
        high  = [m for m in cve_matches if getattr(m, "cvss_severity", "") == "HIGH"]
        kev   = [m for m in cve_matches if getattr(m, "kev_exploited", False)]
        mal_t = [r for r in threat_results if getattr(r, "malicious", False)]

        if cve_matches:
            lines.append(
                f"CVEs: {len(cve_matches)} total — "
                f"{len(crit)} CRITICAL, {len(high)} HIGH, {len(kev)} in CISA KEV"
            )
        if threat_results:
            lines.append(
                f"THREAT INTEL: {len(mal_t)}/{len(threat_results)} indicators flagged malicious"
            )
        if open_ports:
            lines.append(f"EXPOSURE: {len(open_ports)} open port(s)")

        # Pattern matching — show all matching combinations
        for combo_tags, advisory in SECURITY_COMBINATIONS:
            if combo_tags <= active_tags:
                lines.append(f"PATTERN: {advisory}")

        # Top CVE by risk score (KEV > EPSS > CVSS)
        if cve_matches:
            def _risk(m):
                base = getattr(m, "cvss_score", 0.0)
                epss_bonus = getattr(m, "epss_score", 0.0) * 3
                kev_bonus  = 4.0 if getattr(m, "kev_exploited", False) else 0.0
                return base + epss_bonus + kev_bonus
            top = max(cve_matches, key=_risk)
            kev_str = "  [KEV]" if getattr(top, "kev_exploited", False) else ""
            epss_str = f"  EPSS:{getattr(top, 'epss_score', 0):.1%}" if getattr(top, "epss_score", 0) else ""
            lines.append(
                f"LEAD CVE: {top.cve_id}  CVSS:{getattr(top, 'cvss_score', 0):.1f}{kev_str}{epss_str}"
                f"\n         {getattr(top, 'description', '')[:120]}"
            )

        # Top threat indicator
        if mal_t:
            top_ti = max(mal_t, key=lambda r: getattr(r, "confidence", 0))
            lines.append(
                f"LEAD INDICATOR: {top_ti.target}  "
                f"confidence:{getattr(top_ti, 'confidence', 0)}%  "
                f"sources:{','.join(getattr(top_ti, 'sources', []))}"
            )

        # Remediation priorities (rule-based, no LLM)
        remeds = self._remediations(active_tags, crit, kev)
        if remeds:
            lines.append("REMEDIATION PRIORITIES:")
            for i, r in enumerate(remeds, 1):
                lines.append(f"  {i}. {r}")

        return "\n".join(lines)

    def _threat_level(self, cve_matches: list, threat_results: list,
                      active_tags: set) -> str:
        if "kev_exploited" in active_tags and "port_open" in active_tags:
            return "critical"
        if "critical_cvss" in active_tags and "network_reachable" in active_tags:
            return "critical"
        mal_count = sum(1 for r in threat_results if getattr(r, "malicious", False))
        crit_cves = sum(1 for m in cve_matches if getattr(m, "cvss_severity", "") == "CRITICAL")
        if crit_cves >= 1 or mal_count >= 2:
            return "high"
        high_cves = sum(1 for m in cve_matches if getattr(m, "cvss_severity", "") == "HIGH")
        if high_cves >= 2 or mal_count >= 1:
            return "medium"
        if cve_matches or threat_results:
            return "low"
        return "info"

    def _remediations(self, tags: set, crit_cves: list, kev_cves: list) -> list[str]:
        r = []
        if kev_cves:
            r.append(
                f"Patch {', '.join(m.cve_id for m in kev_cves[:3])} immediately "
                f"(CISA KEV — federal due date applies)"
            )
        if crit_cves and not kev_cves:
            r.append(
                f"Patch CRITICAL CVEs: {', '.join(m.cve_id for m in crit_cves[:3])}"
            )
        if "no_auth_required" in tags and "network_reachable" in tags:
            r.append("Restrict network access to vulnerable service(s) via firewall rule")
        if "tor_exit" in tags:
            r.append("Block Tor exit IPs at perimeter firewall; review outbound connections")
        if "malicious_ip" in tags or "malicious_domain" in tags:
            r.append("Block flagged IPs/domains in firewall and DNS; check for C2 beaconing")
        if "credential_finding" in tags:
            r.append("Rotate all discovered credentials; check for reuse across services")
        if "web_facing" in tags and "web_vuln" in tags:
            r.append("Enable WAF rules for web-facing services with known web vulnerabilities")
        return r


# Global singleton
assessor = SecurityAssessor()
