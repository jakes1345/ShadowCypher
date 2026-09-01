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
import sys
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
}

STREAMING_METHODS = {"run_mission"}


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
