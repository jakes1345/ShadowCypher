# Guardian Agent Auto-Update — Design Spec

**Goal:** Guardian agent checks for newer versions on startup and daily, downloads and self-replaces if one exists.

**Date:** 2026-05-08

---

## Architecture

A new unauthenticated API endpoint `GET /v1/agent/version` returns the current published agent version, download URL, and SHA256 checksum. The agent checks this endpoint on startup and every 24 hours while running. If a newer version is found it downloads the script, verifies SHA256, atomically replaces itself, and re-execs.

---

## API Endpoint

**Route:** `GET /v1/agent/version` — no auth required, public.

**Response:**
```json
{
  "version": "0.4.0",
  "download_url": "https://shadowcypher.site/agent/shadowcypher_agent.py",
  "sha256": "<64-char hex digest of the script file>"
}
```

Version and SHA256 are stored as Cloudflare Worker env vars (`AGENT_VERSION`, `AGENT_SHA256`) in `wrangler.toml` — bump them when shipping a new agent build. No database required.

---

## Agent Update Flow

```
startup / 24hr timer
  → GET /v1/agent/version (timeout 10s, fail silently)
  → parse version string, compare to AGENT_VERSION constant using semver
  → if remote_version <= local_version: do nothing
  → if remote_version > local_version:
      → GET download_url → write to temp file (same dir as __file__)
      → sha256(temp_file) == response.sha256 ?
          no  → delete temp file, log warning, continue running
          yes → os.replace(temp_file, __file__)
               → os.execv(sys.executable, [sys.executable] + sys.argv)
```

**Safety rules:**
- Any network error → log and continue, never crash
- SHA256 mismatch → delete temp file, log, continue
- Re-exec failure → log, continue (old version keeps running)
- Never update if running in a venv the user doesn't own (check `sys.executable`)

---

## Version Comparison

Simple tuple comparison on `"major.minor.patch"` strings — no external semver library needed:

```python
def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))

def _is_newer(remote: str, local: str) -> bool:
    return _version_tuple(remote) > _version_tuple(local)
```

---

## New / Modified Files

| File | Action | Purpose |
|---|---|---|
| `backend/api/src/agent_version.ts` | Create | `GET /v1/agent/version` handler |
| `backend/api/wrangler.toml` | Modify | Add `AGENT_VERSION` + `AGENT_SHA256` vars |
| `backend/api/src/index.ts` | Modify | Register `/v1/agent/version` route (no auth) |
| `agent/shadowcypher_agent.py` | Modify | Add `check_for_update()`, call on startup + in run loop |

---

## Out of Scope

- Rollback mechanism (future phase)
- Staged rollout / canary (future phase)
- Windows self-replace (current agent targets Linux/macOS)
- Notification to dashboard when agent updates itself
