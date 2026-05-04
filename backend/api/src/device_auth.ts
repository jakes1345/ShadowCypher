/**
 * Phase 4K — Device authorization flow.
 *
 * Lets the shadow-cli agent authenticate without paste-key UX. Modeled on RFC 8628.
 *
 * Flow:
 *   1. Agent: POST /v1/auth/device { client_label }
 *      → { device_code, user_code (8 chars), verification_uri, expires_in, interval }
 *   2. User opens verification_uri in a browser, signs in if needed,
 *      types the user_code, clicks Authorize. Site calls /v1/auth/device/authorize
 *      with the user_code (the user is authenticated by their Bearer key).
 *   3. Agent polls POST /v1/auth/device/poll { device_code }
 *      → { status: "pending" } until authorized, then { status: "authorized", api_key }.
 *
 * Codes expire after 10 minutes. Each code is single-use.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate } from "./supabase";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

// User codes use a small alphabet (no 0/O/1/I to avoid confusion when typing)
const USER_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

function genUserCode(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  let code = "";
  for (let i = 0; i < 8; i++) code += USER_CODE_ALPHABET[bytes[i] % USER_CODE_ALPHABET.length];
  return code.slice(0, 4) + "-" + code.slice(4);
}

function genDeviceCode(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

/** POST /v1/auth/device — agent kicks off the flow (no auth needed). */
export async function startDeviceAuth(req: Request, env: Env, _user: unknown, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { client_label?: string };
  const device_code = genDeviceCode();
  const user_code = genUserCode();
  const expires_in = 600; // 10 min
  const expires_at = new Date(Date.now() + expires_in * 1000).toISOString();

  await dbInsert(env, "device_auth_codes", {
    device_code,
    user_code,
    client_label: (body.client_label || "shadow-cli").slice(0, 96),
    status: "pending",
    expires_at,
  });

  return json({
    device_code,
    user_code,
    verification_uri: "https://shadowcypher.site/device",
    verification_uri_complete: `https://shadowcypher.site/device?code=${encodeURIComponent(user_code)}`,
    expires_in,
    interval: 5,
  }, {}, cors);
}

/** POST /v1/auth/device/poll — agent polls (no auth). */
export async function pollDeviceAuth(req: Request, env: Env, _user: unknown, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { device_code?: string };
  if (!body.device_code) return json({ error: "device_code_required" }, { status: 400 }, cors);

  const rows = await dbSelect<{
    device_code: string;
    user_code: string;
    user_id: string | null;
    status: string;
    expires_at: string;
  }>(env, "device_auth_codes", {
    select: "device_code,user_code,user_id,status,expires_at",
    filters: { device_code: `eq.${body.device_code}` },
    limit: 1,
  });
  const row = rows[0];
  if (!row) return json({ error: "invalid_code" }, { status: 404 }, cors);

  if (new Date(row.expires_at).getTime() < Date.now()) {
    await dbUpdate(env, "device_auth_codes", { device_code: `eq.${row.device_code}` }, { status: "expired" });
    return json({ status: "expired" }, { status: 410 }, cors);
  }

  if (row.status === "pending") return json({ status: "pending" }, {}, cors);
  if (row.status === "denied") return json({ status: "denied" }, { status: 403 }, cors);

  if (row.status === "authorized" && row.user_id) {
    // Hand back the user's API key + mark consumed (single-use)
    const apiKeyResp = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${row.user_id}`, {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      },
    });
    if (!apiKeyResp.ok) return json({ error: "lookup_failed" }, { status: 500 }, cors);
    const userData = (await apiKeyResp.json()) as { user_metadata?: { api_key?: string }; email?: string };
    const apiKey = userData.user_metadata?.api_key;
    if (!apiKey) return json({ error: "user_has_no_api_key" }, { status: 500 }, cors);

    await dbUpdate(env, "device_auth_codes", { device_code: `eq.${row.device_code}` }, {
      status: "consumed",
      consumed_at: new Date().toISOString(),
    });

    return json({
      status: "authorized",
      api_key: apiKey,
      email: userData.email,
    }, {}, cors);
  }

  if (row.status === "consumed") return json({ status: "consumed" }, { status: 410 }, cors);
  return json({ status: row.status }, {}, cors);
}

/** POST /v1/auth/device/authorize — site calls after user clicks Authorize. Authed. */
export async function authorizeDeviceAuth(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { user_code?: string; deny?: boolean };
  if (!body.user_code) return json({ error: "user_code_required" }, { status: 400 }, cors);

  // Normalize: strip whitespace, uppercase
  const code = body.user_code.trim().toUpperCase();

  const rows = await dbSelect<{ device_code: string; status: string; expires_at: string; client_label: string | null }>(
    env, "device_auth_codes",
    {
      select: "device_code,status,expires_at,client_label",
      filters: { user_code: `eq.${code}` },
      limit: 1,
    }
  );
  const row = rows[0];
  if (!row) return json({ error: "invalid_code" }, { status: 404 }, cors);

  if (new Date(row.expires_at).getTime() < Date.now()) {
    return json({ error: "expired" }, { status: 410 }, cors);
  }
  if (row.status !== "pending") {
    return json({ error: "already_handled", current_status: row.status }, { status: 409 }, cors);
  }

  await dbUpdate(env, "device_auth_codes", { device_code: `eq.${row.device_code}` }, {
    status: body.deny ? "denied" : "authorized",
    user_id: user.id,
    authorized_at: new Date().toISOString(),
  });

  return json({
    status: body.deny ? "denied" : "authorized",
    client_label: row.client_label,
  }, {}, cors);
}
