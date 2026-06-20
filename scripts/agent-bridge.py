#!/usr/bin/env python3
"""Shared coordination bus for Cursor + Claude Code (and humans) on ShadowCypher.

No live API between agents — both read/write `.agents/state.yaml` on disk.

Usage:
  agent-bridge status
  agent-bridge claim shadowos --task "QEMU login fix"
  agent-bridge release shadowos
  agent-bridge handoff claude-code "Layer7 import fixed; audit stealth stack next"
  agent-bridge note "May 29 ISO still needs rebuild"
  agent-bridge paths shadowcypher/modules/__init__.py shadowcypher/scripts/gauntlet_run.py
  agent-bridge check                    # exit 1 if another agent holds your area

Set identity once per session:
  export AGENT_BRIDGE_ID=cursor        # or claude-code, human
"""
from __future__ import annotations

import argparse
import fcntl
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO = Path(__file__).resolve().parents[1]
STATE_DIR = REPO / ".agents"
STATE_FILE = STATE_DIR / "state.yaml"
LOCK_FILE = STATE_DIR / "state.lock"
SCHEMA_VERSION = 1
STALE_SECONDS = 3 * 3600

AREAS = {
    "shadowos": "ISO profile, QEMU, sync-to-live, SDDM/Hyprland/Waybar",
    "shadowcypher-app": "GTK app, ui/, app.py, autostart/session",
    "shadowcypher-modules": "shadowcypher/modules/, scripts/, ai/, core/",
    "backend-go": "agent/, backend/, native/",
    "android-apk": "Shadow AI APK / mobile",
    "guardian-web": "Guardian app, website, fly server",
    "ai-engine": "ai_engine/, Ollama glue",
    "infra-release": "CI, packaging, version strings, release notes",
}

DEFAULT_STATE = {
    "schema_version": SCHEMA_VERSION,
    "updated_at": None,
    "updated_by": None,
    "agents": {},
    "claims": {},
    "handoff_log": [],
    "notes": [],
    "path_watch": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _agent_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("AGENT_BRIDGE_ID", "").strip()
    if env:
        return env
    if os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_TRACE_ID"):
        return "cursor"
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDE_SESSION"):
        return "claude-code"
    return f"human@{socket.gethostname()}"


def _load_yaml_raw() -> dict:
    if not STATE_FILE.exists():
        return dict(DEFAULT_STATE)
    text = STATE_FILE.read_text(encoding="utf-8")
    if not text.strip():
        return dict(DEFAULT_STATE)
    if yaml is None:
        sys.exit("PyYAML required: pip install pyyaml  (or pacman -S python-yaml)")
    data = yaml.safe_load(text) or {}
    for key, val in DEFAULT_STATE.items():
        data.setdefault(key, val if not isinstance(val, dict) else dict(val))
    return data


def _dump_yaml(data: dict) -> str:
    if yaml is None:
        sys.exit("PyYAML required: pip install pyyaml")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _with_lock(fn):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "a+", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            return fn()
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _save(data: dict, who: str) -> None:
    data["schema_version"] = SCHEMA_VERSION
    data["updated_at"] = _now()
    data["updated_by"] = who
    STATE_FILE.write_text(_dump_yaml(data), encoding="utf-8")


def _touch_agent(data: dict, who: str, focus: str | None = None) -> None:
    agents = data.setdefault("agents", {})
    entry = agents.get(who, {})
    entry["last_seen"] = _now()
    if focus:
        entry["focus"] = focus
    agents[who] = entry


def _parse_ts(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _claim_stale(claim: dict) -> bool:
    since = _parse_ts(claim.get("since"))
    if since is None:
        return True
    return (time.time() - since) > STALE_SECONDS


def cmd_status(_: argparse.Namespace) -> int:
    data = _load_yaml_raw()
    print("ShadowCypher agent bridge")
    print(f"  state: {STATE_FILE.relative_to(REPO)}")
    print(f"  updated: {data.get('updated_at')} by {data.get('updated_by')}")
    print()
    print("Areas:")
    claims = data.get("claims") or {}
    for area, desc in AREAS.items():
        c = claims.get(area)
        if not c or not c.get("owner"):
            print(f"  {area:22} — free — {desc}")
            continue
        stale = _claim_stale(c)
        flag = " (STALE)" if stale else ""
        print(
            f"  {area:22} — {c.get('owner')}{flag} — {c.get('task') or 'no task'}"
        )
    agents = data.get("agents") or {}
    if agents:
        print("\nAgents:")
        for name, info in sorted(agents.items()):
            print(f"  {name:16} seen {info.get('last_seen')}  focus: {info.get('focus', '—')}")
    notes = data.get("notes") or []
    if notes:
        print("\nRecent notes:")
        for n in notes[-5:]:
            print(f"  [{n.get('at')}] {n.get('by')}: {n.get('text')}")
    handoffs = data.get("handoff_log") or []
    if handoffs:
        print("\nRecent handoffs:")
        for h in handoffs[-5:]:
            print(f"  [{h.get('at')}] {h.get('from')} → {h.get('to')}: {h.get('message')}")
    paths = data.get("path_watch") or []
    if paths:
        print("\nWatched paths:")
        for p in paths[-10:]:
            print(f"  [{p.get('at')}] {p.get('by')}: {', '.join(p.get('paths', []))}")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)
    area = args.area

    def work():
        data = _load_yaml_raw()
        claims = data.setdefault("claims", {})
        cur = claims.get(area) or {}
        owner = cur.get("owner")
        if owner and owner != who and not _claim_stale(cur):
            print(f"BLOCKED: {area} held by {owner} since {cur.get('since')}", file=sys.stderr)
            print(f"  task: {cur.get('task')}", file=sys.stderr)
            return 1
        claims[area] = {
            "owner": who,
            "since": _now(),
            "task": args.task or "",
        }
        _touch_agent(data, who, args.task or f"claim:{area}")
        _save(data, who)
        print(f"claimed {area} as {who}")
        return 0

    return _with_lock(work)


def cmd_release(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)
    area = args.area

    def work():
        data = _load_yaml_raw()
        claims = data.setdefault("claims", {})
        cur = claims.get(area) or {}
        owner = cur.get("owner")
        if owner and owner != who and not args.force:
            print(f"refusing release: {area} owned by {owner} (use --force)", file=sys.stderr)
            return 1
        claims[area] = {"owner": None, "since": None, "task": None}
        _touch_agent(data, who)
        _save(data, who)
        print(f"released {area}")
        return 0

    return _with_lock(work)


def cmd_handoff(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)
    target = args.to

    def work():
        data = _load_yaml_raw()
        log = data.setdefault("handoff_log", [])
        log.append(
            {
                "at": _now(),
                "from": who,
                "to": target,
                "message": args.message,
            }
        )
        data["handoff_log"] = log[-50:]
        _touch_agent(data, who, f"handoff→{target}")
        agents = data.setdefault("agents", {})
        agents.setdefault(target, {})["focus"] = args.message
        agents[target]["last_seen"] = _now()
        _save(data, who)
        print(f"handoff → {target}: {args.message}")
        return 0

    return _with_lock(work)


def cmd_note(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)

    def work():
        data = _load_yaml_raw()
        notes = data.setdefault("notes", [])
        notes.append({"at": _now(), "by": who, "text": args.text})
        data["notes"] = notes[-100:]
        _touch_agent(data, who)
        _save(data, who)
        print("note saved")
        return 0

    return _with_lock(work)


def cmd_paths(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)
    paths = [str(Path(p).as_posix()) for p in args.paths]

    def work():
        data = _load_yaml_raw()
        watch = data.setdefault("path_watch", [])
        watch.append({"at": _now(), "by": who, "paths": paths})
        data["path_watch"] = watch[-100:]
        _touch_agent(data, who)
        _save(data, who)
        print(f"registered {len(paths)} path(s)")
        return 0

    return _with_lock(work)


def cmd_check(args: argparse.Namespace) -> int:
    who = _agent_id(args.as_agent)
    data = _load_yaml_raw()
    claims = data.get("claims") or {}
    blocked = []
    for area in args.areas or []:
        c = claims.get(area) or {}
        owner = c.get("owner")
        if owner and owner != who and not _claim_stale(c):
            blocked.append((area, owner, c.get("task")))
    if blocked:
        for area, owner, task in blocked:
            print(f"CONFLICT {area}: {owner} — {task}", file=sys.stderr)
        return 1
    return 0


def cmd_init(_: argparse.Namespace) -> int:
    def work():
        if STATE_FILE.exists():
            print(f"already exists: {STATE_FILE}")
            return 0
        _save(dict(DEFAULT_STATE), _agent_id(None))
        print(f"initialized {STATE_FILE}")
        return 0

    return _with_lock(work)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cursor ↔ Claude Code coordination bus")
    parser.add_argument("--as", dest="as_agent", help="agent id (cursor, claude-code, human)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="show claims, handoffs, notes")
    sub.add_parser("init", help="create empty state file")

    p_claim = sub.add_parser("claim", help="exclusive area lock")
    p_claim.add_argument("area", choices=sorted(AREAS))
    p_claim.add_argument("--task", default="", help="what you are doing")

    p_rel = sub.add_parser("release", help="release area lock")
    p_rel.add_argument("area", choices=sorted(AREAS))
    p_rel.add_argument("--force", action="store_true")

    p_hand = sub.add_parser("handoff", help="message for the other agent")
    p_hand.add_argument("to", help="cursor | claude-code | human | any id")
    p_hand.add_argument("message")

    p_note = sub.add_parser("note", help="append shared note")
    p_note.add_argument("text")

    p_paths = sub.add_parser("paths", help="register files you are editing")
    p_paths.add_argument("paths", nargs="+")

    p_check = sub.add_parser("check", help="exit 1 if areas conflict")
    p_check.add_argument("areas", nargs="*", choices=sorted(AREAS))

    args = parser.parse_args()
    cmds = {
        "status": cmd_status,
        "init": cmd_init,
        "claim": cmd_claim,
        "release": cmd_release,
        "handoff": cmd_handoff,
        "note": cmd_note,
        "paths": cmd_paths,
        "check": cmd_check,
    }
    return cmds[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
