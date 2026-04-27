# ShadowCypher API (Cloudflare Worker)

Backend for `api.shadowcypher.site`. Validates user API keys against Supabase, returns user profile, manages key rotation/revocation.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/health` | none | Liveness probe |
| GET | `/v1/me` | Bearer key | Return current user's profile + plan |
| POST | `/v1/keys/rotate` | Bearer key | Issue new key, invalidate old |
| POST | `/v1/keys/revoke` | Bearer key | Permanently invalidate current key |

Auth header: `Authorization: Bearer sc_live_<48 hex chars>`

## Local dev

```bash
cd backend/api
npm install
cp .dev.vars.example .dev.vars     # then edit with your service-role key
npm run dev                         # runs at http://localhost:8787
curl http://localhost:8787/v1/health
```

## Deploy

```bash
# One-time setup
npx wrangler login                                       # browser auth
npx wrangler secret put SUPABASE_URL                     # paste https://...supabase.co
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY        # paste ROTATED service-role key

# Each deploy
npm run deploy                                           # → api.shadowcypher.site
```

## Security model

- `SUPABASE_SERVICE_ROLE_KEY` is a Worker secret. **Never** in code, **never** in git, **never** sent to the browser.
- All Supabase access happens server-side via service-role.
- The browser only ever holds the user's **anon** key + their personal `sc_live_…` API key.
- Row-Level Security policies in Supabase enforce that users can only read/write their own row even if the anon key leaks.
