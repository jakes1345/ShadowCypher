"""
ShadowCypher IPC Daemon — JSON-RPC 2.0 server over Unix socket.

Bridges the Qt6 native UI to all Python backend modules.
Socket path: /tmp/shadowcypher-daemon.sock

Start:  python -m shadowcypher.core.daemon
        (or auto-started by the Qt6 app on launch)
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("shadow.daemon")

SOCKET_PATH = "/tmp/shadowcypher-daemon.sock"
MISSION_DIR  = Path("/opt/shadowcypher/shadowscript/missions")
_start_time  = time.time()

# ── Active mission state (one mission at a time for now) ──
_running_missions: dict[str, asyncio.Task] = {}


# ──────────────────────────────────────────────────────────────────────────────
# JSON-RPC helpers
# ──────────────────────────────────────────────────────────────────────────────

def ok(req_id: int, result: Any) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id}) + "\n").encode()


def err(req_id: int | None, message: str, code: int = -32600) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}) + "\n").encode()


# ──────────────────────────────────────────────────────────────────────────────
# Method handlers
# ──────────────────────────────────────────────────────────────────────────────

def _uptime_str() -> str:
    elapsed = int(time.time() - _start_time)
    h, rem = divmod(elapsed, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


async def handle_get_tactical_summary(_params: dict) -> dict:
    try:
        from shadowcypher.core.hub import hub
        summary = hub.get_tactical_summary()
        return {
            "active_missions": summary.get("active_missions", len(_running_missions)),
            "uptime": summary.get("uptime", _uptime_str()),
            "threat_hits": summary.get("threat_hits", 0),
            "integrity": True,
            "stealth_active": hub.is_stealth_ready() if hasattr(hub, "is_stealth_ready") else False,
            "relay_connected": (hasattr(hub, "relay_bridge") and hub.relay_bridge.connected),
        }
    except Exception as e:
        return {
            "active_missions": len(_running_missions),
            "uptime": _uptime_str(),
            "threat_hits": 0,
            "integrity": True,
            "stealth_active": False,
            "relay_connected": False,
            "_error": str(e),
        }


async def handle_get_devices(_params: dict) -> dict:
    try:
        from shadowcypher.core.hub import hub
        devices = hub.get_devices() if hasattr(hub, "get_devices") else []
        return {"devices": devices}
    except Exception as e:
        logger.debug("get_devices error: %s", e)
        return {"devices": [], "error": str(e)}


async def handle_get_incidents(_params: dict) -> dict:
    try:
        from shadowcypher.core.hub import hub
        incidents = hub.get_incidents() if hasattr(hub, "get_incidents") else []
        return {"incidents": incidents}
    except Exception as e:
        return {"incidents": [], "error": str(e)}


async def handle_trigger_scan(_params: dict) -> dict:
    try:
        from shadowcypher.core.hub import hub
        if hasattr(hub, "trigger_scan"):
            hub.trigger_scan()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def handle_counter_intel_full_scan(params: dict) -> dict:
    try:
        from shadowcypher.modules.counter_intel import CounterIntelEngine
        engine = CounterIntelEngine()
        interface = params.get("interface", "eth0")
        # Store scan state for polling
        engine._scan_results = {"checks": {}, "findings": [], "complete": False, "alert_count": 0, "max_severity": "none"}

        def _on_output(finding: dict):
            engine._scan_results["findings"].append(finding)
            sev = finding.get("severity", "info")
            engine._scan_results["alert_count"] = len([
                f for f in engine._scan_results["findings"] if f.get("severity") in ("critical", "warning")
            ])
            if sev == "critical" or engine._scan_results["max_severity"] != "critical":
                engine._scan_results["max_severity"] = sev
            check = finding.get("check", "unknown")
            engine._scan_results["checks"][check] = {
                "status": "alert" if sev in ("critical", "warning") else "clean",
                "detail": finding.get("message", "")[:40]
            }

        def _on_complete(results: dict):
            engine._scan_results["complete"] = True
            engine._scan_results.update(results)

        import threading
        threading.Thread(
            target=engine.run_full_scan,
            kwargs={"interface": interface, "on_output": _on_output, "on_complete": _on_complete},
            daemon=True
        ).start()

        # Store for polling
        handle_counter_intel_full_scan._active_engine = engine
        return {"started": True, "checks": engine._scan_results["checks"]}
    except Exception as e:
        return {"started": False, "error": str(e)}


async def handle_counter_intel_status(_params: dict) -> dict:
    engine = getattr(handle_counter_intel_full_scan, "_active_engine", None)
    if engine is None or not hasattr(engine, "_scan_results"):
        return {"checks": {}, "findings": [], "complete": False, "alert_count": 0, "max_severity": "none"}
    r = engine._scan_results
    return {
        "checks": r.get("checks", {}),
        "findings": r.get("findings", []),
        "complete": r.get("complete", False),
        "alert_count": r.get("alert_count", 0),
        "max_severity": r.get("max_severity", "none"),
    }


async def handle_get_ai_model(_params: dict) -> dict:
    try:
        from shadowcypher.ai.providers import provider_registry
        p = provider_registry.active
        if p and p.is_configured:
            return {"model": p.model, "provider": p.name}
        return {"model": "Ollama (local)", "provider": "ollama"}
    except Exception:
        return {"model": "Offline", "provider": "none"}


async def handle_ai_chat(params: dict) -> dict:
    message = params.get("message", "")
    if not message:
        return {"response": "", "error": "empty message"}
    try:
        from shadowcypher.ai.engine import AIEngine
        engine = AIEngine()
        response = await asyncio.to_thread(engine.chat, message)
        return {"response": response}
    except Exception as e:
        return {"response": "", "error": str(e)}


async def handle_list_missions(_params: dict) -> dict:
    missions = []
    dirs_to_check = [
        MISSION_DIR,
        Path.home() / ".local/share/shadowcypher/missions",
        Path(__file__).parents[3] / "shadowscript/missions",
    ]
    for d in dirs_to_check:
        if d.exists():
            for f in sorted(d.glob("*.shadow")):
                missions.append({"name": f.stem, "path": str(f)})
            break
    return {"missions": missions}


async def handle_run_mission(params: dict, writer: asyncio.StreamWriter, req_id: int) -> None:
    """Streaming handler — sends multiple partial results then a final complete."""
    name   = params.get("name", "unknown")
    source = params.get("source", "")

    if not source:
        # Try loading from disk
        for d in [MISSION_DIR, Path.home() / ".local/share/shadowcypher/missions",
                  Path(__file__).parents[3] / "shadowscript/missions"]:
            p = d / f"{name}.shadow"
            if p.exists():
                source = p.read_text()
                break

    if not source:
        writer.write(ok(req_id, {"output": f"Mission not found: {name}", "level": "ERROR", "complete": True}))
        return

    def _send_line(text: str, level: str = "INFO"):
        if not writer.is_closing():
            data = ok(req_id, {"output": text, "level": level, "complete": False})
            asyncio.get_event_loop().call_soon_threadsafe(writer.write, data)

    try:
        from shadowcypher.core.shadowscript import ShadowScriptEngine
        engine = ShadowScriptEngine(output_callback=_send_line)
        _running_missions[name] = asyncio.current_task()

        await asyncio.to_thread(engine.run, source)

        writer.write(ok(req_id, {"output": f"Mission '{name}' complete.", "level": "SUCCESS", "complete": True}))
    except Exception as e:
        writer.write(ok(req_id, {"output": f"Mission error: {e}", "level": "ERROR", "complete": True}))
    finally:
        _running_missions.pop(name, None)


async def handle_stop_mission(params: dict) -> dict:
    name = params.get("name", "")
    task = _running_missions.pop(name, None)
    if task:
        task.cancel()
        return {"ok": True, "stopped": name}
    return {"ok": False, "error": "not running"}


async def _run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


def _mail_credentials() -> tuple[str, str]:
    """Read API key and base URL from the local config file written by the Qt6 app."""
    import configparser
    cfg = configparser.ConfigParser()
    cfg_path = Path.home() / ".config" / "shadowcypher" / "config.ini"
    cfg.read(str(cfg_path))
    api_key  = cfg.get("api",  "key",      fallback="")
    base_url = cfg.get("api",  "base_url", fallback="https://api.shadowcypher.site")
    return api_key, base_url


async def handle_mail_inbox(_params: dict) -> dict:
    try:
        import json as _json
        import urllib.request
        api_key, base_url = _mail_credentials()
        if not api_key:
            return {"messages": [], "error": "API key not configured"}
        req = urllib.request.Request(
            f"{base_url}/v1/mail/inbox",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _json.loads(resp.read())
    except Exception as e:
        return {"messages": [], "error": str(e)}


async def handle_mail_send(params: dict) -> dict:
    try:
        import json as _json
        import urllib.request
        api_key, base_url = _mail_credentials()
        if not api_key:
            return {"ok": False, "error": "API key not configured"}
        body = _json.dumps({
            "to":      params.get("to", ""),
            "subject": params.get("subject", ""),
            "body":    params.get("body", ""),
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/v1/mail/send",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _run_cmd_output(cmd: list[str], timeout: int = 15) -> str:
    """Run a command and return combined stdout, capped at 8 KB."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode(errors="replace")[:8192]
        except asyncio.TimeoutError:
            proc.kill()
            return f"[TIMEOUT] {' '.join(cmd)}\n"
    except FileNotFoundError:
        return f"[NOT FOUND] {cmd[0]} — install it to use this check\n"
    except Exception as e:
        return f"[ERROR] {e}\n"


async def handle_osint_domain_scan(params: dict, writer: asyncio.StreamWriter, req_id: int) -> None:
    import shutil

    target  = params.get("target", "").strip()
    checks  = list(params.get("checks", []))

    from shadowcypher.core.sanitize import validate_target
    if not target or not validate_target(target):
        writer.write(ok(req_id, {"output": f"Invalid target: {target!r}", "level": "ERROR", "complete": True}))
        await writer.drain()
        return

    def _send(text: str, level: str = "INFO"):
        if writer.is_closing():
            return
        data = ok(req_id, {"output": text.rstrip(), "level": level, "complete": False})
        asyncio.get_event_loop().call_soon_threadsafe(writer.write, data)

    _send(f"[OSINT] Starting domain scan: {target} ({len(checks)} checks)")

    for check in checks:
        if check == "whois":
            _send(f"\n── WHOIS: {target} ──")
            out = await _run_cmd_output(["whois", target], timeout=20)
            _send(out)

        elif check == "dns":
            _send(f"\n── DNS Records: {target} ──")
            for rtype in ("A", "AAAA", "NS", "MX", "TXT", "CNAME"):
                out = await _run_cmd_output(["dig", target, rtype, "+short", "+time=5"], timeout=10)
                if out.strip():
                    _send(f"[{rtype}] {out.strip()}")

        elif check == "ssl":
            _send(f"\n── SSL Certificate: {target}:443 ──")
            out = await _run_cmd_output(
                ["sh", "-c", f"echo | openssl s_client -connect {target}:443 -showcerts 2>&1 | head -60"],
                timeout=15,
            )
            _send(out)

        elif check == "headers":
            _send(f"\n── HTTP Headers: {target} ──")
            url = target if target.startswith("http") else f"https://{target}"
            out = await _run_cmd_output(
                ["curl", "-Is", "--max-time", "10", "--connect-timeout", "8", url],
                timeout=15,
            )
            _send(out)

        elif check == "tech":
            _send(f"\n── Tech Fingerprint: {target} ──")
            url = target if target.startswith("http") else f"https://{target}"
            if shutil.which("whatweb"):
                out = await _run_cmd_output(["whatweb", url, "--no-errors"], timeout=20)
            elif shutil.which("httpx"):
                out = await _run_cmd_output(
                    ["httpx", "-u", url, "-silent", "-tech-detect", "-title", "-status-code", "-no-color"],
                    timeout=20,
                )
            else:
                out = "[TECH] Install whatweb or httpx (go install github.com/projectdiscovery/httpx/cmd/httpx@latest)\n"
            _send(out)

        elif check == "mx":
            _send(f"\n── MX / SPF Records: {target} ──")
            mx  = await _run_cmd_output(["dig", target, "MX", "+short", "+time=5"], timeout=10)
            txt = await _run_cmd_output(["dig", target, "TXT", "+short", "+time=5"], timeout=10)
            _send(f"[MX]\n{mx}\n[TXT/SPF]\n{txt}")

        elif check == "subnet":
            _send(f"\n── Subnet / ASN: {target} ──")
            out = await _run_cmd_output(["whois", "-h", "whois.radb.net", target], timeout=20)
            _send(out)

        elif check == "zone":
            _send(f"\n── Zone Transfer: {target} ──")
            ns_out = await _run_cmd_output(["dig", target, "NS", "+short", "+time=5"], timeout=10)
            nameservers = [line.strip().rstrip(".") for line in ns_out.strip().splitlines() if line.strip()]
            if not nameservers:
                _send("[ZONE] Could not resolve NS records.")
            else:
                for ns in nameservers[:3]:
                    _send(f"[ZONE] Trying axfr @{ns}…")
                    out = await _run_cmd_output(["dig", f"@{ns}", "axfr", target, "+time=8"], timeout=15)
                    _send(out)

        elif check == "wayback":
            _send(f"\n── Wayback Machine Recon: {target} ──")
            import json as _json
            import re as _re
            import urllib.request
            bare = _re.sub(r"^https?://", "", target).split("/")[0]
            url = (
                f"http://web.archive.org/cdx/search/cdx"
                f"?url=*.{bare}/*&output=json&collapse=urlkey&limit=1000&fl=original"
            )
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ShadowCypher-OSINT/2.0"})
                with urllib.request.urlopen(req, timeout=25) as resp:  # nosec B310
                    data = _json.loads(resp.read())
                if len(data) <= 1:
                    _send("[WAYBACK] No archived data found.")
                else:
                    subdomains: set = set()
                    endpoints: set = set()
                    for row in data[1:]:
                        m = _re.search(r"https?://([^/]+)((/[^?#]*)?)", row[0])
                        if m:
                            subdomains.add(m.group(1))
                            if m.group(2) and m.group(2) != "/":
                                endpoints.add(m.group(2).split("?")[0])
                    _send(f"[WAYBACK] {len(subdomains)} unique subdomains, {len(endpoints)} endpoints\n")
                    for s in sorted(subdomains)[:30]:
                        _send(f"  [+] {s}")
                    _send("")
                    for e in sorted(endpoints)[:30]:
                        _send(f"  [>] {e}")
            except Exception as exc:
                _send(f"[WAYBACK] Error: {exc}")

    writer.write(ok(req_id, {"output": "\n[OSINT] Scan complete.", "level": "SUCCESS", "complete": True}))
    await writer.drain()


async def handle_osint_identity_scan(params: dict, writer: asyncio.StreamWriter, req_id: int) -> None:
    import shutil

    query = params.get("query", "").strip()
    mode  = params.get("mode",  "breach")

    if not query:
        writer.write(ok(req_id, {"output": "query is required", "level": "ERROR", "complete": True}))
        await writer.drain()
        return

    def _send(text: str, level: str = "INFO"):
        if writer.is_closing():
            return
        data = ok(req_id, {"output": text.rstrip(), "level": level, "complete": False})
        asyncio.get_event_loop().call_soon_threadsafe(writer.write, data)

    _send(f"[OSINT] {mode.upper()} → {query}")

    if mode == "breach":
        import hashlib
        import urllib.request
        sha1   = hashlib.sha1(query.encode()).hexdigest().upper()  # nosec B324
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            req = urllib.request.Request(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "ShadowCypher-OSINT/2.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                body = resp.read().decode()
            found = next((ln for ln in body.splitlines() if ln.split(":")[0] == suffix), None)
            if found:
                count = found.split(":")[1]
                _send(f"[BREACH] ⚠  FOUND: '{query}' appears in {count} known data breach(es).", "ERROR")
            else:
                _send(f"[BREACH] ✓  CLEAN: '{query}' not found in known breach databases.", "SUCCESS")
        except Exception as e:
            _send(f"[BREACH] API error: {e}", "ERROR")

    elif mode == "social":
        from shadowcypher.core.config import config
        sherlock_root = os.path.join(str(config.project_root), "tools", "sherlock")
        if not os.path.isdir(sherlock_root):
            _send("[OSINT] Sherlock not staged — run: tools/install_osint.sh", "ERROR")
        else:
            python_bin = "python3"
            out = await _run_cmd_output(
                [python_bin, "-m", "sherlock_project", query, "--timeout", "10", "--no-color"],
                timeout=120,
            )
            _send(out)

    elif mode == "email":
        from shadowcypher.core.config import config
        holehe_path = os.path.join(str(config.project_root), "tools", "holehe")
        if not os.path.isdir(holehe_path):
            _send("[OSINT] Holehe not staged — run: tools/install_osint.sh", "ERROR")
        else:
            out = await _run_cmd_output(
                ["python3", os.path.join(holehe_path, "holehe", "core.py"), query],
                timeout=120,
            )
            _send(out)

    elif mode == "harvest":
        harvester = shutil.which("theHarvester")
        if not harvester:
            _send("[OSINT] theHarvester not found — pip install theHarvester", "ERROR")
        else:
            out = await _run_cmd_output(
                [harvester, "-d", query, "-b", "all", "-l", "200"],
                timeout=120,
            )
            _send(out)

    elif mode == "wayback":
        import json as _json
        import re
        import urllib.request
        bare = re.sub(r"^https?://", "", query).split("/")[0]
        url = (
            f"http://web.archive.org/cdx/search/cdx"
            f"?url=*.{bare}/*&output=json&collapse=urlkey&limit=1000&fl=original"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ShadowCypher-OSINT/2.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:  # nosec B310
                data = _json.loads(resp.read())
            if len(data) <= 1:
                _send("[WAYBACK] No archived data found.")
            else:
                subdomains: set = set()
                endpoints: set = set()
                for row in data[1:]:
                    m = re.search(r"https?://([^/]+)((/[^?#]*)?)", row[0])
                    if m:
                        subdomains.add(m.group(1))
                        if m.group(2) and m.group(2) != "/":
                            endpoints.add(m.group(2).split("?")[0])
                _send(f"[WAYBACK] {len(subdomains)} unique subdomains, {len(endpoints)} endpoints")
                for s in sorted(subdomains)[:50]:
                    _send(f"  [+] {s}")
                _send("")
                for e in sorted(endpoints)[:50]:
                    _send(f"  [>] {e}")
        except Exception as exc:
            _send(f"[WAYBACK] Error: {exc}", "ERROR")

    else:
        _send(f"[OSINT] Unknown mode: {mode}", "ERROR")

    writer.write(ok(req_id, {"output": "[OSINT] Done.", "level": "SUCCESS", "complete": True}))
    await writer.drain()


async def handle_cve_feed_recent(params: dict) -> dict:
    try:
        from shadowcypher.modules.cve_feed import cve_feed
        days = int(params.get("days", 7))
        raw_vulns = cve_feed.fetch_recent(days=days)
        kev = cve_feed.fetch_cisa_kev()
        normalized = []
        for vuln in raw_vulns:
            cve_obj = vuln.get("cve", {})
            if not cve_obj:
                continue
            nd = cve_feed._normalize_cve(cve_obj)
            normalized.append({
                "cve_id":          nd["id"],
                "severity":        nd["severity"],
                "score":           nd["score"],
                "description":     nd["desc"][:250],
                "published":       nd["published"],
                "references":      nd["refs"],
                "epss_score":      0.0,
                "epss_percentile": 0.0,
                "kev_exploited":   nd["id"] in kev,
                "kev_due_date":    kev.get(nd["id"], ""),
                "service":         "",
            })
        return {"cves": normalized, "count": len(normalized)}
    except Exception as e:
        logger.exception("cve_feed_recent error")
        return {"cves": [], "count": 0, "error": str(e)}


async def handle_cve_feed_search(params: dict) -> dict:
    try:
        from shadowcypher.modules.cve_feed import cve_feed
        keyword = params.get("keyword", "").strip()
        if not keyword:
            return {"cves": [], "count": 0, "error": "keyword required"}
        kev = cve_feed.fetch_cisa_kev()
        raw_cves = cve_feed.search(keyword)
        result = []
        for nd in raw_cves:
            result.append({
                "cve_id":          nd["id"],
                "severity":        nd["severity"],
                "score":           nd["score"],
                "description":     nd["desc"][:250],
                "published":       nd["published"],
                "references":      nd["refs"],
                "epss_score":      0.0,
                "epss_percentile": 0.0,
                "kev_exploited":   nd["id"] in kev,
                "kev_due_date":    kev.get(nd["id"], ""),
                "service":         "",
            })
        return {"cves": result, "count": len(result)}
    except Exception as e:
        logger.exception("cve_feed_search error")
        return {"cves": [], "count": 0, "error": str(e)}


async def handle_cve_feed_scan(params: dict, writer: asyncio.StreamWriter, req_id: int) -> None:
    target   = params.get("target", "").strip()
    services = params.get("services", [])

    if not target or not services:
        writer.write(ok(req_id, {"output": "target and services are required", "level": "ERROR", "complete": True}))
        await writer.drain()
        return

    def _send_line(text: str):
        if not writer.is_closing():
            data = ok(req_id, {"output": text.rstrip(), "level": "INFO", "complete": False})
            asyncio.get_event_loop().call_soon_threadsafe(writer.write, data)

    try:
        from shadowcypher.modules.cve_feed import cve_feed
        matches = await asyncio.to_thread(
            cve_feed.correlate_target,
            target, list(services), _send_line
        )
        cves = [m.to_dict() for m in matches]
        writer.write(ok(req_id, {
            "output":   f"Scan complete — {len(cves)} CVE(s) matched.",
            "level":    "SUCCESS",
            "complete": True,
            "cves":     cves,
            "count":    len(cves),
        }))
        await writer.drain()
    except Exception as e:
        writer.write(ok(req_id, {"output": f"Scan error: {e}", "level": "ERROR", "complete": True}))
        await writer.drain()


async def handle_ghost_mode_status(_params: dict) -> dict:
    tor_rc, tor_out, _ = await _run_cmd(["systemctl", "is-active", "tor"])
    tor_active = (tor_out.strip() == "active")

    ks_rc, ks_out, _ = await _run_cmd(
        ["sh", "-c", "iptables -L OUTPUT -n 2>/dev/null | grep -i drop"]
    )
    kill_switch = (ks_rc == 0 and bool(ks_out.strip()))

    try:
        gw_rc, gw_out, _ = await _run_cmd(
            ["sh", "-c", "ip route list default 2>/dev/null | awk '{print $5}' | head -1"]
        )
        iface = gw_out.strip() or "eth0"
        _, mac_out, _ = await _run_cmd(
            ["sh", "-c", f"ip -o link show {iface} 2>/dev/null | awk '{{print $17}}'"]
        )
        mac = mac_out.strip() or "unknown"
    except Exception:
        mac = "unknown"

    try:
        with open("/etc/resolv.conf") as f:
            content = f.read()
        dns_locked = any(ns in content for ns in ("127.", "::1", "127.0.0.1"))
    except Exception:
        dns_locked = False

    active = tor_active and kill_switch
    return {
        "tor": tor_active,
        "kill_switch": kill_switch,
        "mac": mac,
        "dns_locked": dns_locked,
        "active": active,
    }


async def handle_ghost_mode_enable(_params: dict) -> dict:
    try:
        cmds = [
            ["systemctl", "start", "tor"],
            ["sh", "-c", "iptables -I OUTPUT -m state --state NEW -o ! lo -j DROP 2>/dev/null || true"],
            ["sh", "-c", "iptables -I OUTPUT -m owner --uid-owner debian-tor -j ACCEPT 2>/dev/null || true"],
        ]
        for cmd in cmds:
            rc, _, stderr = await _run_cmd(cmd)
            if rc not in (0, 1) and stderr:
                logger.warning("ghost enable cmd error: %s", stderr.strip())
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def handle_ghost_mode_disable(_params: dict) -> dict:
    try:
        cmds = [
            ["systemctl", "stop", "tor"],
            ["sh", "-c", "iptables -F OUTPUT 2>/dev/null || true"],
        ]
        for cmd in cmds:
            await _run_cmd(cmd)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Method dispatch table
# ──────────────────────────────────────────────────────────────────────────────

METHODS = {
    "get_tactical_summary":      handle_get_tactical_summary,
    "get_devices":               handle_get_devices,
    "get_incidents":             handle_get_incidents,
    "trigger_scan":              handle_trigger_scan,
    "counter_intel_full_scan":   handle_counter_intel_full_scan,
    "counter_intel_status":      handle_counter_intel_status,
    "get_ai_model":              handle_get_ai_model,
    "ai_chat":                   handle_ai_chat,
    "list_missions":             handle_list_missions,
    "stop_mission":              handle_stop_mission,
    "ghost_mode_status":         handle_ghost_mode_status,
    "ghost_mode_enable":         handle_ghost_mode_enable,
    "ghost_mode_disable":        handle_ghost_mode_disable,
    "mail_inbox":                handle_mail_inbox,
    "mail_send":                 handle_mail_send,
    "cve_feed_recent":           handle_cve_feed_recent,
    "cve_feed_search":           handle_cve_feed_search,
}

STREAMING_METHODS = {"run_mission", "cve_feed_scan", "osint_domain_scan", "osint_identity_scan"}


# ──────────────────────────────────────────────────────────────────────────────
# Client handler
# ──────────────────────────────────────────────────────────────────────────────

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername", "unknown")
    logger.info("Qt6 client connected: %s", addr)
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req_id = None
            try:
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method", "")
                params = req.get("params") or {}

                if method in STREAMING_METHODS:
                    if method == "cve_feed_scan":
                        asyncio.create_task(handle_cve_feed_scan(params, writer, req_id))
                    elif method == "osint_domain_scan":
                        asyncio.create_task(handle_osint_domain_scan(params, writer, req_id))
                    elif method == "osint_identity_scan":
                        asyncio.create_task(handle_osint_identity_scan(params, writer, req_id))
                    else:
                        asyncio.create_task(handle_run_mission(params, writer, req_id))
                    continue

                handler = METHODS.get(method)
                if handler is None:
                    writer.write(err(req_id, f"method not found: {method}", -32601))
                    await writer.drain()
                    continue

                result = await handler(params)
                writer.write(ok(req_id, result))
                await writer.drain()

            except json.JSONDecodeError:
                writer.write(err(req_id, "parse error", -32700))
                await writer.drain()
            except Exception as e:
                logger.exception("handler error")
                writer.write(err(req_id, str(e)))
                await writer.drain()

    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        writer.close()
        logger.info("Qt6 client disconnected")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    logging.basicConfig(level=logging.INFO, format="[daemon] %(levelname)s %(message)s")

    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    server = await asyncio.start_unix_server(handle_client, SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)

    logger.info("ShadowCypher IPC daemon listening on %s", SOCKET_PATH)
    logger.info("Waiting for Qt6 app connection…")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daemon stopped.")
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
