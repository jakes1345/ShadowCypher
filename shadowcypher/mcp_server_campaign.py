#!/usr/bin/env python3
"""
SHADOWCYPHER CAMPAIGN MCP SERVER — Offensive engagement & campaign tracking

Tools exposed:
  shadowcypher_campaign_create        — create a new engagement campaign
  shadowcypher_campaign_list          — list all campaigns
  shadowcypher_campaign_get           — get full campaign details
  shadowcypher_campaign_update_status — update campaign status
  shadowcypher_campaign_add_target    — add a target to a campaign
  shadowcypher_campaign_add_finding   — record a finding (vuln / intel / cred)
  shadowcypher_campaign_report        — generate markdown engagement report
  shadowcypher_campaign_delete        — delete a campaign

Data: stored in ~/.shadowcypher/campaigns.json (no external DB needed)

Start:  python3 shadowcypher/mcp_server_campaign.py
Config: add 'shadow-cypher-campaign' to mcpServers in .claude/settings.json
"""

import sys, os, json, re, time, uuid, datetime

JSONRPC_VERSION     = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

CAMPAIGNS_FILE = os.path.expanduser("~/.shadowcypher/campaigns.json")

# ── MITRE ATT&CK (offline subset) ─────────────────────────────────────────────

_TECHNIQUES = {
    "T1595": ("Active Scanning", "Reconnaissance"),
    "T1590": ("Gather Victim Network Information", "Reconnaissance"),
    "T1591": ("Gather Victim Org Information", "Reconnaissance"),
    "T1592": ("Gather Victim Host Information", "Reconnaissance"),
    "T1593": ("Search Open Websites/Domains", "Reconnaissance"),
    "T1596": ("Search Open Technical Databases", "Reconnaissance"),
    "T1588": ("Obtain Capabilities", "Resource Development"),
    "T1190": ("Exploit Public-Facing Application", "Initial Access"),
    "T1566": ("Phishing", "Initial Access"),
    "T1078": ("Valid Accounts", "Initial Access"),
    "T1059": ("Command and Scripting Interpreter", "Execution"),
    "T1068": ("Exploitation for Privilege Escalation", "Privilege Escalation"),
    "T1027": ("Obfuscated Files or Information", "Defense Evasion"),
    "T1070": ("Indicator Removal", "Defense Evasion"),
    "T1090": ("Proxy", "Defense Evasion"),
    "T1539": ("Steal Web Session Cookie", "Credential Access"),
    "T1110": ("Brute Force", "Credential Access"),
    "T1040": ("Network Sniffing", "Credential Access"),
    "T1046": ("Network Service Discovery", "Discovery"),
    "T1082": ("System Information Discovery", "Discovery"),
    "T1135": ("Network Share Discovery", "Discovery"),
    "T1021": ("Remote Services", "Lateral Movement"),
    "T1119": ("Automated Collection", "Collection"),
    "T1048": ("Exfiltration Over Alternative Protocol", "Exfiltration"),
    "T1041": ("Exfiltration Over C2 Channel", "Exfiltration"),
}

_KEYWORD_MAP = {
    r"\bport.?scan|nmap\b": ["T1046", "T1595"],
    r"\bsubdomain|dns.enum": ["T1590"],
    r"\bwhois|osint\b": ["T1591", "T1596"],
    r"\bssl|cert\b": ["T1592"],
    r"\bssh\b": ["T1021"],
    r"\bsmb\b": ["T1135"],
    r"\bphish": ["T1566"],
    r"\bbrute.?forc": ["T1110"],
    r"\bsniff|pcap": ["T1040"],
    r"\bproxy|proxychains": ["T1090"],
    r"\bsql.?inject\b": ["T1190"],
    r"\bxss\b|cross.site": ["T1059"],
    r"\bprivilege.escal|privesc": ["T1068"],
    r"\bcookie|session.hijack": ["T1539"],
    r"\bexfiltr": ["T1048"],
    r"\bweb.recon|tech.detect": ["T1593"],
}

def _auto_tag(text: str) -> list[str]:
    ids: set[str] = set()
    lower = text.lower()
    for pattern, tids in _KEYWORD_MAP.items():
        if re.search(pattern, lower):
            ids.update(tids)
    for m in re.finditer(r"T\d{4}(?:\.\d{3})?", text.upper()):
        if m.group(0) in _TECHNIQUES:
            ids.add(m.group(0))
    return sorted(ids)

# ── Storage helpers ────────────────────────────────────────────────────────────

def _load() -> dict:
    os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
    if os.path.exists(CAMPAIGNS_FILE):
        try:
            with open(CAMPAIGNS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"campaigns": {}}

def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
    with open(CAMPAIGNS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"

def _short_id() -> str:
    return str(uuid.uuid4())[:8]

# ── Tools ─────────────────────────────────────────────────────────────────────

def tool_campaign_create(name: str, description: str = "", scope: str = "",
                          engagement_type: str = "pentest") -> dict:
    data = _load()
    cid = _short_id()
    campaign = {
        "id": cid,
        "name": name,
        "description": description,
        "scope": scope,
        "engagement_type": engagement_type,  # pentest | red-team | bug-bounty | osint
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
        "targets": [],
        "findings": [],
    }
    data["campaigns"][cid] = campaign
    _save(data)
    return {"ok": True, "campaign_id": cid, "campaign": campaign}

def tool_campaign_list() -> dict:
    data = _load()
    campaigns = []
    for cid, c in data["campaigns"].items():
        campaigns.append({
            "id": cid,
            "name": c["name"],
            "status": c["status"],
            "engagement_type": c.get("engagement_type", ""),
            "target_count": len(c.get("targets", [])),
            "finding_count": len(c.get("findings", [])),
            "created_at": c.get("created_at", ""),
        })
    campaigns.sort(key=lambda x: x["created_at"], reverse=True)
    return {"campaigns": campaigns, "total": len(campaigns)}

def tool_campaign_get(campaign_id: str) -> dict:
    data = _load()
    c = data["campaigns"].get(campaign_id)
    if not c:
        return {"error": f"Campaign not found: {campaign_id}"}
    # Add MITRE summary
    all_techs: set[str] = set()
    for f in c.get("findings", []):
        all_techs.update(f.get("mitre_tags", []))
    tactic_groups: dict[str, list] = {}
    for tid in sorted(all_techs):
        if tid in _TECHNIQUES:
            name, tactic = _TECHNIQUES[tid]
            tactic_groups.setdefault(tactic, []).append({"id": tid, "name": name})
    return {**c, "mitre_coverage": tactic_groups, "unique_technique_count": len(all_techs)}

def tool_campaign_update_status(campaign_id: str, status: str) -> dict:
    valid = {"active", "paused", "completed", "archived"}
    if status not in valid:
        return {"error": f"Invalid status. Use: {', '.join(sorted(valid))}"}
    data = _load()
    c = data["campaigns"].get(campaign_id)
    if not c:
        return {"error": f"Campaign not found: {campaign_id}"}
    c["status"] = status
    c["updated_at"] = _now()
    _save(data)
    return {"ok": True, "campaign_id": campaign_id, "status": status}

def tool_campaign_add_target(campaign_id: str, host: str, ip: str = "",
                              scope_notes: str = "") -> dict:
    data = _load()
    c = data["campaigns"].get(campaign_id)
    if not c:
        return {"error": f"Campaign not found: {campaign_id}"}
    target = {
        "id": _short_id(),
        "host": host,
        "ip": ip,
        "scope_notes": scope_notes,
        "added_at": _now(),
    }
    c["targets"].append(target)
    c["updated_at"] = _now()
    _save(data)
    return {"ok": True, "target_id": target["id"], "target": target}

def tool_campaign_add_finding(campaign_id: str, title: str, severity: str,
                               description: str, target: str = "",
                               cvss: float | None = None,
                               proof: str = "",
                               recommendation: str = "",
                               tags: list | None = None) -> dict:
    valid_sev = {"critical", "high", "medium", "low", "info"}
    severity = severity.lower()
    if severity not in valid_sev:
        return {"error": f"Invalid severity. Use: {', '.join(sorted(valid_sev))}"}
    data = _load()
    c = data["campaigns"].get(campaign_id)
    if not c:
        return {"error": f"Campaign not found: {campaign_id}"}

    # Auto-tag MITRE ATT&CK from title + description
    combined = f"{title} {description} {' '.join(tags or [])}"
    mitre_tags = _auto_tag(combined)

    finding = {
        "id": _short_id(),
        "title": title,
        "severity": severity,
        "description": description,
        "target": target,
        "cvss": cvss,
        "proof": proof,
        "recommendation": recommendation,
        "tags": tags or [],
        "mitre_tags": mitre_tags,
        "created_at": _now(),
    }
    c["findings"].append(finding)
    c["updated_at"] = _now()
    _save(data)
    return {"ok": True, "finding_id": finding["id"], "mitre_tags": mitre_tags, "finding": finding}

def tool_campaign_report(campaign_id: str) -> dict:
    data = _load()
    c = data["campaigns"].get(campaign_id)
    if not c:
        return {"error": f"Campaign not found: {campaign_id}"}

    findings = c.get("findings", [])
    targets = c.get("targets", [])

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
    sorted_findings = sorted(findings, key=lambda x: sev_order.get(x.get("severity", "info"), 5))

    # MITRE coverage
    all_techs: set[str] = set()
    for f in findings:
        all_techs.update(f.get("mitre_tags", []))
    tactic_groups: dict[str, list] = {}
    for tid in sorted(all_techs):
        if tid in _TECHNIQUES:
            name, tactic = _TECHNIQUES[tid]
            tactic_groups.setdefault(tactic, []).append(f"{tid}: {name}")

    lines = [
        f"# {c['name']} — Engagement Report",
        f"",
        f"**Type:** {c.get('engagement_type', 'pentest')}  ",
        f"**Status:** {c['status']}  ",
        f"**Created:** {c.get('created_at', '')}  ",
        f"**Generated:** {_now()}",
        f"",
        f"## Scope",
        c.get("scope") or "_Not defined_",
        f"",
        f"## Target Summary",
    ]
    if targets:
        for t in targets:
            lines.append(f"- `{t['host']}`" + (f" ({t['ip']})" if t.get("ip") else "")
                         + (f" — {t['scope_notes']}" if t.get("scope_notes") else ""))
    else:
        lines.append("_No targets recorded_")

    lines += [
        f"",
        f"## Finding Summary",
        f"",
        f"| Severity | Count |",
        f"|----------|-------|",
    ]
    for sev in ("critical", "high", "medium", "low", "info"):
        n = sev_counts.get(sev, 0)
        lines.append(f"| {sev.capitalize()} | {n} |")

    lines += ["", "## Findings", ""]
    for f in sorted_findings:
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡",
                     "low": "🟢", "info": "🔵"}.get(f["severity"], "⚪")
        lines.append(f"### {sev_emoji} [{f['severity'].upper()}] {f['title']}")
        if f.get("target"):
            lines.append(f"**Target:** `{f['target']}`  ")
        if f.get("cvss"):
            lines.append(f"**CVSS:** {f['cvss']}  ")
        if f.get("mitre_tags"):
            labels = []
            for tid in f["mitre_tags"]:
                name = _TECHNIQUES.get(tid, (tid,))[0]
                labels.append(f"`{tid}` {name}")
            lines.append(f"**ATT&CK:** {', '.join(labels)}  ")
        lines.append(f"")
        lines.append(f"**Description:** {f['description']}")
        if f.get("proof"):
            lines.append(f"")
            lines.append(f"**Proof:** {f['proof']}")
        if f.get("recommendation"):
            lines.append(f"")
            lines.append(f"**Recommendation:** {f['recommendation']}")
        lines.append(f"")

    lines += ["## MITRE ATT&CK Coverage", ""]
    if tactic_groups:
        for tactic, techs in sorted(tactic_groups.items()):
            lines.append(f"**{tactic}**")
            for t in techs:
                lines.append(f"  - {t}")
            lines.append("")
    else:
        lines.append("_No ATT&CK techniques tagged_")

    report_md = "\n".join(lines)
    return {
        "campaign_id": campaign_id,
        "report_markdown": report_md,
        "finding_count": len(findings),
        "severity_breakdown": sev_counts,
        "mitre_technique_count": len(all_techs),
        "mitre_coverage": tactic_groups,
    }

def tool_campaign_delete(campaign_id: str) -> dict:
    data = _load()
    if campaign_id not in data["campaigns"]:
        return {"error": f"Campaign not found: {campaign_id}"}
    name = data["campaigns"][campaign_id]["name"]
    del data["campaigns"][campaign_id]
    _save(data)
    return {"ok": True, "deleted": campaign_id, "name": name}

# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "shadowcypher_campaign_create": {
        "description": (
            "Create a new offensive engagement campaign. "
            "engagement_type: 'pentest' | 'red-team' | 'bug-bounty' | 'osint'"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Campaign name"},
                "description": {"type": "string", "default": ""},
                "scope": {"type": "string", "default": "",
                          "description": "In-scope targets / IP ranges / domains"},
                "engagement_type": {
                    "type": "string",
                    "enum": ["pentest", "red-team", "bug-bounty", "osint"],
                    "default": "pentest"
                }
            },
            "required": ["name"]
        },
        "handler": lambda p: tool_campaign_create(
            p["name"], p.get("description", ""), p.get("scope", ""),
            p.get("engagement_type", "pentest"))
    },
    "shadowcypher_campaign_list": {
        "description": "List all engagement campaigns with target/finding counts and status.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda p: tool_campaign_list()
    },
    "shadowcypher_campaign_get": {
        "description": "Get full campaign details including all targets, findings, and MITRE ATT&CK coverage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "8-char campaign ID from campaign_create"}
            },
            "required": ["campaign_id"]
        },
        "handler": lambda p: tool_campaign_get(p["campaign_id"])
    },
    "shadowcypher_campaign_update_status": {
        "description": "Update campaign status: 'active' | 'paused' | 'completed' | 'archived'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "paused", "completed", "archived"]}
            },
            "required": ["campaign_id", "status"]
        },
        "handler": lambda p: tool_campaign_update_status(p["campaign_id"], p["status"])
    },
    "shadowcypher_campaign_add_target": {
        "description": "Add a target host/IP to an engagement campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "host": {"type": "string", "description": "Hostname or IP"},
                "ip": {"type": "string", "default": ""},
                "scope_notes": {"type": "string", "default": ""}
            },
            "required": ["campaign_id", "host"]
        },
        "handler": lambda p: tool_campaign_add_target(
            p["campaign_id"], p["host"], p.get("ip", ""), p.get("scope_notes", ""))
    },
    "shadowcypher_campaign_add_finding": {
        "description": (
            "Record a vulnerability or finding in an engagement campaign. "
            "severity: critical | high | medium | low | info. "
            "MITRE ATT&CK tags are auto-detected from title + description. "
            "Pass existing tags list or explicit T#### IDs to augment auto-detection."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "title": {"type": "string", "description": "Short finding title"},
                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                "description": {"type": "string", "description": "Detailed finding description"},
                "target": {"type": "string", "default": "", "description": "Affected host/URL"},
                "cvss": {"type": "number", "description": "CVSS score 0.0-10.0 (optional)"},
                "proof": {"type": "string", "default": "", "description": "PoC / screenshot ref / payload"},
                "recommendation": {"type": "string", "default": "", "description": "Remediation advice"},
                "tags": {"type": "array", "items": {"type": "string"}, "default": [],
                         "description": "Tags or ATT&CK technique IDs (T1046, etc.)"}
            },
            "required": ["campaign_id", "title", "severity", "description"]
        },
        "handler": lambda p: tool_campaign_add_finding(
            p["campaign_id"], p["title"], p["severity"], p["description"],
            p.get("target", ""), p.get("cvss"), p.get("proof", ""),
            p.get("recommendation", ""), p.get("tags", []))
    },
    "shadowcypher_campaign_report": {
        "description": (
            "Generate a full Markdown engagement report for a campaign. "
            "Includes executive summary table, all findings sorted by severity, "
            "MITRE ATT&CK coverage breakdown by tactic, and recommendations."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"}
            },
            "required": ["campaign_id"]
        },
        "handler": lambda p: tool_campaign_report(p["campaign_id"])
    },
    "shadowcypher_campaign_delete": {
        "description": "Permanently delete a campaign and all its findings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"}
            },
            "required": ["campaign_id"]
        },
        "handler": lambda p: tool_campaign_delete(p["campaign_id"])
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
                "serverInfo": {"name": "shadow-cypher-campaign", "version": "1.0.0"}
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
    sys.stderr.write("ShadowCypher Campaign MCP Server started\n")
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
