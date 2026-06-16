#!/usr/bin/env python3
"""
SHADOWCYPHER MCP SERVER — Model Context Protocol bridge
Exposes ShadowCypher tools to any MCP-compatible AI assistant
(Claude Code / free-code / shadow-cli / VS Code Copilot / etc.)

This server lets the AI assistant call ShadowCypher operations directly:
  - Network scanning and device discovery
  - Ghost mode (engage/disengage/status)
  - Anonymity auditing
  - Tor management
  - Trace erasing
  - Secure file shredding
  - Router/device auditing
  - Traffic analysis

Start:   python3 mcp_server.py
Config:  Add to ~/.claude/settings.json under mcpServers
"""

import sys
import os
import json
import subprocess
import socket
import re
import time
import shutil

# MCP protocol constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))  # nosec B602
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", 1
    except Exception as e:
        return str(e), 1


# ═══════════════════════════════════════════════════════════════
# Tool Implementations
# ═══════════════════════════════════════════════════════════════

def tool_network_scan():
    """Scan the local network for all devices."""
    subnet = None
    out, _ = run_cmd(["ip", "-o", "-4", "addr", "show"])
    for line in out.split("\n"):
        if "127.0.0.1" in line:
            continue
        m = re.search(r"inet (\d+\.\d+\.\d+)\.\d+/(\d+)", line)
        if m:
            subnet = f"{m.group(1)}.0/{m.group(2)}"
            break

    if not subnet:
        return {"error": "Cannot determine local subnet"}

    gateway_out, _ = run_cmd(["ip", "route", "show", "default"])
    gateway_match = re.search(r"default via (\S+)", gateway_out)
    gateway = gateway_match.group(1) if gateway_match else "unknown"

    devices = []
    if shutil.which("nmap"):
        out, rc = run_cmd(["nmap", "-sn", "-n", subnet], timeout=30)
        if rc == 0:
            current_ip = None
            for line in out.split("\n"):
                ip_m = re.search(r"Nmap scan report for (\S+)", line)
                mac_m = re.search(r"MAC Address: (\S+)\s+\((.+?)\)", line)
                if ip_m:
                    if current_ip:
                        devices.append({"ip": current_ip, "mac": "local", "vendor": ""})
                    current_ip = ip_m.group(1)
                if mac_m and current_ip:
                    devices.append({"ip": current_ip, "mac": mac_m.group(1), "vendor": mac_m.group(2)})
                    current_ip = None
            if current_ip:
                devices.append({"ip": current_ip, "mac": "local", "vendor": ""})

    # Quick port check on each device
    for dev in devices:
        open_ports = []
        for port in [22, 23, 80, 443, 445, 3389, 8080, 9050]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((dev["ip"], port)) == 0:
                    open_ports.append(port)
                s.close()
            except Exception:
                pass
        dev["open_ports"] = open_ports
        dev["is_gateway"] = dev["ip"] == gateway

    return {"subnet": subnet, "gateway": gateway, "device_count": len(devices), "devices": devices}


def tool_ghost_mode(action):
    """Control Ghost Mode (engage/disengage/status)."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "ghost_mode.py")
    if not os.path.exists(script):
        return {"error": f"ghost_mode.py not found at {script}"}

    out, rc = run_cmd(["python3", script, action], timeout=60)
    # Strip ANSI codes for clean output
    clean = re.sub(r"\033\[[0-9;]*m", "", out)
    return {"action": action, "output": clean, "success": rc == 0}


def tool_tor_status():
    """Check Tor anonymity status."""
    result = {"tor_running": False, "real_ip": None, "tor_ip": None, "anonymous": False}

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result["tor_running"] = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        pass

    out, rc = run_cmd(["curl", "-s", "--max-time", "5", "https://api.ipify.org"])
    if rc == 0:
        result["real_ip"] = out

    if result["tor_running"]:
        out, rc = run_cmd(["curl", "-s", "--max-time", "10", "--socks5-hostname",
                           "127.0.0.1:9050", "https://api.ipify.org"])
        if rc == 0:
            result["tor_ip"] = out
            result["anonymous"] = result["tor_ip"] != result["real_ip"]

    return result


def tool_anonymity_audit():
    """Run full anonymity chain audit."""
    checks = []

    # Tor
    tor_running = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        tor_running = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        pass
    checks.append({"test": "Tor SOCKS", "status": "PASS" if tor_running else "FAIL"})

    # DNS
    if os.path.exists("/etc/resolv.conf"):
        with open("/etc/resolv.conf") as f:
            content = f.read()
        nameservers = re.findall(r"nameserver\s+(\S+)", content)
        for ns in nameservers:
            if ns.startswith("127."):
                checks.append({"test": f"DNS {ns}", "status": "PASS", "detail": "local resolver"})
            else:
                checks.append({"test": f"DNS {ns}", "status": "WARN", "detail": "may leak queries"})

    # MAC
    out, _ = run_cmd(["ip", "-o", "link", "show"])
    for line in out.split("\n"):
        mac_match = re.search(r"(\w+): .+link/ether\s+([0-9a-f:]{17})", line)
        if mac_match and mac_match.group(1) != "lo":
            first_byte = int(mac_match.group(2).split(":")[0], 16)
            randomized = bool(first_byte & 0x02)
            checks.append({
                "test": f"MAC {mac_match.group(1)}",
                "status": "PASS" if randomized else "WARN",
                "detail": mac_match.group(2)
            })

    # Hostname
    hostname = socket.gethostname()
    checks.append({
        "test": "Hostname",
        "status": "PASS" if hostname in ("localhost", "localhost.localdomain") else "WARN",
        "detail": hostname
    })

    # Timezone
    tz = time.strftime("%Z")
    checks.append({
        "test": "Timezone",
        "status": "PASS" if tz in ("UTC", "GMT") else "WARN",
        "detail": tz
    })

    passed = sum(1 for c in checks if c["status"] == "PASS")
    total = len(checks)
    return {"score_pct": round(passed / total * 100, 1) if total else 0,
            "passed": passed, "total": total, "checks": checks}


def tool_trace_erase(deep=False):
    """Erase forensic traces."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "trace_eraser.py")
    if not os.path.exists(script):
        return {"error": "trace_eraser.py not found"}

    cmd = ["python3", script]
    if deep:
        cmd.append("--deep")
    out, rc = run_cmd(cmd, timeout=30)
    clean = re.sub(r"\033\[[0-9;]*m", "", out)
    return {"output": clean, "success": rc == 0}


def tool_port_scan(target, ports="22,80,443,8080,3389,445"):
    """Scan specific ports on a target."""
    results = []
    for port_str in ports.split(","):
        try:
            port = int(port_str.strip())
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            is_open = s.connect_ex((target, port)) == 0
            s.close()
            results.append({"port": port, "state": "open" if is_open else "closed"})
        except Exception as e:
            results.append({"port": port_str, "state": "error", "error": str(e)})

    return {"target": target, "results": results}


def tool_router_audit():
    """Audit the home router for security issues."""
    out, _ = run_cmd(["ip", "route", "show", "default"])
    m = re.search(r"default via (\S+)", out)
    if not m:
        return {"error": "Cannot detect gateway"}

    gateway = m.group(1)
    issues = []
    dangerous = {23: "Telnet", 7547: "TR-069", 1900: "UPnP", 21: "FTP"}

    for port, name in dangerous.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex((gateway, port)) == 0:
                issues.append({"port": port, "service": name, "severity": "HIGH"})
            s.close()
        except Exception:
            pass

    return {"gateway": gateway, "issues": issues,
            "risk": "HIGH" if issues else "LOW"}


def tool_secure_shred(target):
    """Securely delete a file (7-pass overwrite)."""
    if not os.path.exists(target):
        return {"error": f"File not found: {target}"}
    if shutil.which("shred"):
        out, rc = run_cmd(["shred", "-vzfun", "7", target], timeout=60)
        return {"target": target, "method": "shred", "success": rc == 0}
    else:
        return {"error": "shred utility not found"}


def tool_traffic_analyze():
    """Analyze current network traffic patterns."""
    out, _ = run_cmd(["ss", "-tnp"])
    connections = [ln for ln in out.split("\n")[1:] if ln.strip()]

    port_counts = {}
    for conn in connections:
        parts = conn.split()
        if len(parts) >= 5:
            port_match = re.search(r":(\d+)$", parts[4])
            if port_match:
                port = int(port_match.group(1))
                port_counts[port] = port_counts.get(port, 0) + 1

    port_names = {80:"HTTP", 443:"HTTPS", 9050:"Tor", 22:"SSH", 53:"DNS"}
    traffic = [{"port": p, "name": port_names.get(p, str(p)), "connections": c}
               for p, c in sorted(port_counts.items(), key=lambda x: -x[1])[:10]]

    return {"total_connections": len(connections), "top_destinations": traffic}


# ═══════════════════════════════════════════════════════════════
# MCP Protocol Handler
# ═══════════════════════════════════════════════════════════════

TOOLS = {
    "shadowcypher_network_scan": {
        "description": "Discover all devices on the local network. Returns IPs, MACs, vendors, and open ports for every device including phones, TVs, tablets, PCs, and IoT devices.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda params: tool_network_scan()
    },
    "shadowcypher_ghost_mode": {
        "description": "Control Ghost Mode for total operational invisibility. Actions: 'engage' (activate all anonymity layers), 'disengage' (restore normal), 'status' (check current state).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["engage", "disengage", "status", "workspace"],
                           "description": "Ghost mode action"}
            },
            "required": ["action"]
        },
        "handler": lambda params: tool_ghost_mode(params["action"])
    },
    "shadowcypher_tor_status": {
        "description": "Check Tor anonymity status: whether Tor is running, your real IP vs Tor exit IP, and whether you are anonymous.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda params: tool_tor_status()
    },
    "shadowcypher_anonymity_audit": {
        "description": "Run a comprehensive anonymity audit checking Tor, DNS leaks, MAC randomization, hostname exposure, and timezone leaks. Returns an anonymity score.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda params: tool_anonymity_audit()
    },
    "shadowcypher_trace_erase": {
        "description": "Erase forensic traces from the system: shell histories, system logs, temp files, and application traces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "deep": {"type": "boolean", "description": "If true, also clears journal, wtmp, lastlog, kernel ring buffer",
                          "default": False}
            }
        },
        "handler": lambda params: tool_trace_erase(params.get("deep", False))
    },
    "shadowcypher_port_scan": {
        "description": "Scan specific ports on a target IP address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target IP address"},
                "ports": {"type": "string", "description": "Comma-separated port list", "default": "22,80,443,8080"}
            },
            "required": ["target"]
        },
        "handler": lambda params: tool_port_scan(params["target"], params.get("ports", "22,80,443,8080"))
    },
    "shadowcypher_router_audit": {
        "description": "Audit the home router for security vulnerabilities: checks for exposed Telnet, TR-069, UPnP, and FTP.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda params: tool_router_audit()
    },
    "shadowcypher_secure_shred": {
        "description": "Securely delete a file using 7-pass overwrite. The file becomes unrecoverable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Path to file to securely delete"}
            },
            "required": ["target"]
        },
        "handler": lambda params: tool_secure_shred(params["target"])
    },
    "shadowcypher_traffic_analyze": {
        "description": "Analyze current network traffic patterns to identify what services you're connecting to.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda params: tool_traffic_analyze()
    },
}

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
                "serverInfo": {"name": "shadowcypher", "version": "1.0.0"}
            }
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    elif method == "tools/list":
        tools_list = []
        for name, tool in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        return {
            "jsonrpc": JSONRPC_VERSION, "id": req_id,
            "result": {"tools": tools_list}
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        if tool_name in TOOLS:
            try:
                result = TOOLS[tool_name]["handler"](tool_args)
                return {
                    "jsonrpc": JSONRPC_VERSION, "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": JSONRPC_VERSION, "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": JSONRPC_VERSION, "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }

    elif method == "ping":
        return {"jsonrpc": JSONRPC_VERSION, "id": req_id, "result": {}}

    else:
        return {
            "jsonrpc": JSONRPC_VERSION, "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


def main():
    """MCP stdio transport — reads JSON-RPC from stdin, writes to stdout."""
    sys.stderr.write("ShadowCypher MCP Server started\n")
    sys.stderr.flush()

    buffer = ""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            buffer += line

            # Try to parse complete JSON-RPC messages
            try:
                request = json.loads(buffer)
                buffer = ""
            except json.JSONDecodeError:
                continue

            response = handle_request(request)
            if response is not None:
                out = json.dumps(response)
                sys.stdout.write(out + "\n")
                sys.stdout.flush()

        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
