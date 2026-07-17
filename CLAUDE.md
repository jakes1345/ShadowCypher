# ShadowCypher

Sovereign personal security platform — network monitoring, CVE threat feed, local AI, and offensive toolkit. Self-hostable, no telemetry.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Single-page HTML/JS (`www/index.html`) — no build step, ships as-is |
| API | Cloudflare Worker (`backend/api/src/index.ts`) — TypeScript, Wrangler 4 |
| Auth + DB | Supabase (PostgreSQL, Auth) |
| Backup DB | Neon (PostgreSQL) — mirrors Supabase via webhook |
| Email | Cloudflare Email Routing catch-all → Worker → Supabase; outbound via Resend |
| Real-time chat | Cloudflare Durable Objects (`ChatRoom` class in `chat_do.ts`) |
| File storage | Cloudflare R2 (`SHADOW_FILES` binding) |
| OTA updates | Cloudflare KV (`SHADOW_OTA` binding) |
| Desktop agent | Python (`agent/`) — runs on user machines, phones home to API |
| ShadowOS | Arch Linux ISO (`shadowos/`) built with archiso/mkarchiso |

## Key directories

```
www/index.html          # Entire frontend (auth, chat, mail, dashboard, drive)
backend/api/src/
  index.ts              # Worker entrypoint — all routes, auth middleware
  chat_do.ts            # Durable Object for WebSocket chat rooms
  neon.ts               # Neon PostgreSQL helpers (mirrors Supabase)
  supabase.ts           # Supabase REST helpers
  mail.ts               # Shadow Mail (inbound/outbound)
  account.ts            # /v1/me/export, /v1/me/stats
  *.ts                  # Feature modules (billing, webhooks, guardian, etc.)
shadowos/               # Arch Linux ISO profile
  profile/airootfs/usr/local/bin/shadowos-ai-setup   # Ollama model installer
agent/                  # Python agent that runs on monitored machines
shadowcypher/           # MCP servers for intel/offensive/campaign tooling
```

## Auth model

- Users sign up with a handle → internal email `handle@shadowcypher.site`
- Supabase Auth issues JWTs; API exchanges them for API keys (`sc_live_` + 48 hex chars)
- API key stored in `Authorization: Bearer` header for all API calls
- E2E chat encryption: PBKDF2 from account password → AES-256-GCM, derived silently at login

## Development commands

```bash
# API (Cloudflare Worker)
cd backend/api
npm run dev          # local dev server (wrangler dev)
npm run typecheck    # tsc --noEmit
npm test             # vitest run
npm run deploy       # wrangler deploy → production

# Check live worker logs
npm run tail         # wrangler tail

# Secrets (run once per secret)
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
wrangler secret put SUPABASE_WEBHOOK_SECRET
wrangler secret put NEON_DATABASE_URL
wrangler secret put RESEND_API_KEY

# ShadowOS ISO
cd shadowos && bash build.sh        # builds ISO via mkarchiso
bash qemu-test.sh                   # boots ISO in QEMU for testing
```

## Environment / secrets

All secrets go through `wrangler secret put` — never committed. Public vars in `backend/api/wrangler.toml`.

Required secrets:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — service role key for admin DB ops
- `SUPABASE_WEBHOOK_SECRET` — shared secret for `POST /v1/internal/supabase-event`
- `NEON_DATABASE_URL` — Neon PostgreSQL connection string
- `RESEND_API_KEY` — for transactional email via Resend

## API routes (key ones)

```
POST   /v1/auth/register          signup
POST   /v1/auth/login             login → returns api_key
POST   /v1/auth/recover           recovery code flow
GET    /v1/me                     authed user info
GET    /v1/chat/rooms             list chat rooms
WS     /v1/chat/ws?room=&key=     WebSocket for chat (Durable Object)
GET    /v1/mail/inbox             inbox list
POST   /v1/mail/send              send outbound email via Resend
POST   /v1/internal/supabase-event  Supabase webhook (new user → sync to Neon)
```

## Important conventions

- `callApi(path, opts)` in `www/index.html` returns **parsed JSON**, not a `Response` — don't call `.ok` or `.json()` on the result
- `neonRegisterUser(env, userId, email, apiKey)` — 4th arg is the api_key string, not handle
- API key pattern: `/^sc_live_[a-f0-9]{48}$/`
- Chat vault key lives in memory only (`_vaultKey`) — derived at login, never persisted
- Branch for Claude work: `claude/private-github-access-gz9kqg`
