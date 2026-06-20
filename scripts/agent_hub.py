#!/usr/bin/env python3
"""Local Agent Hub — HTTP API connecting Cursor + Claude Code on ShadowCypher.

Uses your existing subscriptions via native CLIs when dispatching:
  - Claude Code: `claude -p` (Anthropic / Claude Pro)
  - Cursor:      `agent -p`  (Cursor subscription)

Coordination state lives in `.agents/state.yaml` (same as agent-bridge).

Start:
  python3 scripts/agent_hub.py
  # or: ./scripts/agent-hubctl.sh start

Default: http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    import yaml
except ImportError:
    yaml = None

REPO = Path(__file__).resolve().parents[1]
BRIDGE = REPO / "scripts" / "agent-bridge.py"
STATE_FILE = REPO / ".agents" / "state.yaml"
TASKS_FILE = REPO / ".agents" / "tasks.yaml"
DEFAULT_PORT = int(os.environ.get("AGENT_HUB_PORT", "8765"))
HOST = os.environ.get("AGENT_HUB_HOST", "127.0.0.1")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_bridge(*args: str, env: dict | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(BRIDGE), *args]
    e = os.environ.copy()
    if env:
        e.update(env)
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=e)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def _load_tasks() -> list[dict]:
    if not TASKS_FILE.exists() or yaml is None:
        return []
    data = yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8")) or {}
    return data.get("tasks") or []


def _save_tasks(tasks: list[dict]) -> None:
    if yaml is None:
        return
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(
        yaml.safe_dump({"tasks": tasks[-200:]}, sort_keys=False),
        encoding="utf-8",
    )


def _load_state() -> dict:
    if not STATE_FILE.exists() or yaml is None:
        return {}
    return yaml.safe_load(STATE_FILE.read_text(encoding="utf-8")) or {}


def _briefing() -> str:
    st = _load_state()
    lines = ["# Agent Hub briefing (Cursor ↔ Claude Code)", ""]
    claims = st.get("claims") or {}
    active = [(a, c) for a, c in claims.items() if c and c.get("owner")]
    if active:
        lines.append("## Active claims")
        for area, c in active:
            lines.append(f"- **{area}**: {c.get('owner')} — {c.get('task') or '—'}")
        lines.append("")
    for label, key in [("Handoffs", "handoff_log"), ("Notes", "notes")]:
        items = st.get(key) or []
        if items:
            lines.append(f"## Recent {label.lower()}")
            for item in items[-5:]:
                if key == "handoff_log":
                    lines.append(
                        f"- [{item.get('at')}] {item.get('from')} → {item.get('to')}: {item.get('message')}"
                    )
                else:
                    lines.append(f"- [{item.get('at')}] {item.get('by')}: {item.get('text')}")
            lines.append("")
    pending = [t for t in _load_tasks() if t.get("status") == "pending"]
    if pending:
        lines.append("## Pending tasks (for you)")
        for t in pending[-10:]:
            lines.append(
                f"- `{t.get('id')}` → **{t.get('target')}** from {t.get('from')}: {t.get('prompt', '')[:200]}"
            )
        lines.append("")
    lines.append(
        "Run `python3 scripts/agent-bridge.py status` or `curl localhost:8765/v1/context` anytime."
    )
    return "\n".join(lines)


def _dispatch_cli(target: str, prompt: str) -> dict[str, Any]:
    """Run native CLI using existing subscription login (not a merged API key)."""
    if target == "claude-code":
        cmd = [
            "claude",
            "-p",
            "--add-dir",
            str(REPO),
            prompt,
        ]
    elif target == "cursor":
        cmd = ["agent", "-p", prompt]
    else:
        return {"ok": False, "error": f"unknown target: {target}"}

    try:
        p = subprocess.run(
            cmd,
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=600,
            env=os.environ.copy(),
        )
        return {
            "ok": p.returncode == 0,
            "exit_code": p.returncode,
            "stdout": (p.stdout or "")[-8000:],
            "stderr": (p.stderr or "")[-4000:],
        }
    except FileNotFoundError:
        return {"ok": False, "error": f"CLI not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "dispatch timed out (600s)"}


class HubHandler(BaseHTTPRequestHandler):
    server_version = "AgentHub/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[agent-hub] {self.address_string()} - {fmt % args}\n")

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        if path in ("/", "/v1/health"):
            self._json(200, {"ok": True, "service": "agent-hub", "repo": str(REPO)})
            return

        if path == "/v1/context":
            self._json(
                200,
                {
                    "briefing": _briefing(),
                    "state": _load_state(),
                    "tasks_pending": len([t for t in _load_tasks() if t.get("status") == "pending"]),
                },
            )
            return

        if path == "/v1/status":
            code, out = _run_bridge("status")
            self._json(200 if code == 0 else 500, {"exit_code": code, "output": out})
            return

        if path == "/v1/tasks":
            status = qs.get("status", [None])[0]
            tasks = _load_tasks()
            if status:
                tasks = [t for t in tasks if t.get("status") == status]
            self._json(200, {"tasks": tasks})
            return

        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/v1/claim":
            agent = body.get("agent") or os.environ.get("AGENT_BRIDGE_ID", "human")
            area = body.get("area", "")
            task = body.get("task", "")
            code, out = _run_bridge("claim", area, "--task", task, "--as", agent)
            self._json(200 if code == 0 else 409, {"exit_code": code, "output": out})
            return

        if path == "/v1/release":
            agent = body.get("agent") or os.environ.get("AGENT_BRIDGE_ID", "human")
            area = body.get("area", "")
            args = ["release", area, "--as", agent]
            if body.get("force"):
                args.append("--force")
            code, out = _run_bridge(*args)
            self._json(200 if code == 0 else 400, {"exit_code": code, "output": out})
            return

        if path == "/v1/handoff":
            agent = body.get("from") or body.get("agent") or "human"
            target = body.get("to", "")
            msg = body.get("message", "")
            code, out = _run_bridge("handoff", target, msg, "--as", agent)
            self._json(200 if code == 0 else 400, {"exit_code": code, "output": out})
            return

        if path == "/v1/note":
            agent = body.get("agent") or "human"
            text = body.get("text", "")
            code, out = _run_bridge("note", text, "--as", agent)
            self._json(200 if code == 0 else 400, {"exit_code": code, "output": out})
            return

        if path == "/v1/task":
            tid = str(uuid.uuid4())[:8]
            task = {
                "id": tid,
                "status": "pending",
                "from": body.get("from", "human"),
                "target": body.get("target", "claude-code"),
                "area": body.get("area"),
                "prompt": body.get("prompt", ""),
                "created_at": _now(),
            }
            tasks = _load_tasks()
            tasks.append(task)
            _save_tasks(tasks)
            self._json(201, {"task": task})
            return

        if path == "/v1/dispatch":
            target = body.get("target", "claude-code")
            prompt = body.get("prompt", "")
            run_now = body.get("run", True)
            if not prompt:
                self._json(400, {"error": "prompt required"})
                return
            if not run_now:
                tid = str(uuid.uuid4())[:8]
                task = {
                    "id": tid,
                    "status": "pending",
                    "from": body.get("from", "human"),
                    "target": target,
                    "prompt": prompt,
                    "created_at": _now(),
                }
                tasks = _load_tasks()
                tasks.append(task)
                _save_tasks(tasks)
                self._json(202, {"queued": task})
                return
            result = _dispatch_cli(target, prompt)
            self._json(200 if result.get("ok") else 502, result)
            return

        self._json(404, {"error": "not found"})


def main() -> int:
    if yaml is None:
        print("Install PyYAML: pip install pyyaml  (or pacman -S python-yaml)", file=sys.stderr)
        return 1
    if not BRIDGE.exists():
        print(f"Missing {BRIDGE}", file=sys.stderr)
        return 1
    REPO.joinpath(".agents").mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        _run_bridge("init")

    server = ThreadingHTTPServer((HOST, DEFAULT_PORT), HubHandler)
    print(f"Agent Hub listening on http://{HOST}:{DEFAULT_PORT}")
    print(f"  context: curl -s http://{HOST}:{DEFAULT_PORT}/v1/context | jq -r .briefing")
    print(f"  repo:    {REPO}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())
