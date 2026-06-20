# Agent bridge (Cursor ↔ Claude Code)

Both AI tools edit the **same files on disk**. There is no live wire between them.
This folder is the shared bus so you do not double-fix, overwrite, or contradict each other.

## Before you edit

```bash
# From repo root — set who you are for this terminal session
export AGENT_BRIDGE_ID=cursor          # or claude-code

python3 scripts/agent-bridge.py status
python3 scripts/agent-bridge.py claim shadowos --task "QEMU + login fix"
python3 scripts/agent-bridge.py check shadowos   # fails if someone else holds it
```

## When you finish or switch tasks

```bash
python3 scripts/agent-bridge.py handoff claude-code "Login fix in profile; audit app tabs next"
python3 scripts/agent-bridge.py release shadowos
python3 scripts/agent-bridge.py note "May 29 ISO needs rebuild for baked login fix"
python3 scripts/agent-bridge.py paths shadowcypher/modules/__init__.py
```

## Areas (claim one at a time per agent)

| Area | Owns |
|------|------|
| `shadowos` | ISO profile, QEMU, sync-to-live, desktop stack |
| `shadowcypher-app` | GTK dashboard, `ui/`, `app.py` |
| `shadowcypher-modules` | `modules/`, `scripts/`, `ai/`, `core/` |
| `backend-go` | `agent/`, `backend/`, `native/` |
| `android-apk` | mobile / Shadow AI APK |
| `guardian-web` | Guardian, website, Fly deploy |
| `ai-engine` | `ai_engine/` |
| `infra-release` | CI, packaging, release notes |

Claims older than **3 hours** are treated as stale (another agent may take over).

## Files

- `state.yaml` — live coordination state (**gitignored** — local only)
- `state.example.yaml` — empty template

Both **Cursor** and **Claude Code** must read `AGENTS.md` (coordination section) every session.

## Agent Hub (local API)

Start once per boot session:

```bash
./scripts/agent-hubctl.sh start
```

- **URL:** http://127.0.0.1:8765  
- **Session hooks** inject `/v1/context` into Cursor + Claude Code automatically  
- **Queue task** for the other agent: `./scripts/agent-hubctl.sh task claude-code "…"`  
- **Dispatch now** (uses your logged-in CLIs): `./scripts/agent-hubctl.sh dispatch claude-code "…"`

Dispatch calls `claude -p` (Anthropic subscription) or `agent -p` (Cursor subscription) — not a merged third-party API key.

