# ShadowCypher Full System Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every broken system in ShadowCypher — desktop app crashes, missing binaries, config errors, and deployment gaps.

**Architecture:** Six independent fixes across the Python core (`shadowcypher/core/`), config (`config.json`), Go arsenal (`shadowcypher/arsenal/primitives/http_flood/`), and frontend (`index.html` + `www/index.html`). Each fix is self-contained and doesn't depend on the others.

**Tech Stack:** Python 3.12, Go 1.24+, JSON config, HTML/JS frontend, Cloudflare Workers (backend — some steps require manual Cloudflare/Wrangler action noted inline)

---

## Files Modified

| File | What changes |
|---|---|
| `shadowcypher/core/ghost.py:126` | Default cert dir `/etc/shadowcypher/ghost` → `~/.shadowcypher/ghost` |
| `shadowcypher/core/hub.py:199` | Fix double-nested `socket.socket(socket.socket(...))` bug |
| `config.json` | Set `irc.hub_secret` to a generated 32-byte hex token |
| `shadowcypher/arsenal/primitives/http_flood/main.go` | Already exists — compile to binary |
| `index.html` + `www/index.html` | Update `API_BASE` from `.workers.dev` to `api.shadowcypher.site` |

---

## Task 1: Fix Ghost Orchestrator SSL cert path

**Problem:** Ghost starts a TLS server and tries to write certs to `/etc/shadowcypher/ghost` — a root-owned directory. Crashes with `PermissionError` on every startup.

**Files:**
- Modify: `shadowcypher/core/ghost.py:126`

- [ ] **Step 1: Fix the cert dir default**

In `ghost.py` line 126, change:
```python
cert_dir = os.environ.get("SHADOWCYPHER_GHOST_CERT_DIR", "/etc/shadowcypher/ghost")
```
To:
```python
cert_dir = os.environ.get("SHADOWCYPHER_GHOST_CERT_DIR", os.path.expanduser("~/.shadowcypher/ghost"))
```

- [ ] **Step 2: Verify fix — import hub without PermissionError**

```bash
cd /home/jack/ShadowCypher
python3 -c "
import sys; sys.path.insert(0, '.')
from shadowcypher.core.ghost import ghost_orchestrator
print('Ghost import OK')
" 2>&1 | grep -E "PermissionError|Ghost import OK|GHOST_SSL"
```
Expected output: `Ghost import OK` with no `PermissionError`

- [ ] **Step 3: Commit**

```bash
git add shadowcypher/core/ghost.py
git commit -m "fix: ghost orchestrator cert dir — use ~/.shadowcypher/ghost not /etc"
```

---

## Task 2: Fix Training Range socket bug

**Problem:** `hub.py:199` has `socket.socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))` — passing a socket object as the argument to `socket.socket()` instead of the AF_INET constant. Crashes with `'socket' object cannot be interpreted as an integer`.

**Files:**
- Modify: `shadowcypher/core/hub.py:199`

- [ ] **Step 1: Fix the nested socket call**

In `hub.py` around line 199, change:
```python
with socket.socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
```
To:
```python
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
```

- [ ] **Step 2: Verify fix**

```bash
cd /home/jack/ShadowCypher
python3 -c "
import sys; sys.path.insert(0, '.')
from shadowcypher.core import hub
h = hub.ShadowHub.__new__(hub.ShadowHub)
h._start_training_range()
print('Training range check OK')
" 2>&1 | grep -E "TRAINING_RANGE|Training range check OK|socket"
```
Expected: `TRAINING_RANGE: Already active on port 5000.` or `Training range check OK` — no socket error.

- [ ] **Step 3: Commit**

```bash
git add shadowcypher/core/hub.py
git commit -m "fix: training range socket — remove double-nested socket.socket() call"
```

---

## Task 3: Generate and set Nexus hub_secret

**Problem:** `config.json` has `"hub_secret": ""` — Nexus relay refuses to start without a 32+ byte token. Logs `NEXUS_INIT_FAILURE` on every startup.

**Files:**
- Modify: `config.json`

- [ ] **Step 1: Generate a secure hub secret**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output — it's your hub secret (64 hex chars = 32 bytes).

- [ ] **Step 2: Set it in config.json**

Open `config.json`, find the `"irc"` section, and replace:
```json
"hub_secret": ""
```
With:
```json
"hub_secret": "<the token you just generated>"
```

- [ ] **Step 3: Verify Nexus starts without error**

```bash
cd /home/jack/ShadowCypher
python3 -c "
import sys, os; sys.path.insert(0, '.')
from shadowcypher.core.nexus import NexusRelay
n = NexusRelay()
print('Nexus init OK — secret accepted')
" 2>&1 | grep -E "Nexus init OK|HUB_SECRET_UNSET|NEXUS"
```
Expected: `Nexus init OK — secret accepted`

- [ ] **Step 4: Commit**

```bash
git add config.json
git commit -m "fix: set nexus hub_secret — was empty, nexus refused to start"
```

---

## Task 4: Compile missing http_flood binary

**Problem:** `shadowcypher/arsenal/primitives/http_flood/http_flood` binary is missing — only Go source exists. Arsenal module fails with `FATAL_ERROR: HTTP_Flood binary missing`.

**Files:**
- Compile: `shadowcypher/arsenal/primitives/http_flood/` → `http_flood` binary

- [ ] **Step 1: Compile the binary**

```bash
cd /home/jack/ShadowCypher/shadowcypher/arsenal/primitives/http_flood
go build -o http_flood main.go
chmod +x http_flood
```

- [ ] **Step 2: Verify binary exists and runs**

```bash
ls -la /home/jack/ShadowCypher/shadowcypher/arsenal/primitives/http_flood/http_flood
/home/jack/ShadowCypher/shadowcypher/arsenal/primitives/http_flood/http_flood --help 2>&1 | head -3 || echo "binary exists and runs"
```
Expected: File listed with `-rwxr-xr-x` permissions, binary executes without "file not found".

- [ ] **Step 3: Test arsenal import**

```bash
cd /home/jack/ShadowCypher
python3 -c "
import sys; sys.path.insert(0, '.')
from shadowcypher.modules.arsenal.base import arsenal_http_flood
result = arsenal_http_flood.__doc__
print('Arsenal import OK:', result[:50])
" 2>&1
```
Expected: `Arsenal import OK:` with docstring text.

- [ ] **Step 4: Commit**

```bash
git add shadowcypher/arsenal/primitives/http_flood/http_flood
git commit -m "build: compile http_flood Go binary — was missing, only source existed"
```

---

## Task 5: Update API_BASE to custom domain

**Problem:** `index.html` and `www/index.html` both hardcode `API_BASE = 'https://shadowcypher-api.shadowcypher.workers.dev'` with a TODO comment to switch to `api.shadowcypher.site`. The custom domain is better for reliability and branding.

**Prerequisite (manual step — do this first):**
- Log into Cloudflare Dashboard → Workers & Pages → `shadowcypher-api` → Settings → Triggers → Custom Domains → Add `api.shadowcypher.site`
- Wait for DNS to propagate (~1 min)
- Test: `curl -s https://api.shadowcypher.site/v1/health` should return `{"ok":true,...}`

**Files:**
- Modify: `index.html:912` and `www/index.html:912`

- [ ] **Step 1: Verify custom domain is live before editing**

```bash
curl -s https://api.shadowcypher.site/v1/health
```
Expected: `{"ok":true,...}` — only proceed if this returns 200.

- [ ] **Step 2: Update API_BASE in both files**

In `index.html` around line 912, change:
```javascript
const API_BASE = window.SHADOWCYPHER_API || 'https://shadowcypher-api.shadowcypher.workers.dev';
```
To:
```javascript
const API_BASE = window.SHADOWCYPHER_API || 'https://api.shadowcypher.site';
```

Apply the identical change to `www/index.html` (same line number — files are currently identical).

Also remove the TODO comment on the line above it:
```javascript
// TODO: bind api.shadowcypher.site in Cloudflare Workers → Triggers → Custom Domains, then switch to that
```

- [ ] **Step 3: Verify both files updated**

```bash
grep "API_BASE.*shadow" /home/jack/ShadowCypher/index.html /home/jack/ShadowCypher/www/index.html
```
Expected: Both lines show `api.shadowcypher.site`, no `.workers.dev`.

- [ ] **Step 4: Commit**

```bash
git add index.html www/index.html
git commit -m "fix: switch API_BASE to api.shadowcypher.site custom domain"
```

---

## Task 6: Android release APK

**Problem:** Only a debug APK exists (`android/app/build/outputs/apk/debug/app-debug.apk`). Debug builds can't be distributed via Play Store or sideloaded reliably on most devices.

**Prerequisite:** Android SDK + JDK 17 must be installed. Check with `java -version` and `ls ~/Android/Sdk` or `ANDROID_HOME`.

**Files:**
- `android/app/build.gradle` — needs release signing config
- `android/app/build/outputs/apk/release/app-release.apk` — output

- [ ] **Step 1: Check if keystore already exists**

```bash
find /home/jack/ShadowCypher/android -name "*.keystore" -o -name "*.jks" 2>/dev/null
```
If `shadowcypher.keystore` is found, note its path. If not, generate one:
```bash
keytool -genkey -v -keystore /home/jack/ShadowCypher/android/shadowcypher.keystore \
  -alias shadowcypher -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=ShadowCypher, OU=Security, O=ShadowCypher, L=US, S=US, C=US"
```
Set a strong password and remember it.

- [ ] **Step 2: Add signing config to android/app/build.gradle**

In `android/app/build.gradle`, inside the `android {}` block, add before `buildTypes`:
```groovy
signingConfigs {
    release {
        storeFile file("../shadowcypher.keystore")
        storePassword System.getenv("KEYSTORE_PASS") ?: "changeme"
        keyAlias "shadowcypher"
        keyPassword System.getenv("KEY_PASS") ?: "changeme"
    }
}
```
And update `buildTypes.release`:
```groovy
release {
    signingConfig signingConfigs.release
    minifyEnabled false
    proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
}
```

- [ ] **Step 3: Sync web assets into Android**

```bash
cd /home/jack/ShadowCypher
npx cap sync android
```

- [ ] **Step 4: Build release APK**

```bash
cd /home/jack/ShadowCypher/android
KEYSTORE_PASS="your_keystore_password" KEY_PASS="your_key_password" \
  ./gradlew assembleRelease
```

- [ ] **Step 5: Verify release APK**

```bash
ls -lh /home/jack/ShadowCypher/android/app/build/outputs/apk/release/
```
Expected: `app-release.apk` present, size > 5MB.

- [ ] **Step 6: Commit**

```bash
git add android/app/build.gradle
# Do NOT commit the keystore or passwords
git commit -m "build: add release signing config for Android APK"
```

---

## Task 7: Set Supabase service role key in Cloudflare Worker (manual)

**Problem:** The Cloudflare Worker backend has `SUPABASE_SERVICE_ROLE_KEY=PASTE_YOUR_ROTATED_SERVICE_ROLE_KEY_HERE` as a placeholder in `.dev.vars.example`. If this was never set via `wrangler secret put`, all authenticated API routes silently fail.

**This task is fully manual — no code changes.**

- [ ] **Step 1: Get the service role key from Supabase**

Go to: `https://supabase.com/dashboard/project/umruqwvyipylfslwwozj/settings/api`
Copy the **service_role** key (NOT the anon key).

- [ ] **Step 2: Set it as a Wrangler secret**

```bash
cd /home/jack/ShadowCypher/backend/api
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
# Paste the key when prompted
```

- [ ] **Step 3: Verify the worker works end-to-end**

Sign in on `shadowcypher.site`, then:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://shadowcypher-api.shadowcypher.workers.dev/v1/me
```
Expected: JSON with your user profile, not a 401 or 500.

---

## Self-Review

**Spec coverage:**
- ✅ Ghost PermissionError → Task 1
- ✅ Nexus HUB_SECRET_UNSET → Task 3
- ✅ Training range socket bug → Task 2
- ✅ http_flood binary missing → Task 4
- ✅ API_BASE .workers.dev URL → Task 5
- ✅ Android debug-only APK → Task 6
- ✅ Supabase service key → Task 7
- ✅ sisyphus import — `hub.py:19` imports `from shadowcypher.ai.sisyphus import sisyphus` which is correct. The failed import in the test was using the wrong path (`shadowcypher.core.sisyphus`). Hub itself is fine — no fix needed.

**Not in scope (require Cloudflare Dashboard access — manual):**
- Binding `api.shadowcypher.site` custom domain (prereq for Task 5)
- Setting `SUPABASE_SERVICE_ROLE_KEY` (Task 7)
