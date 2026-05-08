# Guardian Agent Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guardian agent checks for newer versions on startup and every 24 hours, downloads and self-replaces atomically if one exists.

**Architecture:** A new unauthenticated `GET /v1/agent/version` endpoint returns the current version, download URL, and SHA256 from Cloudflare Worker env vars. The agent calls this on startup and in its run loop (daily), compares versions, and if newer: downloads to a temp file, verifies SHA256, atomically replaces itself, and re-execs. All failures are silent — never crash on a failed update.

**Tech Stack:** Python 3.8+ (stdlib only: `urllib.request`, `hashlib`, `os`, `sys`), TypeScript Cloudflare Worker.

---

## Files

| File | Action | Purpose |
|---|---|---|
| `backend/api/src/agent_version.ts` | Create | `GET /v1/agent/version` handler |
| `backend/api/wrangler.toml` | Modify | Add `AGENT_VERSION` + `AGENT_SHA256` vars |
| `backend/api/src/index.ts` | Modify | Register `/v1/agent/version` as unauthenticated route |
| `agent/shadowcypher_agent.py` | Modify | Add `check_for_update()`, call on startup + daily in run loop |

---

## Task 1: API endpoint — agent_version.ts

**Files:**
- Create: `backend/api/src/agent_version.ts`

- [ ] **Step 1: Create the handler file**

```typescript
/**
 * GET /v1/agent/version — unauthenticated, public.
 *
 * Returns the current published Guardian agent version, download URL,
 * and SHA256 checksum. Version + SHA256 come from wrangler vars so they
 * can be updated without code changes.
 */

import type { Env } from "./index";

export function getAgentVersion(env: Env, cors: HeadersInit): Response {
  return new Response(
    JSON.stringify({
      version: env.AGENT_VERSION || "0.3.0",
      download_url: "https://shadowcypher.site/agent/shadowcypher_agent.py",
      sha256: env.AGENT_SHA256 || "",
    }),
    { headers: { "Content-Type": "application/json", ...cors } }
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/jack/ShadowCypher/backend/api
node_modules/.bin/tsc --noEmit 2>&1
```
Expected: no output (clean).

- [ ] **Step 3: Commit**

```bash
cd /home/jack/ShadowCypher
git add backend/api/src/agent_version.ts
git commit -m "feat(agent): add GET /v1/agent/version handler"
```

---

## Task 2: Add AGENT_VERSION + AGENT_SHA256 to wrangler.toml

**Files:**
- Modify: `backend/api/wrangler.toml`

The current agent script SHA256 is `6590fee3f95e24a9a14a968feb598327eeb2daece83654fffe5e7cf974e13d4f`.

- [ ] **Step 1: Add vars to wrangler.toml**

In `backend/api/wrangler.toml`, inside the `[vars]` block, add after `RESEND_FROM_EMAIL`:

```toml
AGENT_VERSION = "0.3.0"
AGENT_SHA256 = "6590fee3f95e24a9a14a968feb598327eeb2daece83654fffe5e7cf974e13d4f"
```

- [ ] **Step 2: Verify the toml is valid**

```bash
cd /home/jack/ShadowCypher/backend/api
node_modules/.bin/wrangler deploy --dry-run 2>&1 | grep -E "error|Error|AGENT_VERSION" | head -5
```
Expected: `AGENT_VERSION` appears in binding list, no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/jack/ShadowCypher
git add backend/api/wrangler.toml
git commit -m "feat(agent): add AGENT_VERSION + AGENT_SHA256 to wrangler vars"
```

---

## Task 3: Wire route in index.ts

**Files:**
- Modify: `backend/api/src/index.ts`

- [ ] **Step 1: Add import**

In `backend/api/src/index.ts`, add with the other imports:

```typescript
import { getAgentVersion } from "./agent_version";
```

- [ ] **Step 2: Register unauthenticated route**

In `index.ts`, after the existing `/v1/health` block (around line 396):

```typescript
      if (path === "/v1/agent/version" && req.method === "GET") {
        return getAgentVersion(env, cors);
      }
```

- [ ] **Step 3: Add route to the comment header at the top of index.ts**

Find the comment block near line 20 that lists routes. Add:
```
 *   GET  /v1/agent/version     — current agent version + download URL (no auth)
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /home/jack/ShadowCypher/backend/api
node_modules/.bin/tsc --noEmit 2>&1
```
Expected: no output (clean).

- [ ] **Step 5: Deploy**

```bash
cd /home/jack/ShadowCypher/backend/api
node_modules/.bin/wrangler deploy 2>&1 | tail -5
```
Expected: `Deployed shadowcypher-api triggers` with no errors.

- [ ] **Step 6: Smoke test the live endpoint**

```bash
curl -s https://shadowcypher-api.shadowcypher.workers.dev/v1/agent/version
```
Expected:
```json
{"version":"0.3.0","download_url":"https://shadowcypher.site/agent/shadowcypher_agent.py","sha256":"6590fee3..."}
```

- [ ] **Step 7: Commit**

```bash
cd /home/jack/ShadowCypher
git add backend/api/src/index.ts
git commit -m "feat(agent): register /v1/agent/version route"
```

---

## Task 4: Add check_for_update() to the agent

**Files:**
- Modify: `agent/shadowcypher_agent.py`

The agent currently has `AGENT_VERSION = "0.3.0"` at line 48 and `DEFAULT_API = "https://shadowcypher-api.shadowcypher.workers.dev"` at line 50.

- [ ] **Step 1: Add stdlib imports at the top**

In `agent/shadowcypher_agent.py`, the imports block already has `import os`, `import sys`, `import time`. Add `hashlib` and `tempfile` to the existing imports:

```python
import hashlib
import tempfile
import urllib.request
```

These are all stdlib — no pip install needed.

- [ ] **Step 2: Add version helpers + check_for_update() after the AGENT_VERSION constant**

After line 48 (`AGENT_VERSION = "0.3.0"`), add:

```python
UPDATE_CHECK_INTERVAL = 86400  # 24 hours


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return (0,)


def check_for_update(api_base: str) -> None:
    """Download and self-replace if a newer agent version is available. Never raises."""
    try:
        url = f"{api_base}/v1/agent/version"
        with urllib.request.urlopen(url, timeout=10) as resp:
            import json as _json
            data = _json.loads(resp.read().decode())

        remote_ver = data.get("version", "")
        download_url = data.get("download_url", "")
        expected_sha256 = data.get("sha256", "")

        if not remote_ver or not download_url or not expected_sha256:
            return
        if _version_tuple(remote_ver) <= _version_tuple(AGENT_VERSION):
            return

        print(f"[*] update available: {AGENT_VERSION} → {remote_ver}")

        # Download to a temp file in the same directory as this script
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)

        fd, tmp_path = tempfile.mkstemp(dir=script_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                with urllib.request.urlopen(download_url, timeout=30) as resp:
                    f.write(resp.read())

            # Verify SHA256
            h = hashlib.sha256()
            with open(tmp_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_sha256:
                print("[!] update skipped: SHA256 mismatch", file=sys.stderr)
                os.unlink(tmp_path)
                return

            # Atomic replace + re-exec
            os.replace(tmp_path, script_path)
            print(f"[+] updated to {remote_ver} — restarting...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except Exception as e:
        print(f"[!] update check failed (continuing): {e}", file=sys.stderr)
```

- [ ] **Step 3: Call check_for_update() on startup in cmd_run()**

In the `cmd_run()` function, after loading config and before the auth sanity-check (around line 560), add:

```python
    check_for_update(cfg["api_base"])
```

The full block should look like:
```python
def cmd_run(cfg: dict) -> None:
    api = ApiClient(cfg["api_base"], cfg["api_key"])
    state = load_state()

    check_for_update(cfg["api_base"])   # ← add this line

    # Sanity-check key against /v1/me before starting the loop
    try:
        me = api.get("/v1/me")
```

- [ ] **Step 4: Add daily update check inside the run loop**

In `cmd_run()`, add a `last_update_check` tracker and call `check_for_update` every 24 hours. The run loop currently looks like:

```python
    last_scan = 0.0
    while True:
        try:
            now = time.time()
            agent_id = ensure_agent(api, state)
            api.post(f"/v1/agents/heartbeat?agent_id={agent_id}")
            if now - last_scan >= interval:
                cycle(cfg, api, state)
                last_scan = now
            time.sleep(hb_interval)
```

Replace with:

```python
    last_scan = 0.0
    last_update_check = time.time()  # already checked on startup
    while True:
        try:
            now = time.time()
            agent_id = ensure_agent(api, state)
            api.post(f"/v1/agents/heartbeat?agent_id={agent_id}")
            if now - last_scan >= interval:
                cycle(cfg, api, state)
                last_scan = now
            if now - last_update_check >= UPDATE_CHECK_INTERVAL:
                check_for_update(cfg["api_base"])
                last_update_check = now
            time.sleep(hb_interval)
```

- [ ] **Step 5: Verify the agent imports cleanly**

```bash
cd /home/jack/ShadowCypher
python3 -c "import ast; ast.parse(open('agent/shadowcypher_agent.py').read()); print('syntax OK')"
```
Expected: `syntax OK`

- [ ] **Step 6: Verify check_for_update handles a bad endpoint gracefully**

```bash
python3 -c "
import sys; sys.path.insert(0, 'agent')
# Monkey-patch urllib to simulate a network error
import urllib.request, shadowcypher_agent as a
orig = urllib.request.urlopen
urllib.request.urlopen = lambda *args, **kw: (_ for _ in ()).throw(OSError('connection refused'))
a.check_for_update('http://127.0.0.1:1')
urllib.request.urlopen = orig
print('graceful failure OK')
" 2>&1
```
Expected output ends with `graceful failure OK` and a `[!] update check failed` warning — no exception traceback.

- [ ] **Step 7: Commit**

```bash
git add agent/shadowcypher_agent.py
git commit -m "feat(agent): self-update on startup + daily — SHA256-verified atomic replace"
```

---

## Self-Review

**Spec coverage:**
- ✅ `GET /v1/agent/version` unauthenticated → Task 1 + Task 3
- ✅ Returns `version`, `download_url`, `sha256` → `agent_version.ts`
- ✅ Version + SHA256 from env vars → Task 2 wrangler.toml vars
- ✅ Check on startup → Task 4 Step 3
- ✅ Check every 24 hours while running → Task 4 Step 4 (`UPDATE_CHECK_INTERVAL = 86400`)
- ✅ Semver comparison → `_version_tuple()` helper
- ✅ Download to temp file → `tempfile.mkstemp` in same dir as script
- ✅ SHA256 verification → `hashlib.sha256` check before replace
- ✅ Atomic replace → `os.replace(tmp_path, script_path)`
- ✅ Re-exec → `os.execv(sys.executable, [sys.executable] + sys.argv)`
- ✅ Any failure is silent → outer `except Exception` catches all, logs warning
- ✅ Temp file cleanup on failure → `os.unlink(tmp_path)` in except block
