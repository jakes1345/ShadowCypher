# ShadowCypher API

The Cloudflare Worker behind `api.shadowcypher.site`. The web app, the desktop app, the Android app and the Guardian agent all talk to it. Entry point: `src/index.ts`.

It runs on:

- Supabase for auth and the main PostgreSQL database, with Neon as a mirror (`src/neon.ts`). API-key lookups try Neon first and fall back to Supabase.
- A Durable Object, `ChatRoom` (`src/chat_do.ts`), for WebSocket chat rooms.
- R2 (`SHADOW_FILES`) for Drive and chat attachments.
- KV for the desktop OTA manifest (`SHADOW_OTA`) and rate limits (`SHADOW_RL`).
- Cloudflare Email Routing for inbound mail (the Worker's `email` handler) and Resend for outbound.
- An hourly cron (`0 * * * *`) that pulls CVEs from NVD for the last two hours, matches them against users' devices by open port and sends alerts (`src/cve_matcher.ts`).

## Auth

Most routes need a personal API key: `Authorization: Bearer sc_live_<48 hex chars>`. The routes under `/v1/identity/me` also need the user's Supabase session in `X-Session-Token`, and writes there need a sign-in from the last 15 minutes.

A few routes are public: health and version checks, the device-login kickoff and poll, `GET /v1/auth/kdf`, public-key lookup, public profiles, the Stripe webhook (signature-checked) and the Supabase user webhook (secret-checked).

## Endpoints

`GET /` returns a JSON list of routes. The main groups:

| Area | Routes |
|---|---|
| Account | `GET /v1/me`, `POST /v1/keys/rotate`, `POST /v1/keys/revoke`, `PATCH /v1/me/profile`, `GET /v1/me/export`, `GET /v1/me/stats`, `GET /v1/me/audit`, `GET /v1/me/mfa`, `POST /v1/me/delete` |
| Sign-in | `POST /v1/auth/device`, `POST /v1/auth/device/poll`, `POST /v1/auth/device/authorize`, `GET /v1/auth/kdf`, `POST /v1/auth/send-recovery-kit`, `POST /v1/auth/recover` |
| Identity keys | `GET /v1/identity/lookup`, `GET /v1/identity/me`, `POST /v1/identity/me` |
| Guardian | `/v1/agents` (list, register, heartbeat), `POST /v1/scans`, `GET /v1/scans/recent`, `/v1/devices`, `/v1/incidents` (create, list, ack), `GET /v1/cve-alerts`, `GET /v1/guardian/summary` |
| Missions | `POST /v1/agents/:id/missions`, `GET /v1/agents/:id/missions/pending`, `POST /v1/missions/:id/result`, `GET /v1/missions`, `GET /v1/missions/:id` |
| Mail | `GET /v1/mail/inbox`, `GET /v1/mail/count`, `POST /v1/mail/send`, `GET`/`DELETE /v1/mail/:id`, `POST /v1/mail/:id/read`, `POST /v1/mail/:id/reply` |
| Chat | `/v1/chat/rooms`, `/v1/chat/messages`, `/v1/chat/send`, `/v1/chat/dm`, `/v1/chat/presence`, `/v1/chat/online`, WebSocket at `GET /v1/chat/ws?room=<name>` |
| Drive | `GET /v1/files`, `POST /v1/files/upload`, `GET`/`DELETE /v1/files/:key` |
| Calendar | `GET`/`POST /v1/calendar/events`, `PATCH`/`DELETE /v1/calendar/events/:id` |
| Assistant | `POST /v1/assistant/query`, `GET /v1/assistant/usage`, `POST /v1/assistant/byok`, `POST /v1/assistant/ollama` |
| Threat data | `GET /v1/threats`, `GET /v1/threats/stats`, and lookups under `/v1/shadow/` (`cve`, `ip`, `breach`, `dns`, `search`, `wiki`, `instant`, `weather`, `currency`) |
| Teams, webhooks, notifications, referrals | `/v1/teams/*`, `/v1/webhooks/*`, `/v1/notifications/*`, `/v1/referrals/*` |
| Billing | `POST /v1/billing/checkout`, `POST /v1/billing/portal`, `POST /v1/billing/webhook` (Stripe) |
| Other | `GET /v1/health`, `GET /v1/agent/version`, `GET`/`POST /v1/shadow/ota`, `GET /v1/admin/*` |

Some routes are rate-limited per user through KV (assistant queries, scans, incidents, uploads, mail sends, room creation and others). The limits are in `src/index.ts`.

The assistant answers with Anthropic's API by default (`ANTHROPIC_MODEL` in `wrangler.toml`). Users can switch to their own Anthropic key (stored encrypted) or their own Ollama endpoint.

## Local dev

```bash
cd backend/api
npm install
cp .dev.vars.example .dev.vars     # then fill in your Supabase URL and service-role key
npm run dev                        # http://localhost:8787
curl http://localhost:8787/v1/health
```

`npm run typecheck` runs `tsc --noEmit`. `npm test` runs the Vitest suite in `src/__tests__/`.

## Configuration

Public variables are in `wrangler.toml`. Secrets go in with `npx wrangler secret put <NAME>` and are never committed.

Required: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_WEBHOOK_SECRET`, `NEON_DATABASE_URL`, `RESEND_API_KEY`.

Needed for the features that use them: the `STRIPE_*` keys and price IDs (billing), `ANTHROPIC_API_KEY` (assistant), `BYOK_ENCRYPTION_SECRET` (stored user keys), `PUSH_VAPID_*` (push notifications), `SHADOW_ADMIN_KEY` (OTA manifest updates). Optional: `NVD_API_KEY`, `ABUSEIPDB_KEY`, `HIBP_KEY`, `BRAVE_SEARCH_KEY`, `OLLAMA_DEFAULT_MODEL`.

Database changes live in `migrations/` and are applied to Supabase in order. Apply a new migration before deploying code that depends on it.

## Deploy

```bash
npx wrangler login
npm run deploy        # wrangler deploy, to api.shadowcypher.site
```

`npm run deploy` ships whatever is in your working tree, so run it from a clean checkout of `main` after `npm run typecheck` and `npm test` pass.

## Security model

- The service-role key is a Worker secret. It's never in code, in git, or sent to a browser.
- All database access from clients goes through the Worker, which checks the API key and scopes queries to that user.
- The browser holds the public Supabase anon key (for sign-in) and the user's own `sc_live_…` key.
- Row-level security is enabled on many of the tables in `migrations/` as a second layer, but not on all of them, so the Worker is the access control that matters.
