"""
Intent detector — maps user messages to security tool actions.

The key insight from real-world local model usage: small models don't reliably
emit tool_call JSON. Instead, detect intent from the user's message directly,
execute the tool, then give the AI the real output to analyze.

Usage:
    from shadowcypher.ai.intent import detect_intent, TOOL_REGISTRY
    intent = detect_intent("scan 192.168.1.1 for open ports")
    # → {"type": "nmap_scan", "target": "192.168.1.1", "confidence": "high"}
"""

from __future__ import annotations
import re
from typing import Optional

# ── Target extractors ─────────────────────────────────────────────────────────

_IP     = r"(\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?)"
_DOMAIN = r"((?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,})"
_URL    = r"(https?://[^\s]+)"
_CVE    = r"(CVE-\d{4}-\d{4,})"
_HASH   = r"([a-fA-F0-9]{32,64})"
_TARGET = rf"(?:{_URL}|{_IP}|{_DOMAIN})"

def _first(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.I)
    return m.group(1) if m else None

def _target(text: str) -> Optional[str]:
    return _first(_URL, text) or _first(_IP, text) or _first(_DOMAIN, text)


# ── Intent patterns ───────────────────────────────────────────────────────────
# Each entry: (regex_trigger, intent_type, target_fn)
# Ordered most-specific first.

_PATTERNS: list[tuple[re.Pattern, str, callable]] = [
    # Port / service scanning
    (re.compile(r"\b(port.?scan|nmap|scan.{0,30}port|open.port|service.detect)", re.I),
     "nmap_scan", _target),

    # Vulnerability scanning
    (re.compile(r"\b(nuclei|vuln.?scan|cve.?scan|scan.{0,20}vuln)", re.I),
     "nuclei_scan", _target),

    # Web app scanning
    (re.compile(r"\b(nikto|web.?scan|http.?scan|scan.{0,20}web)", re.I),
     "nikto_scan", _target),

    # SQL injection
    (re.compile(r"\b(sqlmap|sql.?inject|sqli.{0,20}test)", re.I),
     "sqlmap_scan", _target),

    # Subdomain enumeration
    (re.compile(r"\b(subdomain|subfinder|enumerate.{0,20}domain|dns.?enum)", re.I),
     "subdomain_enum", lambda t: _first(_DOMAIN, t)),

    # CVE lookup
    (re.compile(r"\b(CVE-\d{4}-\d{4,})", re.I),
     "cve_lookup", lambda t: _first(_CVE, t)),

    # IP reputation / threat intel
    (re.compile(r"\b(ip.?rep|abuseipdb|threat.?intel.{0,20}ip|is.{0,10}malicious|lookup.{0,20}ip)", re.I),
     "ip_reputation", lambda t: _first(_IP, t)),

    # Domain / URL reputation
    (re.compile(r"\b(virustotal|vt.?scan|url.?scan|domain.?rep|otx|alienvault)", re.I),
     "domain_reputation", _target),

    # WHOIS
    (re.compile(r"\b(whois|who.?is|domain.?info|registrar)", re.I),
     "whois_lookup", lambda t: _first(_DOMAIN, t) or _first(_IP, t)),

    # OSINT / person lookup
    (re.compile(r"\b(osint|sherlock|username.?search|find.{0,20}person|social.?media.?search)", re.I),
     "osint_lookup", lambda t: re.search(r'["\']([^"\']+)["\']', t) and re.search(r'["\']([^"\']+)["\']', t).group(1)),

    # Hash lookup
    (re.compile(r"\b(hash|md5|sha1|sha256|malware.?hash|file.?hash)", re.I),
     "hash_lookup", lambda t: _first(_HASH, t)),

    # Adaptive full-pipeline auto scan (must be before deep_recon — both match "full scan")
    (re.compile(r"\b(auto.?scan|adaptive.?scan|full.?assess|full.?scan|scan.?everything|run.?all|complete.?scan|pentest)", re.I),
     "auto_scan", _target),

    # Recon / deep scan
    (re.compile(r"\b(recon|footprint|attack.?surface|deep.?scan)", re.I),
     "deep_recon", _target),

    # Ghost mode / Tor
    (re.compile(r"\b(ghost.?mode|enable.?tor|anonymize|stealth.?mode)", re.I),
     "ghost_mode", lambda t: None),
]


# ── Tool registry ─────────────────────────────────────────────────────────────
# Maps intent_type → executor function (lazy-imported at call time)

TOOL_REGISTRY: dict[str, callable] = {}

def _register_tools():
    """Lazy registration — only imports when first needed."""
    global TOOL_REGISTRY
    if TOOL_REGISTRY:
        return

    try:
        from shadowcypher.modules.recon import Recon
        _recon = Recon()
        TOOL_REGISTRY["nmap_scan"]      = lambda t, cb: _recon.pulse_target(t, "Service Fingerprint", on_output=cb)
        TOOL_REGISTRY["deep_recon"]     = lambda t, cb: _recon.deep_recon(t, on_output=cb)
        TOOL_REGISTRY["subdomain_enum"] = lambda t, cb: _recon.subdomain_enum(t, on_output=cb)
        TOOL_REGISTRY["whois_lookup"]   = lambda t, cb: _recon.http_probe(t, on_output=cb)
    except Exception:
        pass

    try:
        from shadowcypher.modules.vuln_scanner import VulnScanner
        _vuln = VulnScanner()
        TOOL_REGISTRY["nuclei_scan"] = lambda t, cb: _vuln.nuclei_scan(t, on_output=cb)
        TOOL_REGISTRY["nikto_scan"]  = lambda t, cb: _vuln.nikto_scan(t, on_output=cb)
        TOOL_REGISTRY["sqlmap_scan"] = lambda t, cb: _vuln.sqlmap_scan(t, on_output=cb)
    except Exception:
        pass

    try:
        from shadowcypher.modules.cve_feed import cve_feed
        TOOL_REGISTRY["cve_lookup"] = lambda t, cb: _cve_lookup(cve_feed, t, cb)
    except Exception:
        pass

    try:
        from shadowcypher.modules.threat_intel import threat_intel
        TOOL_REGISTRY["ip_reputation"]     = lambda t, cb: _ti_lookup(threat_intel, t, "ip", cb)
        TOOL_REGISTRY["domain_reputation"] = lambda t, cb: _ti_lookup(threat_intel, t, "domain", cb)
        TOOL_REGISTRY["hash_lookup"]       = lambda t, cb: _ti_lookup(threat_intel, t, "hash", cb)
    except Exception:
        pass

    try:
        from shadowcypher.ai.auto_scan import auto_scan as _auto_scan
        def _run_auto_scan(t, cb):
            result = _auto_scan.run(t, on_output=cb)
            return result.report or result.assessment
        TOOL_REGISTRY["auto_scan"] = _run_auto_scan
    except Exception:
        pass


def _cve_lookup(feed, cve_id: str, cb) -> str:
    results = feed.search(cve_id, on_output=cb)
    if not results:
        return f"No NVD data found for {cve_id}"
    r = results[0]
    return (f"{r.get('id')}  CVSS:{r.get('score')}  [{r.get('severity')}]\n"
            f"{r.get('desc', '')[:400]}")

def _ti_lookup(ti, target: str, kind: str, cb) -> str:
    if kind == "ip":
        result = ti.lookup_ip(target, on_output=cb)
    elif kind == "domain":
        result = ti.lookup_domain(target, on_output=cb)
    else:
        result = ti.lookup_hash(target, on_output=cb)
    return result or "No threat intel data found."


# ── Public API ────────────────────────────────────────────────────────────────

def detect_intent(query: str) -> dict:
    """
    Detect security tool intent in a user query.

    Returns:
        {
            "type": str,         # intent type or "general"
            "target": str|None,  # extracted target
            "confidence": str,   # "high" | "medium" | "none"
            "matched": str,      # which pattern matched
        }
    """
    for pattern, intent_type, target_fn in _PATTERNS:
        if pattern.search(query):
            target = target_fn(query)
            confidence = "high" if target else "medium"
            return {
                "type": intent_type,
                "target": target,
                "confidence": confidence,
                "matched": intent_type,
            }

    # Fallback: if target looks like a URL, default to web scan
    url_target = _first(_URL, query)
    if url_target:
        return {"type": "nikto_scan", "target": url_target, "confidence": "medium", "matched": "url_fallback"}

    return {"type": "general", "target": None, "confidence": "none", "matched": ""}


def execute_intent(intent: dict, on_output: callable = None) -> Optional[str]:
    """
    Execute the tool for a detected intent. Returns raw tool output as string.
    Returns None if intent is general or tool unavailable.
    """
    if intent["type"] == "general" or not intent.get("target"):
        return None

    _register_tools()
    fn = TOOL_REGISTRY.get(intent["type"])
    if not fn:
        return None

    output_lines: list[str] = []

    def _collect(line: str):
        output_lines.append(line)
        if on_output:
            on_output(line)

    try:
        fn(intent["target"], _collect)
    except Exception as e:
        return f"[TOOL_ERROR] {intent['type']} failed: {e}"

    return "".join(output_lines) or None


def build_analysis_prompt(query: str, tool_output: str, intent: dict) -> str:
    """
    Build the AI prompt that injects real tool output for analysis.
    This is sent to the AI instead of the raw user query.
    """
    return f"""You are analyzing REAL tool output from a live security scan.
The following results were produced by actual tools running on the operator's system.
They are NOT fabricated — analyze them as a senior security engineer would.

## Tool Executed
Intent: {intent['type']} | Target: {intent.get('target', 'unknown')}

## Real Output
```
{tool_output[:8000]}
```

## Operator Query
{query}

## Instructions
- Summarize key findings by severity (Critical → High → Medium → Low)
- Reference specific ports, services, versions, CVE IDs found in the output
- Map findings to MITRE ATT&CK technique IDs where relevant
- Provide 3-5 concrete remediation actions
- Do NOT repeat raw output verbatim — synthesize it
- If the output shows errors or no results, say so clearly"""
