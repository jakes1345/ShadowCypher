# ShadowCypher

Sovereign personal security platform: network monitoring, CVE threat feed, encrypted mail, chat and drive, and local AI. Self-hostable, no telemetry.

## Stack

| Layer | Tech |
|-------|------|
| Desktop app | **Qt6 C++** (`shadowcypher-qt/`): Widgets UI plus a C++ daemon, talking over local IPC |
| Web app | Single-page HTML/JS (`www/index.html`), no build step |
| API | Cloudflare Worker (`backend/api/src/index.ts`), TypeScript, Wrangler 4 |
| Auth + DB | Supabase (PostgreSQL, Auth) |
| Backup DB | Neon (PostgreSQL), mirrors Supabase via webhook |
| Email | Cloudflare Email Routing → Worker → Supabase; outbound via Resend |
| Real-time chat | Cloudflare Durable Objects (`ChatRoom` in `chat_do.ts`) |
| File storage | Cloudflare R2 (`SHADOW_FILES` binding) |
| OTA updates | Cloudflare KV (`SHADOW_OTA` binding) |
| ShadowOS | Arch Linux ISO (`shadowos/`), built with archiso |

## Platform decisions (non-negotiable)

- **The desktop app is Qt6 C++, in `shadowcypher-qt/` only.** New desktop features go there.
- **No Python and no GTK.** Don't add Python or GTK code, dependencies, CI jobs or packages. The project moved off Python + GTK3.
- Leftovers from before the switch are being removed: `shadowcypher/`, `tests/`, `agent/`, `shadowscript/` Python code, root Python files, and the Python app bundled into the ShadowOS ISO. Don't build on them or fix them. If a change needs one of them, port the piece into `shadowcypher-qt/` instead.

## Key directories

```
shadowcypher-qt/
  src/                  # Qt Widgets UI: MainWindow, pages/, api/ApiClient, ipc/IpcClient
  daemon/               # C++ background daemon (scans, incidents, CVE feed, ghost mode, AI)
  core/                 # shared runtime, with tests in core/tests
  privacy-helper/       # root helper for Ghost mode's kill-switch, run through pkexec
www/index.html          # entire web frontend (auth, chat, mail, dashboard, drive)
www/js/identity.js      # client-side key derivation and OpenPGP identity keys
backend/api/src/
  index.ts              # Worker entrypoint: routes, auth middleware
  identity.ts           # identity keys and KDF parameters (zero-access encryption)
  chat_do.ts            # Durable Object for WebSocket chat rooms
  supabase.ts           # Supabase REST helpers, findAuthUserByEmail
  neon.ts               # Neon helpers (mirror of Supabase)
  mail.ts               # Shadow Mail (inbound/outbound)
backend/api/migrations/ # SQL migrations, applied to Supabase in order
shadowos/               # Arch Linux ISO profile
android/                # Capacitor app; ships its own copy of the site in app/src/main/assets/public
```

## Auth model

- Users sign up with a handle; their internal email is `handle@shadowcypher.site`.
- The web app signs up and signs in directly against Supabase Auth. API calls use an API key (`sc_live_` + 48 hex chars) in `Authorization: Bearer`.
- The desktop app signs in through the browser: `POST /v1/auth/device`, the user approves at `shadowcypher.site/device`, then the app polls `POST /v1/auth/device/poll`. Pasting an API key also works. There is no `/v1/auth/login` route.
- **Split password (zero-access encryption):** for accounts whose `GET /v1/auth/kdf` returns `v: 1`, the client stretches the password with Argon2id and sends only the derived login secret to Supabase. The other half unlocks the user's OpenPGP key, which never leaves the device. Accounts on `v: 0` still use the plain password, and existing accounts are not upgraded at sign-in, because the Android app's bundled site still sends the plain password.
- Reading or writing identity keys (`/v1/identity/me`) needs the user's Supabase session in `X-Session-Token` as well as the API key. Writes need a sign-in from the last 15 minutes.

## Development commands

```bash
# Desktop app
cmake -S shadowcypher-qt -B build -G Ninja -DBUILD_TESTING=ON
cmake --build build && ctest --test-dir build --output-on-failure

# API (Cloudflare Worker)
cd backend/api
npm run dev          # local dev server
npm run typecheck
npm test

# ShadowOS ISO
cd shadowos && bash build.sh
bash qemu-test.sh
```

## Working rules for Claude sessions

- **One worktree and branch per session.** Never work directly on `main` in the shared checkout; several sessions run at once. Use a worktree under `.claude/worktrees/` on a branch named `claude/<topic>`, and open a PR.
- **Commit only the files you changed.** Never stash, reset or switch branches in a checkout another session might be using.
- **No production changes without the user's explicit OK in that conversation.** That covers `wrangler deploy`, `wrangler pages deploy`, Supabase migrations and pushes to `main`. Approval in one session doesn't carry over to another.
- **Deploys:**
  - Website: the Cloudflare Pages project `shadowcypher` deploys `www/` automatically from `main`. Don't deploy it by hand.
  - API: `cd backend/api && npm run deploy` ships whatever is in the working tree. Only run it from a clean checkout of `main`, after `npm run typecheck` and `npm test` pass.
- **Migrations:** apply a new file in `backend/api/migrations/` to Supabase before deploying code that needs it.
- **Android:** `android/app/src/main/assets/public` is a frozen copy of the site. Login or protocol changes in `www/` don't reach the Android app until that copy is refreshed.

## Environment / secrets

All secrets go through `wrangler secret put` and are never committed. Public vars live in `backend/api/wrangler.toml`.

Required secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_WEBHOOK_SECRET`, `NEON_DATABASE_URL`, `RESEND_API_KEY`.

## Repo hygiene rules (non-negotiable)

**Never commit:**
- Secrets, keys, tokens or credentials (`*.pem`, `*.key`, `*.env`, `config.json`, `*.creds`)
- Debug or test output (`*.log`, `*.tmp`, `err.txt`, screenshots used for debugging)
- Build output or binaries (`*.o`, compiled executables, `build/`)
- Planning docs (`PHASE_*.md`, `*_IMPLEMENTATION.md`), which belong in notes, not the repo
- IDE and tool configs (`.aider*`, `.cursor/`, `.crush/`)

**Product directories on `main`:** `shadowcypher-qt/`, `www/`, `backend/`, `shadowos/`, `android/`, `blog/`. Anything else needs a reason.

**Root-level files allowed:** LICENSE, README.md, CLAUDE.md, CNAME, .gitignore, manifest.json, sitemap.xml, sw.js, icons, privacy.html, terms.html, self-host.html, docs.html, roadmap.html, shadow.html, status.html, styles.css, device.html.

**Don't create documentation that isn't user-facing.**

## Git commit conventions

- Do NOT add `Co-Authored-By: Claude` or any Anthropic attribution lines to commits
- Do NOT add `Claude-Session:` lines to commit messages
- Commits belong to the project owner: **jakes1345**
- PR descriptions should not include Claude Code attribution footers

## Code conventions

- `callApi(path, opts)` in `www/index.html` returns **parsed JSON**, not a `Response`. Don't call `.ok` or `.json()` on the result.
- `neonRegisterUser(env, userId, email, apiKey)`: the 4th argument is the API key string, not the handle.
- API key pattern: `/^sc_live_[a-f0-9]{48}$/`
- Look up auth users with `findAuthUserByEmail` (exact match). GoTrue ignores an `email` query parameter and returns every user.
- The chat vault key lives in memory only (`_vaultKey`), derived at login and never persisted.
