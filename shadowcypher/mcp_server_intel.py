#!/usr/bin/env python3
"""
SHADOWCYPHER INTEL MCP SERVER — Threat intelligence, CVE, OSINT, MITRE ATT&CK

Tools exposed:
  shadowcypher_threat_lookup  — IP/domain/hash reputation (OTX, AbuseIPDB, URLhaus)
  shadowcypher_cve_lookup     — CVE details + EPSS score from NVD
  shadowcypher_cve_correlate  — match CVEs against a service banner list
  shadowcypher_osint          — WHOIS, DNS, SSL cert, HTTP headers, tech detect
  shadowcypher_mitre_tag      — tag a finding/tool against ATT&CK techniques

Start:  python3 shadowcypher/mcp_server_intel.py
Config: add 'shadow-cypher-intel' to mcpServers in .claude/settings.json
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

JSONRPC_VERSION    = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

# ── Config helpers ─────────────────────────────────────────────────────────────

def _load_config():
    paths = [
        os.path.expanduser("~/.shadowcypher/config.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

_CFG = _load_config()

def _key(name, env_var):
    return os.environ.get(env_var) or _CFG.get(name, "")

def _http_get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "timed out", 1
    except Exception as e:
        return str(e), 1

# ── MITRE ATT&CK (offline) ────────────────────────────────────────────────────

_TECHNIQUES = {
    "T1595": ("Active Scanning", "Reconnaissance", "TA0043"),
    "T1595.001": ("Scanning IP Blocks", "Reconnaissance", "TA0043"),
    "T1595.002": ("Vulnerability Scanning", "Reconnaissance", "TA0043"),
    "T1590": ("Gather Victim Network Information", "Reconnaissance", "TA0043"),
    "T1590.002": ("DNS", "Reconnaissance", "TA0043"),
    "T1591": ("Gather Victim Org Information", "Reconnaissance", "TA0043"),
    "T1592": ("Gather Victim Host Information", "Reconnaissance", "TA0043"),
    "T1593": ("Search Open Websites/Domains", "Reconnaissance", "TA0043"),
    "T1596": ("Search Open Technical Databases", "Reconnaissance", "TA0043"),
    "T1588": ("Obtain Capabilities", "Resource Development", "TA0042"),
    "T1190": ("Exploit Public-Facing Application", "Initial Access", "TA0001"),
    "T1566": ("Phishing", "Initial Access", "TA0001"),
    "T1566.002": ("Spearphishing Link", "Initial Access", "TA0001"),
    "T1078": ("Valid Accounts", "Initial Access", "TA0001"),
    "T1059": ("Command and Scripting Interpreter", "Execution", "TA0002"),
    "T1059.004": ("Unix Shell", "Execution", "TA0002"),
    "T1203": ("Exploitation for Client Execution", "Execution", "TA0002"),
    "T1068": ("Exploitation for Privilege Escalation", "Privilege Escalation", "TA0004"),
    "T1027": ("Obfuscated Files or Information", "Defense Evasion", "TA0005"),
    "T1036": ("Masquerading", "Defense Evasion", "TA0005"),
    "T1070": ("Indicator Removal", "Defense Evasion", "TA0005"),
    "T1090": ("Proxy", "Defense Evasion", "TA0005"),
    "T1090.003": ("Multi-hop Proxy", "Defense Evasion", "TA0005"),
    "T1572": ("Protocol Tunneling", "Command and Control", "TA0011"),
    "T1539": ("Steal Web Session Cookie", "Credential Access", "TA0006"),
    "T1557": ("Adversary-in-the-Middle", "Credential Access", "TA0006"),
    "T1110": ("Brute Force", "Credential Access", "TA0006"),
    "T1040": ("Network Sniffing", "Credential Access", "TA0006"),
    "T1046": ("Network Service Discovery", "Discovery", "TA0007"),
    "T1082": ("System Information Discovery", "Discovery", "TA0007"),
    "T1083": ("File and Directory Discovery", "Discovery", "TA0007"),
    "T1087": ("Account Discovery", "Discovery", "TA0007"),
    "T1069": ("Permission Groups Discovery", "Discovery", "TA0007"),
    "T1120": ("Peripheral Device Discovery", "Discovery", "TA0007"),
    "T1135": ("Network Share Discovery", "Discovery", "TA0007"),
    "T1021": ("Remote Services", "Lateral Movement", "TA0008"),
    "T1021.004": ("SSH", "Lateral Movement", "TA0008"),
    "T1021.002": ("SMB/Windows Admin Shares", "Lateral Movement", "TA0008"),
    "T1119": ("Automated Collection", "Collection", "TA0009"),
    "T1113": ("Screen Capture", "Collection", "TA0009"),
    "T1071": ("Application Layer Protocol", "Command and Control", "TA0011"),
    "T1573": ("Encrypted Channel", "Command and Control", "TA0011"),
    "T1048": ("Exfiltration Over Alternative Protocol", "Exfiltration", "TA0010"),
    "T1041": ("Exfiltration Over C2 Channel", "Exfiltration", "TA0010"),
}

_KEYWORD_MAP = {
    r"\bnmap\b": ["T1046", "T1595.001"],
    r"\bport.scan": ["T1046", "T1595"],
    r"\bsubdomain": ["T1590.002", "T1593"],
    r"\bwhois\b": ["T1591", "T1596"],
    r"\bdns\b": ["T1590.002"],
    r"\bssl\b": ["T1592"],
    r"\bssh\b": ["T1021.004"],
    r"\bsmb\b": ["T1021.002"],
    r"\bphish": ["T1566", "T1566.002"],
    r"\bbruteforc|brute.forc": ["T1110"],
    r"\bsniff|pcap|wireshark": ["T1040"],
    r"\bproxy|proxychains": ["T1090"],
    r"\btor\b": ["T1090.003"],
    r"\bsql.inject": ["T1190"],
    r"\bxss\b|cross.site.script": ["T1059"],
    r"\bprivilege.escal|privesc": ["T1068"],
    r"\bpersisten": ["T1078"],
    r"\bexfiltr": ["T1048"],
    r"\bcooki": ["T1539"],
    r"\bmitm|man.in.the.middle": ["T1557"],
    r"\bvulner|exploit": ["T1190", "T1203"],
}

def _mitre_tag(text: str) -> list:
    ids_seen: set = set()
    results = []
    lower = text.lower()
    for pattern, technique_ids in _KEYWORD_MAP.items():
        if re.search(pattern, lower):
            for tid in technique_ids:
                if tid not in ids_seen and tid in _TECHNIQUES:
                    ids_seen.add(tid)
                    name, tactic, tactic_id = _TECHNIQUES[tid]
                    results.append({"id": tid, "name": name, "tactic": tactic, "tactic_id": tactic_id})
    # also accept explicit T#### IDs
    for m in re.finditer(r"T\d{4}(?:\.\d{3})?", text.upper()):
        tid = m.group(0)
        if tid not in ids_seen and tid in _TECHNIQUES:
            ids_seen.add(tid)
            name, tactic, tactic_id = _TECHNIQUES[tid]
            results.append({"id": tid, "name": name, "tactic": tactic, "tactic_id": tactic_id})
    return results

# ── Threat Intel ──────────────────────────────────────────────────────────────

def _detect_type(target: str) -> str:
    if re.match(r"^[0-9a-fA-F]{32,64}$", target):
        return "hash"
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
        return "ip"
    return "domain"

def _ti_otx(target: str, target_type: str, api_key: str) -> dict:
    if not api_key:
        return {}
    try:
        section = {"ip": "IPv4", "domain": "domain", "hash": "file"}[target_type]
        url = f"https://otx.alienvault.com/api/v1/indicators/{section}/{urllib.parse.quote(target)}/general"
        data = _http_get(url, headers={"X-OTX-API-KEY": api_key})
        pulses = data.get("pulse_info", {}).get("count", 0)
        tags = []
        for p in data.get("pulse_info", {}).get("pulses", [])[:5]:
            tags += p.get("tags", [])
        return {"pulses": pulses, "tags": list(set(tags))[:10], "source": "OTX"}
    except Exception as e:
        return {"error": str(e)}

def _ti_abuseipdb(ip: str, api_key: str) -> dict:
    if not api_key:
        return {}
    try:
        url = f"https://api.abuseipdb.com/api/v2/check?ipAddress={urllib.parse.quote(ip)}&maxAgeInDays=90&verbose"
        data = _http_get(url, headers={"Key": api_key, "Accept": "application/json"})
        d = data.get("data", {})
        return {
            "abuse_score": d.get("abuseConfidenceScore", 0),
            "total_reports": d.get("totalReports", 0),
            "country": d.get("countryCode", ""),
            "isp": d.get("isp", ""),
            "last_seen": d.get("lastReportedAt", ""),
            "source": "AbuseIPDB",
        }
    except Exception as e:
        return {"error": str(e)}

def _ti_urlhaus(target: str, target_type: str) -> dict:
    try:
        if target_type == "hash":
            url = "https://urlhaus-api.abuse.ch/v1/payload/"
            data = _http_get_post(url, f"md5_hash={urllib.parse.quote(target)}")
        elif target_type == "domain":
            url = "https://urlhaus-api.abuse.ch/v1/host/"
            data = _http_get_post(url, f"host={urllib.parse.quote(target)}")
        else:
            return {}
        if data.get("query_status") in ("no_results", "invalid_md5"):
            return {"source": "URLhaus", "found": False}
        return {"source": "URLhaus", "found": True, "status": data.get("query_status"),
                "url_count": len(data.get("urls", []))}
    except Exception:
        return {}

def _http_get_post(url, body):
    req = urllib.request.Request(url, data=body.encode(), method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def tool_threat_lookup(target: str) -> dict:
    target_type = _detect_type(target)
    otx_key  = _key("otx_api_key", "OTX_API_KEY")
    abuse_key = _key("abuseipdb_api_key", "ABUSEIPDB_API_KEY")

    result = {"target": target, "type": target_type, "malicious": False,
              "confidence": 0, "sources": [], "details": {}}

    otx = _ti_otx(target, target_type, otx_key)
    if otx and not otx.get("error"):
        result["sources"].append("OTX")
        result["details"]["otx"] = otx
        if otx.get("pulses", 0) > 0:
            result["malicious"] = True
            result["confidence"] = min(100, otx["pulses"] * 10)
            result["tags"] = otx.get("tags", [])

    if target_type == "ip":
        abuse = _ti_abuseipdb(target, abuse_key)
        if abuse and not abuse.get("error"):
            result["sources"].append("AbuseIPDB")
            result["details"]["abuseipdb"] = abuse
            score = abuse.get("abuse_score", 0)
            if score > 25:
                result["malicious"] = True
                result["confidence"] = max(result["confidence"], score)
            result["country"] = abuse.get("country", "")
            result["isp"] = abuse.get("isp", "")

    if target_type in ("hash", "domain"):
        urlhaus = _ti_urlhaus(target, target_type)
        if urlhaus:
            result["sources"].append("URLhaus")
            result["details"]["urlhaus"] = urlhaus
            if urlhaus.get("found"):
                result["malicious"] = True
                result["confidence"] = max(result["confidence"], 75)

    if not result["sources"]:
        result["warning"] = "No API keys configured. Set OTX_API_KEY and ABUSEIPDB_API_KEY."

    result["verdict"] = "MALICIOUS" if result["malicious"] else "CLEAN"
    return result

# ── CVE Feed ──────────────────────────────────────────────────────────────────

def tool_cve_lookup(cve_id: str) -> dict:
    try:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={urllib.parse.quote(cve_id)}"
        data = _http_get(url)
        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return {"error": f"CVE not found: {cve_id}"}
        cve = vulns[0]["cve"]
        desc = next((d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"), "")
        metrics = cve.get("metrics", {})
        score = None
        severity = None
        for mk in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if mk in metrics and metrics[mk]:
                cv = metrics[mk][0].get("cvssData", {})
                score = cv.get("baseScore")
                severity = cv.get("baseSeverity") or metrics[mk][0].get("baseSeverity")
                break

        # EPSS
        epss_score = None
        try:
            ep = _http_get(f"https://api.first.org/data/v1/epss?cve={cve_id}")
            if ep.get("data"):
                epss_score = float(ep["data"][0].get("epss", 0))
        except Exception:
            pass

        refs = [r["url"] for r in cve.get("references", [])[:5]]
        return {
            "cve_id": cve_id,
            "description": desc,
            "cvss_score": score,
            "severity": severity,
            "epss_score": epss_score,
            "published": cve.get("published", ""),
            "references": refs,
        }
    except Exception as e:
        return {"error": str(e)}

def tool_cve_correlate(target: str, services: list) -> dict:
    matches = []
    for svc in services[:10]:
        keyword = re.sub(r"\s+\d[\d.]*", "", svc).strip()
        try:
            url = (f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                   f"?keywordSearch={urllib.parse.quote(keyword)}&cvssV3Severity=HIGH"
                   f"&resultsPerPage=5")
            data = _http_get(url, timeout=20)
            for v in data.get("vulnerabilities", []):
                cve = v["cve"]
                cid = cve["id"]
                desc = next((d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"), "")[:200]
                metrics = cve.get("metrics", {})
                score = None
                for mk in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                    if mk in metrics and metrics[mk]:
                        score = metrics[mk][0].get("cvssData", {}).get("baseScore")
                        break
                matches.append({"service": svc, "cve_id": cid, "cvss_score": score, "description": desc})
            time.sleep(0.6)  # NVD rate limit
        except Exception as e:
            matches.append({"service": svc, "error": str(e)})
    matches.sort(key=lambda x: x.get("cvss_score") or 0, reverse=True)
    return {"target": target, "service_count": len(services), "matches": matches}

# ── OSINT ─────────────────────────────────────────────────────────────────────

def tool_osint(target: str, check_type: str = "all") -> dict:
    result: dict = {"target": target, "check_type": check_type}
    checks = check_type.lower()

    if checks in ("all", "whois"):
        out, rc = run(["whois", target], timeout=15)
        if rc == 0 and out:
            lines = [ln for ln in out.splitlines() if ln.strip() and not ln.startswith("%")][:30]
            result["whois"] = "\n".join(lines)

    if checks in ("all", "dns"):
        records = {}
        for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
            out, rc = run(["dig", "+short", rtype, target])
            if rc == 0 and out:
                records[rtype] = out.splitlines()
        result["dns"] = records

    if checks in ("all", "ssl"):
        out, rc = run(["timeout", "10", "openssl", "s_client", "-connect",
                       f"{target}:443", "-showcerts", "</dev/null"], timeout=15)
        if rc == 0 and out:
            cert_lines = []
            for line in out.splitlines():
                if "subject=" in line or "issuer=" in line or "Not Before" in line or "Not After" in line:
                    cert_lines.append(line.strip())
            result["ssl"] = "\n".join(cert_lines) or out[:500]

    if checks in ("all", "headers"):
        url = target if target.startswith("http") else f"https://{target}"
        out, rc = run(["curl", "-sI", "--max-time", "10", url])
        if rc == 0 and out:
            result["http_headers"] = out[:1000]

    if checks in ("all", "tech"):
        url = target if target.startswith("http") else f"https://{target}"
        if shutil.which("whatweb"):
            out, rc = run(["whatweb", "--no-errors", url], timeout=20)
            result["tech"] = out[:500] if rc == 0 else None
        elif shutil.which("httpx"):
            out, rc = run(["httpx", "-u", url, "-silent", "-tech-detect", "-title",
                           "-status-code", "-no-color"], timeout=20)
            result["tech"] = out[:500] if rc == 0 else None

    if checks in ("all", "asn"):
        # Resolve IP then query BGP
        try:
            ip = socket.gethostbyname(target)
            result["resolved_ip"] = ip
            out, rc = run(["whois", "-h", "whois.cymru.com", f" -v {ip}"], timeout=10)
            if rc == 0:
                result["asn"] = out[:300]
        except Exception:
            pass

    return result

# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "shadowcypher_threat_lookup": {
        "description": (
            "Look up the reputation of an IP address, domain name, or file hash "
            "across OTX AlienVault, AbuseIPDB, and URLhaus. Returns verdict (MALICIOUS/CLEAN), "
            "confidence score, country, ISP, tags, and per-source details."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP address, domain name, or MD5/SHA256 file hash"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_threat_lookup(p["target"])
    },
    "shadowcypher_cve_lookup": {
        "description": (
            "Look up a specific CVE by ID (e.g. CVE-2024-1234). Returns CVSS score, severity, "
            "EPSS exploitation probability, description, and reference links from NVD."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cve_id": {"type": "string", "description": "CVE ID in format CVE-YYYY-NNNNN"}
            },
            "required": ["cve_id"]
        },
        "handler": lambda p: tool_cve_lookup(p["cve_id"])
    },
    "shadowcypher_cve_correlate": {
        "description": (
            "Given a target and a list of service banners (e.g. 'Apache 2.4.51', 'OpenSSH 8.2'), "
            "query NVD for HIGH/CRITICAL CVEs matching each service. Returns ranked vulnerability matches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target hostname or IP being assessed"},
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Service banner strings, e.g. ['Apache httpd 2.4.51', 'OpenSSH 7.9']"
                }
            },
            "required": ["target", "services"]
        },
        "handler": lambda p: tool_cve_correlate(p["target"], p.get("services", []))
    },
    "shadowcypher_osint": {
        "description": (
            "Passive OSINT on a target domain or IP. Returns WHOIS, DNS records, SSL certificate, "
            "HTTP headers, technology stack, and ASN/BGP info. "
            "check_type: 'all' | 'whois' | 'dns' | 'ssl' | 'headers' | 'tech' | 'asn'"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Domain name or IP address"},
                "check_type": {
                    "type": "string",
                    "enum": ["all", "whois", "dns", "ssl", "headers", "tech", "asn"],
                    "default": "all",
                    "description": "Which checks to run"
                }
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_osint(p["target"], p.get("check_type", "all"))
    },
    "shadowcypher_mitre_tag": {
        "description": (
            "Tag a finding description, tool name, or technique text against MITRE ATT&CK. "
            "Returns matching technique IDs, names, and tactics. Works offline — no API call."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Finding text, tool name, or technique description to tag"}
            },
            "required": ["text"]
        },
        "handler": lambda p: {"tags": _mitre_tag(p["text"]), "input": p["text"]}
    },
}

# ── MCP protocol ──────────────────────────────────────────────────────────────

def handle_request(request):
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": JSONRPC_VERSION, "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "shadow-cypher-intel", "version": "1.0.0"}
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return {
            "jsonrpc": JSONRPC_VERSION, "id": req_id,
            "result": {"tools": [
                {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
                for n, t in TOOLS.items()
            ]}
        }
    elif method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        if name not in TOOLS:
            return {"jsonrpc": JSONRPC_VERSION, "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        try:
            result = TOOLS[name]["handler"](args)
            return {"jsonrpc": JSONRPC_VERSION, "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
        except Exception as e:
            return {"jsonrpc": JSONRPC_VERSION, "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                               "isError": True}}
    elif method == "ping":
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {}}
    else:
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}

def main():
    sys.stderr.write("ShadowCypher Intel MCP Server started\n")
    sys.stderr.flush()
    buf = ""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            buf += line
            try:
                req = json.loads(buf)
                buf = ""
            except json.JSONDecodeError:
                continue
            resp = handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
