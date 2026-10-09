#!/usr/bin/env python3
"""
SHADOWCYPHER OFFENSIVE MCP SERVER — Active recon, port scanning, vuln enumeration

Tools exposed:
  shadowcypher_port_scan      — TCP port scan (socket or nmap)
  shadowcypher_service_scan   — Full service/version/OS detection via nmap
  shadowcypher_vuln_scan      — nmap NSE vulnerability scripts
  shadowcypher_subdomain_enum — Subdomain enumeration (DNS brute + passive)
  shadowcypher_web_recon      — HTTP fingerprinting, redirect chains, WAF detect
  shadowcypher_dir_brute      — Web directory/path brute-force via gobuster/ffuf

Start:  python3 shadowcypher/mcp_server_offensive.py
Config: add 'shadow-cypher-offensive' to mcpServers in .claude/settings.json

NOTE: All tools are for authorized engagements only. Ensure written permission
      before scanning targets you do not own.
"""

import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.parse
import urllib.request

JSONRPC_VERSION     = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timed out", 1
    except Exception as e:
        return "", str(e), 1

def _require(tool: str) -> str | None:
    return shutil.which(tool)

# ── Port scan ─────────────────────────────────────────────────────────────────

_COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443,
                 445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443, 8888, 9090]

_PORT_NAMES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5900: "VNC",
    8080: "HTTP-alt", 8443: "HTTPS-alt", 8888: "Jupyter", 9090: "Prometheus",
}

def tool_port_scan(target: str, ports: str = "common", timeout_s: float = 1.0) -> dict:
    if ports == "common":
        port_list = _COMMON_PORTS
    elif ports == "top1000" and _require("nmap"):
        # delegate to nmap for speed
        out, err, rc = run(["nmap", "-sS", "--top-ports", "1000", "-n", "-T4",
                             "--open", "-oG", "-", target], timeout=120)
        if rc != 0:
            return {"target": target, "error": err or "nmap failed"}
        results = []
        for line in out.splitlines():
            m = re.findall(r"(\d+)/open", line)
            for p in m:
                port = int(p)
                results.append({"port": port, "state": "open",
                                 "service": _PORT_NAMES.get(port, "unknown")})
        return {"target": target, "method": "nmap-top1000", "open_ports": results,
                "count": len(results)}
    else:
        try:
            port_list = [int(p.strip()) for p in ports.split(",") if p.strip()]
        except ValueError:
            return {"error": f"Invalid port spec: {ports}"}

    results = []
    for port in port_list:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout_s)
            state = "open" if s.connect_ex((target, port)) == 0 else "closed"
            s.close()
        except Exception as e:
            state = f"error: {e}"
        if state == "open":
            results.append({"port": port, "state": state,
                            "service": _PORT_NAMES.get(port, "unknown")})
    return {"target": target, "method": "socket", "scanned": len(port_list),
            "open_ports": results, "count": len(results)}

# ── Service scan ──────────────────────────────────────────────────────────────

def tool_service_scan(target: str, ports: str = "") -> dict:
    nmap = _require("nmap")
    if not nmap:
        return {"error": "nmap not found. Install: sudo apt install nmap"}

    cmd = ["nmap", "-sV", "-O", "--version-intensity", "5", "-T4", "-n"]
    if ports:
        cmd += ["-p", ports]
    else:
        cmd += ["--top-ports", "100"]
    cmd.append(target)

    out, err, rc = run(cmd, timeout=180)
    if rc not in (0, 1):
        return {"target": target, "error": err or "nmap failed"}

    services = []
    os_guess = []
    for line in out.splitlines():
        # Port/service lines: "22/tcp   open  ssh     OpenSSH 8.2"
        m = re.match(r"(\d+)/(\w+)\s+(\w+)\s+(\S+)\s*(.*)", line)
        if m:
            services.append({
                "port": int(m.group(1)), "proto": m.group(2),
                "state": m.group(3), "service": m.group(4),
                "version": m.group(5).strip()
            })
        # OS detection: "OS details: Linux 5.4"
        om = re.match(r"OS details?: (.+)", line)
        if om:
            os_guess.append(om.group(1))
        agm = re.match(r"Aggressive OS guesses?: (.+)", line)
        if agm:
            os_guess.append(agm.group(1).split(",")[0].strip())

    return {
        "target": target, "services": services,
        "os_guess": os_guess[0] if os_guess else None,
        "raw": out[:2000]
    }

# ── Vuln scan ─────────────────────────────────────────────────────────────────

def tool_vuln_scan(target: str, ports: str = "") -> dict:
    nmap = _require("nmap")
    if not nmap:
        return {"error": "nmap not found. Install: sudo apt install nmap"}

    cmd = ["nmap", "-sV", "--script", "vuln,auth,default", "-T4", "-n"]
    if ports:
        cmd += ["-p", ports]
    cmd.append(target)

    out, err, rc = run(cmd, timeout=300)
    if rc not in (0, 1):
        return {"target": target, "error": err or "nmap failed"}

    findings = []
    current_port = None
    current_script = None
    script_lines: list[str] = []

    for line in out.splitlines():
        pm = re.match(r"(\d+)/(\w+)\s+\w+\s+\S+", line)
        if pm:
            if current_script and script_lines:
                findings.append({"port": current_port, "script": current_script,
                                  "output": "\n".join(script_lines).strip()})
            current_port = int(pm.group(1))
            current_script = None
            script_lines = []
            continue
        sm = re.match(r"\|_?\s*(\S+):\s*(.*)", line)
        if sm:
            sname = sm.group(1)
            if sname.startswith("_"):
                sname = sname[1:]
            if current_script and current_script != sname and script_lines:
                findings.append({"port": current_port, "script": current_script,
                                  "output": "\n".join(script_lines).strip()})
                script_lines = []
            current_script = sname
            rest = sm.group(2)
            if rest:
                script_lines.append(rest)
        elif current_script and line.startswith("|"):
            script_lines.append(line.lstrip("| "))

    if current_script and script_lines:
        findings.append({"port": current_port, "script": current_script,
                          "output": "\n".join(script_lines).strip()})

    vuln_findings = [f for f in findings if any(k in f.get("script", "").lower()
                     for k in ("vuln", "cve", "ms", "exploit"))]
    return {
        "target": target, "total_findings": len(findings),
        "vuln_findings": vuln_findings, "all_findings": findings[:50],
        "raw": out[:3000]
    }

# ── Subdomain enumeration ─────────────────────────────────────────────────────

_COMMON_SUBS = [
    "www", "mail", "remote", "blog", "webmail", "server", "ns1", "ns2",
    "smtp", "secure", "vpn", "m", "shop", "ftp", "api", "cdn", "dev",
    "staging", "test", "portal", "admin", "app", "cloud", "login",
    "gateway", "media", "static", "assets", "git", "gitlab", "jenkins",
    "jira", "confluence", "intranet", "support", "help", "docs",
]

def tool_subdomain_enum(domain: str, wordlist: str = "") -> dict:
    found = []

    # Try gobuster/ffuf/amass first if available
    if wordlist and _require("gobuster"):
        out, err, rc = run(
            ["gobuster", "dns", "-d", domain, "-w", wordlist, "-q", "--no-color"],
            timeout=120
        )
        if rc == 0:
            for line in out.splitlines():
                m = re.search(r"Found: (\S+)", line)
                if m:
                    found.append({"subdomain": m.group(1), "source": "gobuster"})
            return {"domain": domain, "found": found, "count": len(found)}

    if _require("amass"):
        out, err, rc = run(
            ["amass", "enum", "-passive", "-d", domain, "-timeout", "30"],
            timeout=90
        )
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if line.endswith(f".{domain}") or line == domain:
                    found.append({"subdomain": line, "source": "amass"})
            if found:
                return {"domain": domain, "found": found, "count": len(found)}

    # DNS brute-force fallback
    for sub in _COMMON_SUBS:
        fqdn = f"{sub}.{domain}"
        try:
            ips = socket.getaddrinfo(fqdn, None)
            if ips:
                found.append({"subdomain": fqdn, "ip": ips[0][4][0], "source": "dns-brute"})
        except socket.gaierror:
            pass

    # Certificate transparency via crt.sh
    try:
        url = f"https://crt.sh/?q=%25.{urllib.parse.quote(domain)}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "ShadowCypher/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:  # nosec B310
            data = json.loads(r.read())
        seen = set(f["subdomain"] for f in found)
        for entry in data[:200]:
            name = entry.get("name_value", "").strip().lstrip("*.")
            if name.endswith(f".{domain}") and name not in seen:
                seen.add(name)
                found.append({"subdomain": name, "source": "crt.sh"})
    except Exception:
        pass

    return {"domain": domain, "found": found, "count": len(found)}

# ── Web recon ─────────────────────────────────────────────────────────────────

def tool_web_recon(target: str) -> dict:
    url = target if target.startswith("http") else f"https://{target}"
    result: dict = {"target": target, "url": url}

    # Headers + redirect chain
    out, err, rc = run(
        ["curl", "-sIL", "--max-time", "15", "--max-redirs", "5", "-A",
         "Mozilla/5.0 (compatible; ShadowRecon/1.0)", url], timeout=20
    )
    if rc == 0 and out:
        result["headers_raw"] = out[:2000]
        server = re.search(r"^Server:\s*(.+)", out, re.MULTILINE | re.IGNORECASE)
        powered = re.search(r"^X-Powered-By:\s*(.+)", out, re.MULTILINE | re.IGNORECASE)
        location = re.findall(r"^Location:\s*(.+)", out, re.MULTILINE | re.IGNORECASE)
        result["server"] = server.group(1).strip() if server else None
        result["powered_by"] = powered.group(1).strip() if powered else None
        result["redirects"] = [loc.strip() for loc in location]

        # Security headers
        security_headers = [
            "Strict-Transport-Security", "Content-Security-Policy",
            "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy",
            "Permissions-Policy"
        ]
        present = []
        missing = []
        for h in security_headers:
            if re.search(rf"^{h}:", out, re.MULTILINE | re.IGNORECASE):
                present.append(h)
            else:
                missing.append(h)
        result["security_headers"] = {"present": present, "missing": missing}

    # WAF detection heuristics
    waf_indicators = {
        "Cloudflare": ["cf-ray", "cf-cache-status", "__cfduid"],
        "AWS WAF": ["x-amzn-requestid", "x-amz-cf-id"],
        "Akamai": ["akamai-grn", "x-check-cacheable"],
        "Incapsula": ["x-iinfo", "incap_ses"],
        "F5 BIG-IP": ["x-wa-info", "bigipserver"],
    }
    headers_lower = out.lower() if out else ""
    detected_waf = None
    for waf, indicators in waf_indicators.items():
        if any(ind in headers_lower for ind in indicators):
            detected_waf = waf
            break
    result["waf"] = detected_waf

    # Tech detect
    if shutil.which("whatweb"):
        tw, _, trc = run(["whatweb", "--no-errors", "-a", "1", url], timeout=20)
        if trc == 0:
            result["technologies"] = tw[:500]
    elif shutil.which("httpx"):
        tw, _, trc = run(["httpx", "-u", url, "-silent", "-tech-detect",
                           "-title", "-status-code", "-no-color"], timeout=20)
        if trc == 0:
            result["technologies"] = tw[:500]

    return result

# ── Directory brute ───────────────────────────────────────────────────────────

_COMMON_PATHS = [
    "admin", "administrator", "login", "wp-admin", "phpmyadmin", "api",
    "api/v1", "api/v2", "dashboard", "console", "manage", "management",
    "config", "backup", "uploads", "files", "static", "assets",
    "robots.txt", "sitemap.xml", ".env", ".git/config", "phpinfo.php",
    "server-status", "server-info", "web.config", "crossdomain.xml",
]

def tool_dir_brute(target: str, wordlist: str = "", extensions: str = "") -> dict:
    url = target if target.startswith("http") else f"https://{target}"
    found = []

    if wordlist and _require("gobuster"):
        cmd = ["gobuster", "dir", "-u", url, "-w", wordlist, "-q",
               "--no-color", "-t", "20", "--timeout", "5s"]
        if extensions:
            cmd += ["-x", extensions]
        out, err, rc = run(cmd, timeout=180)
        if rc == 0:
            for line in out.splitlines():
                m = re.match(r"(/\S+)\s+\(Status: (\d+)\)", line)
                if m:
                    found.append({"path": m.group(1), "status": int(m.group(2))})
        return {"target": url, "method": "gobuster", "found": found, "count": len(found)}

    if wordlist and _require("ffuf"):
        cmd = ["ffuf", "-u", f"{url}/FUZZ", "-w", wordlist, "-mc", "200,201,204,301,302,307,401,403",
               "-c", "-s", "-t", "20"]
        out, err, rc = run(cmd, timeout=180)
        if rc == 0:
            for line in out.splitlines():
                parts = line.split()
                if parts:
                    found.append({"path": "/" + parts[0], "status": None})
        return {"target": url, "method": "ffuf", "found": found, "count": len(found)}

    # Quick check of common paths
    for path in _COMMON_PATHS:
        check_url = f"{url}/{path}"
        try:
            req = urllib.request.Request(check_url, method="HEAD",
                                          headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:  # nosec B310
                found.append({"path": f"/{path}", "status": r.status})
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                found.append({"path": f"/{path}", "status": e.code})
        except Exception:
            pass

    return {"target": url, "method": "common-paths", "found": found, "count": len(found),
            "note": "Install gobuster for full wordlist scan: sudo apt install gobuster"}

# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = {
    "shadowcypher_port_scan": {
        "description": (
            "TCP port scan on a target. ports: 'common' (22 well-known ports, fast), "
            "'top1000' (requires nmap), or comma-separated list like '22,80,443,8080'. "
            "Returns only open ports with service names."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP address or hostname"},
                "ports": {"type": "string", "default": "common",
                          "description": "'common' | 'top1000' | '22,80,443,...'"},
                "timeout_s": {"type": "number", "default": 1.0,
                              "description": "Per-port connection timeout in seconds"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_port_scan(p["target"], p.get("ports", "common"),
                                             p.get("timeout_s", 1.0))
    },
    "shadowcypher_service_scan": {
        "description": (
            "Full service and version detection plus OS fingerprinting via nmap -sV -O. "
            "Requires nmap. Slower than port_scan but returns service versions and OS info."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP address or hostname"},
                "ports": {"type": "string", "default": "",
                          "description": "Optional port range, e.g. '1-1024' or '80,443,22'"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_service_scan(p["target"], p.get("ports", ""))
    },
    "shadowcypher_vuln_scan": {
        "description": (
            "Run nmap NSE vulnerability scripts (vuln, auth, default) against a target. "
            "Identifies CVEs, weak credentials, and common misconfigurations. Requires nmap. "
            "Takes 2-5 minutes. Use for authorized penetration testing only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP address or hostname"},
                "ports": {"type": "string", "default": "",
                          "description": "Optional port restriction, e.g. '80,443'"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_vuln_scan(p["target"], p.get("ports", ""))
    },
    "shadowcypher_subdomain_enum": {
        "description": (
            "Enumerate subdomains for a domain via DNS brute-force and certificate transparency (crt.sh). "
            "Pass a wordlist path for gobuster/amass if installed; falls back to built-in 40-word list + crt.sh."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Root domain to enumerate, e.g. 'example.com'"},
                "wordlist": {"type": "string", "default": "",
                             "description": "Optional path to subdomain wordlist for gobuster/amass"}
            },
            "required": ["domain"]
        },
        "handler": lambda p: tool_subdomain_enum(p["domain"], p.get("wordlist", ""))
    },
    "shadowcypher_web_recon": {
        "description": (
            "HTTP fingerprinting: follows redirect chains, grabs response headers, detects server/framework, "
            "checks security headers (HSTS, CSP, X-Frame-Options...), detects WAF (Cloudflare, Akamai, AWS, etc.), "
            "and runs whatweb/httpx for technology identification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string",
                           "description": "URL or hostname, e.g. 'example.com' or 'https://example.com'"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_web_recon(p["target"])
    },
    "shadowcypher_dir_brute": {
        "description": (
            "Web directory and file brute-force. Uses gobuster or ffuf if available with a provided wordlist. "
            "Falls back to a quick check of 25 common paths (admin, .env, .git/config, etc.). "
            "Returns paths with HTTP status codes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "URL or hostname"},
                "wordlist": {"type": "string", "default": "",
                             "description": "Path to wordlist file for gobuster/ffuf (optional)"},
                "extensions": {"type": "string", "default": "",
                               "description": "File extensions to append, e.g. 'php,html,txt'"}
            },
            "required": ["target"]
        },
        "handler": lambda p: tool_dir_brute(p["target"], p.get("wordlist", ""), p.get("extensions", ""))
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
                "serverInfo": {"name": "shadow-cypher-offensive", "version": "1.0.0"}
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
    sys.stderr.write("ShadowCypher Offensive MCP Server started\n")
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
