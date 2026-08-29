#!/usr/bin/env python3
"""
ShadowCypher Guardian Agent
============================

Small daemon that runs on a user's machine, scans their local network, and ships
results to the ShadowCypher API. Detects new devices, ARP spoofing, port changes,
and posts incidents the user sees on shadowcypher.site dashboard.

Install:
    pip install requests
    python3 shadowcypher_agent.py init     # writes ~/.shadowcypher/config.json
    python3 shadowcypher_agent.py run      # runs in foreground (or via systemd)

Config (~/.shadowcypher/config.json):
    {
      "api_base": "https://api.shadowcypher.site",
      "api_key": "sc_live_<your_key_from_dashboard>",
      "scan_interval_sec": 600,
      "heartbeat_interval_sec": 60
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("[!] missing dependency: pip install requests", file=sys.stderr)
    sys.exit(2)

CONFIG_DIR = Path.home() / ".shadowcypher"
CONFIG_PATH = CONFIG_DIR / "config.json"
STATE_PATH = CONFIG_DIR / "state.json"
DEFAULT_API = "https://api.shadowcypher.site"
AGENT_VERSION = "0.3.0"
UPDATE_CHECK_INTERVAL = 86400  # 24 hours
GITHUB_REPO = "jakes1345/ShadowCypher"
GITHUB_API = "https://api.github.com"


# ─── Auto-update ─────────────────────────────────────────────────────────────


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return (0,)


def check_for_update(force: bool = False) -> None:
    """Check GitHub releases for a newer agent version and self-replace if found.

    Agent releases use the tag prefix 'agent-v' (e.g. agent-v0.4.0) to
    distinguish them from app/Tauri releases. The release must include an
    asset named 'shadowcypher_agent.py'; a companion
    'shadowcypher_agent.py.sha256' asset is required for integrity checking.
    Never raises — update failures are logged and the daemon continues.
    """
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/releases"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"shadowcypher-agent/{AGENT_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            releases = json.loads(resp.read().decode())

        # Find the latest non-prerelease agent release
        agent_releases = [
            r for r in releases
            if r.get("tag_name", "").startswith("agent-v")
            and not r.get("prerelease", False)
            and not r.get("draft", False)
        ]
        if not agent_releases:
            return

        latest = agent_releases[0]  # GitHub returns newest-first
        tag = latest["tag_name"]   # e.g. "agent-v0.4.0"
        remote_ver = tag[len("agent-v"):]

        if not force and _version_tuple(remote_ver) <= _version_tuple(AGENT_VERSION):
            return

        print(f"[*] update available: {AGENT_VERSION} → {remote_ver}")

        assets = {a["name"]: a["browser_download_url"] for a in latest.get("assets", [])}
        download_url = assets.get("shadowcypher_agent.py")
        sha256_url = assets.get("shadowcypher_agent.py.sha256")

        if not download_url:
            print("[!] update skipped: release has no shadowcypher_agent.py asset", file=sys.stderr)
            return
        if not sha256_url:
            print("[!] update skipped: release has no .sha256 asset (refusing unverified download)", file=sys.stderr)
            return

        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)

        fd, tmp_path = tempfile.mkstemp(dir=script_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                with urllib.request.urlopen(download_url, timeout=60) as resp:
                    f.write(resp.read())

            with urllib.request.urlopen(sha256_url, timeout=10) as resp:
                expected_sha256 = resp.read().decode().strip().split()[0]

            h = hashlib.sha256()
            with open(tmp_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_sha256:
                print("[!] update skipped: SHA256 mismatch", file=sys.stderr)
                os.unlink(tmp_path)
                return

            os.chmod(tmp_path, os.stat(script_path).st_mode)
            os.replace(tmp_path, script_path)
            print(f"[+] updated to {remote_ver} — restarting...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except Exception as e:
        print(f"[!] update check failed (continuing): {e}", file=sys.stderr)


def cmd_update() -> None:
    """Manually check for and apply an agent update. Prints version info."""
    print(f"ShadowCypher Guardian Agent  v{AGENT_VERSION}")
    print(f"Checking GitHub for updates...")
    check_for_update(force=False)
    print("Already up to date.")


# ─── Config / state ─────────────────────────────────────────────────────────


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        sys.exit(f"[!] config not found at {CONFIG_PATH} — run: shadowcypher_agent.py init")
    with CONFIG_PATH.open() as f:
        cfg = json.load(f)
    if not cfg.get("api_key", "").startswith("sc_live_"):
        sys.exit("[!] api_key in config is missing or malformed")
    cfg.setdefault("api_base", DEFAULT_API)
    cfg.setdefault("scan_interval_sec", 600)
    cfg.setdefault("heartbeat_interval_sec", 60)
    return cfg


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        with STATE_PATH.open() as f:
            return json.load(f)
    return {}


def save_state(state: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w") as f:
        json.dump(state, f, indent=2)
    STATE_PATH.chmod(0o600)


def cmd_init() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        print(f"[*] config already exists at {CONFIG_PATH}")
    else:
        print("[*] paste your API key, or press Enter to use browser login")
        api_key = input("API key (sc_live_…): ").strip()
        if not api_key:
            return cmd_login()
        if not api_key.startswith("sc_live_"):
            sys.exit("[!] invalid key format")
        cfg = {
            "api_base": DEFAULT_API,
            "api_key": api_key,
            "scan_interval_sec": 600,
            "heartbeat_interval_sec": 60,
        }
        with CONFIG_PATH.open("w") as f:
            json.dump(cfg, f, indent=2)
        CONFIG_PATH.chmod(0o600)
        print(f"[+] wrote {CONFIG_PATH}")


def cmd_login() -> None:
    """Browser-based auth — no paste-key needed. RFC 8628 device flow."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    label = f"shadow-agent on {platform.node() or socket.gethostname()}"

    print("[*] requesting authorization code...")
    try:
        resp = requests.post(
            f"{DEFAULT_API}/v1/auth/device",
            json={"client_label": label},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        sys.exit(f"[!] failed to start device auth: {e}")

    user_code = data["user_code"]
    device_code = data["device_code"]
    verification_uri = data["verification_uri_complete"]
    interval = max(2, int(data.get("interval", 5)))
    expires_in = int(data.get("expires_in", 600))

    print()
    print("=" * 60)
    print(f"  Open this URL in your browser:")
    print(f"    {verification_uri}")
    print()
    print(f"  Or visit https://shadowcypher.site/device and enter:")
    print(f"    {user_code}")
    print("=" * 60)
    print()
    print(f"[*] waiting for authorization (expires in {expires_in}s)...")

    deadline = time.time() + expires_in
    while time.time() < deadline:
        try:
            poll = requests.post(
                f"{DEFAULT_API}/v1/auth/device/poll",
                json={"device_code": device_code},
                timeout=15,
            )
            body = poll.json() if poll.text else {}
        except requests.RequestException:
            time.sleep(interval)
            continue

        status = body.get("status")
        if status == "pending":
            time.sleep(interval)
            continue
        if status == "authorized":
            api_key = body["api_key"]
            cfg = {
                "api_base": DEFAULT_API,
                "api_key": api_key,
                "scan_interval_sec": 600,
                "heartbeat_interval_sec": 60,
            }
            with CONFIG_PATH.open("w") as f:
                json.dump(cfg, f, indent=2)
            CONFIG_PATH.chmod(0o600)
            print(f"[+] authorized as {body.get('email', '?')}")
            print(f"[+] wrote {CONFIG_PATH}")
            print(f"[*] now run: ./shadow-agent run")
            return
        if status == "denied":
            sys.exit("[!] authorization denied")
        if status in ("expired", "consumed"):
            sys.exit(f"[!] code {status} — try again")
        sys.exit(f"[!] unexpected status: {status}")

    sys.exit("[!] timed out waiting for authorization")


# ─── API client ─────────────────────────────────────────────────────────────


class ApiClient:
    def __init__(self, base: str, key: str) -> None:
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": f"shadowcypher-agent/{AGENT_VERSION}",
        })

    def post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self.session.post(f"{self.base}{path}", json=body or {}, timeout=15)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def get(self, path: str) -> dict[str, Any]:
        resp = self.session.get(f"{self.base}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json()


# ─── Scanners ───────────────────────────────────────────────────────────────


def scan_arp_table() -> list[dict[str, Any]]:
    """Read the OS ARP cache for known LAN devices. No raw sockets needed."""
    devices: list[dict[str, Any]] = []
    try:
        if platform.system() == "Linux":
            output = subprocess.check_output(["ip", "neigh"], text=True, timeout=10)
            # 192.168.1.1 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
            for line in output.splitlines():
                m = re.match(r"^(\S+)\s+dev\s+\S+\s+lladdr\s+([0-9a-f:]+)\s+(\S+)", line)
                if m and m.group(3) in ("REACHABLE", "STALE", "DELAY", "PROBE"):
                    devices.append({"ip": m.group(1), "mac": m.group(2)})
        else:
            output = subprocess.check_output(["arp", "-a"], text=True, timeout=10)
            for line in output.splitlines():
                m = re.search(r"\(([\d.]+)\) at ([0-9a-f:]+)", line, re.IGNORECASE)
                if m:
                    devices.append({"ip": m.group(1), "mac": m.group(2).lower()})
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"[!] arp scan failed: {e}", file=sys.stderr)
    return devices


def reverse_dns(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except (OSError, socket.herror):
        return None


def quick_port_scan(ip: str, ports: list[int], timeout: float = 0.4) -> list[int]:
    """Fast TCP connect scan against a small port set."""
    open_ports: list[int] = []
    for p in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                if s.connect_ex((ip, p)) == 0:
                    open_ports.append(p)
        except OSError:
            continue
    return open_ports


def fingerprint_device_type(open_ports: list[int], hostname: str | None) -> str:
    if 7547 in open_ports or 53 in open_ports or 80 in open_ports and 443 in open_ports:
        return "router"
    if 8009 in open_ports or 8008 in open_ports:
        return "tv"
    if 62078 in open_ports:
        return "phone"
    if hostname and re.search(r"iphone|ipad|android|pixel", hostname, re.I):
        return "phone"
    if hostname and re.search(r"echo|alexa|nest|hue", hostname, re.I):
        return "iot"
    if open_ports:
        return "pc"
    return "unknown"


def scan_network(deep: bool = True) -> list[dict[str, Any]]:
    """ARP cache + reverse DNS + light port probe + simple device-type heuristic."""
    common_ports = [22, 23, 53, 80, 443, 445, 8008, 8009, 8080, 7547, 62078]
    devices = scan_arp_table()
    for d in devices:
        ip = d.get("ip")
        if not ip:
            continue
        d["hostname"] = reverse_dns(ip)
        if deep:
            d["open_ports"] = quick_port_scan(ip, common_ports)
            d["device_type"] = fingerprint_device_type(d["open_ports"], d.get("hostname"))
    return devices


def audit_router(devices: list[dict[str, Any]]) -> dict[str, Any]:
    """Check the gateway router for dangerous exposed services."""
    dangerous = {21: "FTP", 23: "Telnet", 7547: "TR-069", 1900: "UPnP", 8080: "HTTP-alt", 8443: "HTTPS-alt"}
    findings: list[dict[str, Any]] = []
    gateway_ip: str | None = None

    # Try to find the default gateway
    try:
        out = subprocess.check_output(["ip", "route"], text=True, timeout=5)
        for line in out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                via_idx = parts.index("via") if "via" in parts else -1
                if via_idx >= 0 and via_idx + 1 < len(parts):
                    gateway_ip = parts[via_idx + 1]
                    break
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    if not gateway_ip:
        # Fall back to lowest-IP device tagged as router
        routers = [d for d in devices if d.get("device_type") == "router"]
        if routers:
            gateway_ip = routers[0].get("ip")

    if not gateway_ip:
        return {"gateway": None, "findings": []}

    open_ports = quick_port_scan(gateway_ip, list(dangerous.keys()), timeout=1.0)
    for p in open_ports:
        findings.append({"port": p, "service": dangerous[p], "severity": "critical" if p in (23, 7547) else "warning"})

    return {"gateway": gateway_ip, "open_ports": open_ports, "findings": findings}


def check_dns_leak() -> dict[str, Any]:
    """Detect if DNS queries resolve through unexpected resolvers."""
    trusted_resolvers = ["1.1.1.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "208.67.222.222", "208.67.220.220"]
    resolvers: list[str] = []

    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        resolvers.append(parts[1])
    except OSError:
        pass

    leaking = [r for r in resolvers if not (
        r.startswith("127.") or r.startswith("192.168.") or
        r.startswith("10.") or r.startswith("172.") or
        r in trusted_resolvers
    )]
    return {"resolvers": resolvers, "unexpected": leaking, "leak_detected": len(leaking) > 0}


def check_firewall() -> dict[str, Any]:
    """Check local firewall status (ufw or iptables)."""
    result: dict[str, Any] = {"active": False, "tool": None, "details": ""}

    # Try ufw first
    try:
        out = subprocess.check_output(["ufw", "status"], text=True, timeout=5, stderr=subprocess.DEVNULL)
        result["tool"] = "ufw"
        result["active"] = "Status: active" in out
        result["details"] = out.splitlines()[0] if out else ""
        return result
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fall back to iptables rule count
    try:
        out = subprocess.check_output(["iptables", "-L", "--line-numbers"], text=True, timeout=5, stderr=subprocess.DEVNULL)
        rules = [l for l in out.splitlines() if l and not l.startswith("Chain") and not l.startswith("num") and not l.startswith("target")]
        result["tool"] = "iptables"
        result["active"] = len(rules) > 0
        result["details"] = f"{len(rules)} rules"
        return result
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return result


def check_system_hardening() -> dict[str, Any]:
    """Check common local security hardening issues."""
    issues: list[dict[str, Any]] = []

    # SSH: PermitRootLogin
    try:
        out = subprocess.check_output(["sshd", "-T"], text=True, timeout=5, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if line.startswith("permitrootlogin") and "yes" in line.lower():
                issues.append({"check": "ssh_root_login", "severity": "critical", "detail": "SSH allows root login"})
            if line.startswith("passwordauthentication") and "yes" in line.lower():
                issues.append({"check": "ssh_password_auth", "severity": "warning", "detail": "SSH allows password auth (prefer keys)"})
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # World-writable passwd/shadow
    for path in ["/etc/passwd", "/etc/shadow"]:
        try:
            st = os.stat(path)
            if st.st_mode & 0o002:
                issues.append({"check": "world_writable", "severity": "critical", "detail": f"{path} is world-writable"})
        except OSError:
            pass

    # Core dumps enabled
    try:
        out = subprocess.check_output("ulimit -c", shell=True, text=True, timeout=3, stderr=subprocess.DEVNULL).strip()
        if out != "0":
            issues.append({"check": "core_dumps", "severity": "warning", "detail": f"Core dumps enabled (limit: {out})"})
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return {"issues": issues, "score": max(0, 100 - len(issues) * 20)}


def detect_arp_anomalies(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag duplicate MACs across multiple IPs, or duplicate IPs across MACs (classic ARP spoof)."""
    anomalies: list[dict[str, Any]] = []
    by_mac: dict[str, list[str]] = {}
    by_ip: dict[str, list[str]] = {}
    for d in devices:
        mac, ip = d.get("mac"), d.get("ip")
        if mac and ip:
            by_mac.setdefault(mac, []).append(ip)
            by_ip.setdefault(ip, []).append(mac)
    for mac, ips in by_mac.items():
        if len(set(ips)) > 1:
            anomalies.append({"kind": "duplicate_mac", "mac": mac, "ips": ips})
    for ip, macs in by_ip.items():
        if len(set(macs)) > 1:
            anomalies.append({"kind": "duplicate_ip", "ip": ip, "macs": macs})
    return anomalies


# ─── Commands ───────────────────────────────────────────────────────────────


def poll_missions(api: "ApiClient", agent_id: str) -> None:
    """Fetch pending ShadowScript missions from the API and execute them locally."""
    try:
        resp = api.get(f"/v1/agents/{agent_id}/missions/pending")
        missions = resp.get("missions", [])
    except Exception as e:
        print(f"[!] mission poll error: {e}", file=sys.stderr)
        return

    for mission in missions:
        mission_id = mission.get("id", "")
        script = mission.get("script_content", "").strip()
        if not script:
            continue

        print(f"[*] executing mission {mission_id}")
        output_lines: list[str] = []
        exit_code = 0

        try:
            import sys as _sys
            import io

            # Try to import ShadowInterpreter from the local ShadowCypher install
            try:
                from shadowcypher.compiler.interpreter import ShadowInterpreter
                old_stdout = _sys.stdout
                _sys.stdout = io.StringIO()
                try:
                    interp = ShadowInterpreter()
                    interp.run(script)
                    output_lines = _sys.stdout.getvalue().splitlines()
                finally:
                    _sys.stdout = old_stdout
            except ImportError:
                # ShadowCypher not installed locally — run script as shell commands (basic fallback)
                import subprocess
                result = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=120)
                output_lines = result.stdout.splitlines() + result.stderr.splitlines()
                exit_code = result.returncode

        except Exception as e:
            output_lines = [f"MISSION_ERROR: {e}"]
            exit_code = 1

        try:
            api.post(f"/v1/missions/{mission_id}/result", {
                "output": "\n".join(output_lines),
                "exit_code": exit_code,
            })
            print(f"[+] mission {mission_id} completed (exit={exit_code})")
        except Exception as e:
            print(f"[!] failed to post mission result {mission_id}: {e}", file=sys.stderr)


def ensure_agent(api: "ApiClient", state: dict[str, Any]) -> str:
    if state.get("agent_id"):
        return state["agent_id"]
    body = {
        "hostname": platform.node() or socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "agent_version": AGENT_VERSION,
    }
    resp = api.post("/v1/agents/register", body)
    state["agent_id"] = resp["agent_id"]
    save_state(state)
    print(f"[+] registered agent {state['agent_id']}")
    return state["agent_id"]


def cycle(cfg: dict[str, Any], api: ApiClient, state: dict[str, Any]) -> None:
    agent_id = ensure_agent(api, state)
    api.post(f"/v1/agents/heartbeat?agent_id={agent_id}")

    # ── Network scan ──────────────────────────────────────────────────────────
    t0 = time.time()
    devices = scan_network(deep=True)
    duration_ms = int((time.time() - t0) * 1000)
    scan_resp = api.post("/v1/scans", {
        "agent_id": agent_id,
        "scan_type": "network",
        "target": "lan",
        "duration_ms": duration_ms,
        "devices": devices,
        "result": {"raw_count": len(devices)},
    })
    print(f"[+] network scan {scan_resp.get('scan_id', '?')[:8]} · "
          f"{len(devices)} devices · {duration_ms}ms · "
          f"{scan_resp.get('new_device_incidents', 0)} new")

    # ── ARP anomaly detection ─────────────────────────────────────────────────
    for anomaly in detect_arp_anomalies(devices):
        api.post("/v1/incidents", {
            "agent_id": agent_id,
            "severity": "critical",
            "category": "arp_spoof",
            "title": f"Possible ARP anomaly: {anomaly['kind']}",
            "detail": json.dumps(anomaly),
            "data": anomaly,
        })
        print(f"[!] arp anomaly: {anomaly['kind']}")

    # ── Router audit ──────────────────────────────────────────────────────────
    router = audit_router(devices)
    if router["findings"]:
        api.post("/v1/scans", {
            "agent_id": agent_id,
            "scan_type": "router",
            "target": router.get("gateway", "gateway"),
            "result": router,
        })
        for f in router["findings"]:
            api.post("/v1/incidents", {
                "agent_id": agent_id,
                "severity": f["severity"],
                "category": "router_exposure",
                "title": f"Router exposes {f['service']} (port {f['port']})",
                "detail": f"Gateway {router.get('gateway')} has {f['service']} open",
                "data": f,
            })
            print(f"[!] router: {f['service']} exposed on port {f['port']}")
    else:
        print(f"[+] router audit: clean (gateway {router.get('gateway')})")

    # ── DNS leak check ────────────────────────────────────────────────────────
    dns = check_dns_leak()
    api.post("/v1/scans", {
        "agent_id": agent_id,
        "scan_type": "dns",
        "target": "resolvers",
        "result": dns,
    })
    if dns["leak_detected"]:
        api.post("/v1/incidents", {
            "agent_id": agent_id,
            "severity": "warning",
            "category": "dns_leak",
            "title": f"DNS leak detected — {len(dns['unexpected'])} unexpected resolver(s)",
            "detail": f"Unexpected: {', '.join(dns['unexpected'])}",
            "data": dns,
        })
        print(f"[!] dns leak: {dns['unexpected']}")
    else:
        print(f"[+] dns check: clean ({len(dns['resolvers'])} resolver(s))")

    # ── Firewall check ────────────────────────────────────────────────────────
    fw = check_firewall()
    api.post("/v1/scans", {
        "agent_id": agent_id,
        "scan_type": "firewall",
        "target": "local",
        "result": fw,
    })
    if not fw["active"]:
        api.post("/v1/incidents", {
            "agent_id": agent_id,
            "severity": "warning",
            "category": "firewall_disabled",
            "title": "No active firewall detected on this machine",
            "detail": f"Checked: ufw, iptables — neither appears active",
            "data": fw,
        })
        print("[!] firewall: not active")
    else:
        print(f"[+] firewall: active ({fw['tool']} — {fw['details']})")

    # ── System hardening check (runs every 6 cycles to avoid noise) ───────────
    cycle_count = state.get("cycle_count", 0) + 1
    state["cycle_count"] = cycle_count
    save_state(state)
    if cycle_count % 6 == 1:
        hardening = check_system_hardening()
        api.post("/v1/scans", {
            "agent_id": agent_id,
            "scan_type": "system",
            "target": "local",
            "result": hardening,
        })
        for issue in hardening["issues"]:
            api.post("/v1/incidents", {
                "agent_id": agent_id,
                "severity": issue["severity"],
                "category": "hardening",
                "title": issue["detail"],
                "detail": f"Check: {issue['check']}",
                "data": issue,
            })
        print(f"[+] system hardening: score {hardening['score']}/100 · {len(hardening['issues'])} issues")


def cmd_run(cfg: dict[str, Any]) -> None:
    api = ApiClient(cfg["api_base"], cfg["api_key"])
    state = load_state()

    check_for_update()

    # Sanity-check key against /v1/me before starting the loop
    try:
        me = api.get("/v1/me")
        print(f"[+] authenticated as {me['email']} (plan: {me['plan']})")
    except requests.HTTPError as e:
        sys.exit(f"[!] auth failed: {e.response.status_code} {e.response.text}")

    interval = max(60, int(cfg["scan_interval_sec"]))
    hb_interval = max(30, int(cfg["heartbeat_interval_sec"]))
    print(f"[*] running · scan every {interval}s · heartbeat every {hb_interval}s")

    last_scan = 0.0
    last_update_check = time.time()  # already checked on startup
    while True:
        try:
            now = time.time()
            agent_id = ensure_agent(api, state)
            api.post(f"/v1/agents/heartbeat?agent_id={agent_id}")
            poll_missions(api, agent_id)
            if now - last_scan >= interval:
                cycle(cfg, api, state)
                last_scan = now
            if now - last_update_check >= UPDATE_CHECK_INTERVAL:
                check_for_update()
                last_update_check = now
            time.sleep(hb_interval)
        except KeyboardInterrupt:
            print("\n[*] stopped")
            return
        except requests.RequestException as e:
            print(f"[!] network/api error: {e}", file=sys.stderr)
            time.sleep(15)
        except Exception as e:
            print(f"[!] unexpected: {e}", file=sys.stderr)
            time.sleep(30)


def cmd_once(cfg: dict[str, Any]) -> None:
    """Run a single scan cycle and exit (for cron / one-off invocation)."""
    api = ApiClient(cfg["api_base"], cfg["api_key"])
    state = load_state()
    cycle(cfg, api, state)


# ─── Systemd service management ──────────────────────────────────────────────

SERVICE_NAME = "shadowcypher-guardian"


def _service_file_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / f"{SERVICE_NAME}.service"


def _exec_start() -> str:
    """Return the best ExecStart string for this installation."""
    script_dir = Path(__file__).parent.resolve()
    wrapper = script_dir / "shadow-agent"
    if wrapper.exists() and os.access(wrapper, os.X_OK):
        return f"{wrapper} run"
    return f"{sys.executable} {Path(__file__).resolve()} run"


def cmd_install_service() -> None:
    """Install and enable a systemd user service so Guardian runs on boot."""
    if not CONFIG_PATH.exists():
        sys.exit("[!] run 'init' first to set your API key")

    if subprocess.run(["which", "systemctl"], capture_output=True).returncode != 0:
        sys.exit("[!] systemd not found — see README for manual setup")

    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = _service_file_path()

    service_file.write_text(f"""\
[Unit]
Description=ShadowCypher Guardian Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={_exec_start()}
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier={SERVICE_NAME}

[Install]
WantedBy=default.target
""")
    print(f"[+] service file → {service_file}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", SERVICE_NAME], check=True)

    # Enable linger so the user service survives logout / no active session
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    if user:
        subprocess.run(["loginctl", "enable-linger", user], check=False)
        print("[+] linger enabled — service persists after logout")

    print(f"\n[+] Guardian daemon is running\n")
    print(f"    Logs:     journalctl --user -u {SERVICE_NAME} -f")
    print(f"    Stop:     systemctl --user stop {SERVICE_NAME}")
    print(f"    Remove:   ./shadow-agent uninstall-service\n")


def cmd_uninstall_service() -> None:
    """Stop, disable and remove the Guardian systemd user service."""
    subprocess.run(["systemctl", "--user", "stop",    SERVICE_NAME], check=False)
    subprocess.run(["systemctl", "--user", "disable", SERVICE_NAME], check=False)
    sf = _service_file_path()
    if sf.exists():
        sf.unlink()
        print(f"[+] removed {sf}")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print("[+] Guardian daemon uninstalled")


def cmd_status() -> None:
    """Show Guardian daemon status and recent log lines."""
    r = subprocess.run(["systemctl", "--user", "status", SERVICE_NAME])
    if r.returncode not in (0, 3):  # 3 = inactive, which is fine to show
        print("\n[*] recent logs:")
        subprocess.run(["journalctl", "--user", "-u", SERVICE_NAME, "-n", "20", "--no-pager"])


# ─── main ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="ShadowCypher Guardian Agent")
    parser.add_argument("command", choices=[
        "init", "login", "run", "once", "update",
        "install-service", "uninstall-service", "status",
    ])
    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
        return
    if args.command == "login":
        cmd_login()
        return
    if args.command == "update":
        cmd_update()
        return
    if args.command == "install-service":
        cmd_install_service()
        return
    if args.command == "uninstall-service":
        cmd_uninstall_service()
        return
    if args.command == "status":
        cmd_status()
        return

    cfg = load_config()
    if args.command == "run":
        cmd_run(cfg)
    elif args.command == "once":
        cmd_once(cfg)


if __name__ == "__main__":
    main()
