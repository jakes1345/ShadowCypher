/**
 * ShadowCypher Backend API — Cloudflare Worker entry point.
 *
 * v1/auth:
 *   GET  /v1/health             — liveness probe (no auth)
 *   GET  /v1/me                 — current user profile
 *   POST /v1/keys/rotate        — issue a new api key
 *   POST /v1/keys/revoke        — invalidate current key
 *
 * v1/guardian:
 *   POST /v1/agents/register    — register an agent install
 *   POST /v1/agents/heartbeat   — agent heartbeat (?agent_id=)
 *   POST /v1/scans              — upload scan results + auto-detect new devices
 *   GET  /v1/devices            — list all devices for the current user
 *   GET  /v1/scans/recent       — recent scan history
 *   POST /v1/incidents          — agent raises a security incident
 *   GET  /v1/incidents          — list incidents (?open=1 for unacked only)
 *   POST /v1/incidents/ack      — acknowledge an incident (?incident_id=)
 *
 * v1/threats:
 *   GET  /v1/threats        — recent CVEs from NVD (?days=7&severity=CRITICAL&limit=25)
 *   GET  /v1/threats/stats  — counts by severity (last 7 days)
 *
 * Auth: Authorization: Bearer sc_live_<48 hex chars>
 * Secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (set via `wrangler secret put`)
 */

import {
  listAgents,
  registerAgent,
  heartbeatAgent,
  uploadScan,
  listDevices,
  recentScans,
  createIncident,
  listIncidents,
  ackIncident,
} from "./guardian";
import { createCheckout, createPortal, handleWebhook } from "./billing";
import { getPreferences, updatePreferences, sendTest } from "./notifications";
import {
  handleQuery as assistantQuery,
  getUsage as assistantUsage,
  setByok as assistantSetByok,
  setOllama as assistantSetOllama,
} from "./assistant";
import {
  createTeam,
  listTeams,
  inviteMember,
  listInvites,
  acceptInvite,
  leaveTeam,
} from "./teams";
import { createWebhook, listWebhooks, deleteWebhook, testWebhook } from "./webhooks";
import { exportData, getStats } from "./account";
import { listAudit, audit, clientHints } from "./audit";
import { getMfaStatus } from "./mfa";
import { startDeviceAuth, pollDeviceAuth, authorizeDeviceAuth } from "./device_auth";
import { getMyReferral, claimReferral } from "./referrals";
import { getThreats, getThreatStats } from "./threats";
import { dbSelect } from "./supabase";
import { getEffectivePlan, trialDaysRemaining, type ProfileForPlan } from "./plans";

export interface Env {
  SUPABASE_URL: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
  ENVIRONMENT: string;
  ALLOWED_ORIGINS: string;
  // Billing (set via wrangler secret put)
  STRIPE_SECRET_KEY: string;
  STRIPE_WEBHOOK_SECRET: string;
  STRIPE_PRICE_GUARDIAN_PRO: string;
  STRIPE_PRICE_OPERATOR: string;
  STRIPE_PRICE_GUARDIAN_PRO_ANNUAL: string;
  STRIPE_PRICE_OPERATOR_ANNUAL: string;
  SITE_URL: string;
  // Notifications (P4B)
  RESEND_API_KEY: string;
  RESEND_FROM_EMAIL: string;
  PUSH_VAPID_PUBLIC_KEY: string;
  PUSH_VAPID_PRIVATE_KEY: string;
  PUSH_VAPID_SUBJECT: string;
  // AI assistant (P4C)
  ANTHROPIC_API_KEY: string;
  ANTHROPIC_MODEL: string;
  // BYOK encryption (P4F)
  BYOK_ENCRYPTION_SECRET: string;
}

interface SupabaseUser {
  id: string;
  email: string;
  created_at: string;
  user_metadata: Record<string, unknown>;
  app_metadata: Record<string, unknown>;
}

const KEY_PATTERN = /^sc_live_[a-f0-9]{48}$/;

// ─── CORS ───────────────────────────────────────────────────────────────────

function corsHeaders(origin: string | null, allowed: string): HeadersInit {
  const allowList = allowed.split(",").map((o) => o.trim());
  const allowOrigin = origin && allowList.includes(origin) ? origin : allowList[0];
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...cors,
      ...(init.headers || {}),
    },
  });
}

// ─── Auth ───────────────────────────────────────────────────────────────────

function extractKey(req: Request): string | null {
  const auth = req.headers.get("Authorization") || "";
  const m = auth.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;
  const key = m[1].trim();
  return KEY_PATTERN.test(key) ? key : null;
}

/**
 * Look up a user by their api_key in user_metadata.
 * Uses Supabase Admin REST API (requires service-role key).
 *
 * NOTE: For production scale, replace this with a dedicated `api_keys` table
 * (key hash + user_id, indexed). user_metadata scan is fine up to ~10k users.
 */
async function findUserByKey(env: Env, key: string): Promise<SupabaseUser | null> {
  // Page through users (max 1000 per page — sufficient for early stage).
  // Scaling note: when user count > 10k, introduce a Postgres api_keys table.
  const url = `${env.SUPABASE_URL}/auth/v1/admin/users?per_page=1000`;
  const resp = await fetch(url, {
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!resp.ok) {
    console.error("Supabase admin fetch failed", resp.status, await resp.text());
    return null;
  }
  const body = (await resp.json()) as { users: SupabaseUser[] };
  for (const u of body.users) {
    if ((u.user_metadata as { api_key?: string })?.api_key === key) return u;
  }
  return null;
}

async function updateUserMetadata(
  env: Env,
  userId: string,
  patch: Record<string, unknown>
): Promise<boolean> {
  const url = `${env.SUPABASE_URL}/auth/v1/admin/users/${userId}`;
  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_metadata: patch }),
  });
  return resp.ok;
}

function generateApiKey(): string {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `sc_live_${hex}`;
}

// ─── Handlers ───────────────────────────────────────────────────────────────

/**
 * POST /v1/me/delete — hard delete the user's account and all data.
 * Requires the Bearer api_key (proves ownership). Cascade-deletes all child rows
 * via foreign-key constraints on the auth.users id.
 */
async function deleteAccount(req: Request, env: Env, user: { id: string; email: string }, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { confirm_email?: string };
  if ((body.confirm_email || "").trim().toLowerCase() !== user.email.toLowerCase()) {
    return new Response(
      JSON.stringify({ error: "confirm_email_must_match", expected: user.email }),
      { status: 400, headers: { "Content-Type": "application/json", ...cors } }
    );
  }
  // Audit BEFORE we delete — once delete cascades, we can't add the entry
  await audit(env, user.id, "account_deleted", clientHints(req));
  // Delete via Supabase Admin API — cascades through profiles, agents, devices, scans, incidents, team_members, notification_prefs, audit_log
  const resp = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${user.id}`, {
    method: "DELETE",
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!resp.ok) {
    const txt = await resp.text();
    console.error("[delete] failed", resp.status, txt);
    return new Response(
      JSON.stringify({ error: "delete_failed", detail: txt }),
      { status: 500, headers: { "Content-Type": "application/json", ...cors } }
    );
  }
  return new Response(JSON.stringify({ deleted: true }), {
    headers: { "Content-Type": "application/json", ...cors },
  });
}

async function handleMe(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const key = extractKey(req);
  if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);

  const user = await findUserByKey(env, key);
  if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);

  const meta = user.user_metadata as {
    handle?: string;
    api_key_created_at?: string;
  };

  // Plan + subscription state come from public.profiles (source of truth, updated by Stripe webhook)
  type ProfileRow = ProfileForPlan & { cancel_at_period_end: boolean };
  const profiles = await dbSelect<ProfileRow>(env, "profiles", {
    select: "plan,subscription_status,current_period_end,cancel_at_period_end,trial_ends_at",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  const profile = profiles[0];
  const effectivePlan = getEffectivePlan(profile);
  const trialDays = trialDaysRemaining(profile);
  const inTrial = trialDays > 0 && (profile?.plan ?? "community") === "community";

  return json(
    {
      id: user.id,
      email: user.email,
      handle: meta.handle ?? user.email.split("@")[0],
      plan: profile?.plan ?? "community",
      effective_plan: effectivePlan,
      in_trial: inTrial,
      trial_ends_at: profile?.trial_ends_at ?? null,
      trial_days_remaining: trialDays,
      subscription_status: profile?.subscription_status ?? null,
      current_period_end: profile?.current_period_end ?? null,
      cancel_at_period_end: profile?.cancel_at_period_end ?? false,
      key_created_at: meta.api_key_created_at ?? user.created_at,
    },
    {},
    cors
  );
}

async function handleRotate(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const key = extractKey(req);
  if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);

  const user = await findUserByKey(env, key);
  if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);

  const newKey = generateApiKey();
  const ok = await updateUserMetadata(env, user.id, {
    ...user.user_metadata,
    api_key: newKey,
    api_key_created_at: new Date().toISOString(),
    api_key_previous_revoked_at: new Date().toISOString(),
  });
  if (!ok) return json({ error: "rotate_failed" }, { status: 500 }, cors);

  audit(env, user.id, "key_rotated", clientHints(req));
  return json({ api_key: newKey }, {}, cors);
}

async function handleRevoke(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const key = extractKey(req);
  if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);

  const user = await findUserByKey(env, key);
  if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);

  const ok = await updateUserMetadata(env, user.id, {
    ...user.user_metadata,
    api_key: null,
    api_key_revoked_at: new Date().toISOString(),
  });
  if (!ok) return json({ error: "revoke_failed" }, { status: 500 }, cors);

  audit(env, user.id, "key_revoked", clientHints(req));
  return json({ revoked: true }, {}, cors);
}

// ─── Worker entry ───────────────────────────────────────────────────────────

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const origin = req.headers.get("Origin");
    const cors = corsHeaders(origin, env.ALLOWED_ORIGINS);

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    const url = new URL(req.url);
    const path = url.pathname;

    try {
      if (path === "/" || path === "") {
        return json(
          {
            service: "shadowcypher-api",
            version: "0.2.0",
            environment: env.ENVIRONMENT,
            docs: "https://github.com/jakes1345/ShadowCypher/blob/main/backend/api/README.md",
            endpoints: {
              auth: ["GET /v1/health", "GET /v1/me", "POST /v1/keys/rotate", "POST /v1/keys/revoke"],
              guardian: [
                "GET /v1/agents",
                "POST /v1/agents/register",
                "POST /v1/agents/heartbeat?agent_id=",
                "POST /v1/scans",
                "GET /v1/devices",
                "GET /v1/scans/recent",
                "POST /v1/incidents",
                "GET /v1/incidents?open=1",
                "POST /v1/incidents/ack?incident_id=",
              ],
              billing: [
                "POST /v1/billing/checkout",
                "POST /v1/billing/portal",
                "POST /v1/billing/webhook",
              ],
              notifications: [
                "GET /v1/notifications/preferences",
                "POST /v1/notifications/preferences",
                "POST /v1/notifications/test",
              ],
              assistant: [
                "POST /v1/assistant/query",
                "GET /v1/assistant/usage",
                "POST /v1/assistant/byok",
                "POST /v1/assistant/ollama",
              ],
              account: [
                "POST /v1/me/delete",
                "GET /v1/me/export",
                "GET /v1/me/stats",
                "GET /v1/me/audit",
                "GET /v1/me/mfa",
              ],
              cli_auth: [
                "POST /v1/auth/device",
                "POST /v1/auth/device/poll",
                "POST /v1/auth/device/authorize",
              ],
              referrals: [
                "GET /v1/referrals/me",
                "POST /v1/referrals/claim",
              ],
              webhooks: [
                "POST /v1/webhooks",
                "GET /v1/webhooks",
                "POST /v1/webhooks/delete",
                "POST /v1/webhooks/test",
              ],
              teams: [
                "POST /v1/teams",
                "GET /v1/teams",
                "POST /v1/teams/invite",
                "GET /v1/teams/invites",
                "POST /v1/teams/accept",
                "POST /v1/teams/leave",
              ],
            },
          },
          {},
          cors
        );
      }
      if (path === "/v1/health") {
        return json({ ok: true, environment: env.ENVIRONMENT, ts: Date.now() }, {}, cors);
      }
      // Stripe webhook is unauthenticated (signature-verified inside the handler).
      // Stripe sends raw body; we don't apply CORS here.
      if (path === "/v1/billing/webhook" && req.method === "POST") return handleWebhook(req, env, cors);

      // Device-authorization flow — kickoff + poll are unauthenticated (the device_code IS the secret)
      if (path === "/v1/auth/device" && req.method === "POST") return startDeviceAuth(req, env, undefined, cors);
      if (path === "/v1/auth/device/poll" && req.method === "POST") return pollDeviceAuth(req, env, undefined, cors);

      if (path === "/v1/me" && req.method === "GET") return handleMe(req, env, cors);
      if (path === "/v1/keys/rotate" && req.method === "POST") return handleRotate(req, env, cors);
      if (path === "/v1/keys/revoke" && req.method === "POST") return handleRevoke(req, env, cors);

      // Authed routes — resolve user once, dispatch
      const authedRoutes: Record<string, (req: Request, env: Env, user: { id: string; email: string }, cors: HeadersInit) => Promise<Response>> = {
        "GET /v1/agents":             listAgents,
        "POST /v1/agents/register":   registerAgent,
        "POST /v1/agents/heartbeat":  heartbeatAgent,
        "POST /v1/scans":             uploadScan,
        "GET /v1/devices":            listDevices,
        "GET /v1/scans/recent":       recentScans,
        "POST /v1/incidents":         createIncident,
        "GET /v1/incidents":          listIncidents,
        "POST /v1/incidents/ack":     ackIncident,
        "POST /v1/billing/checkout":  createCheckout,
        "POST /v1/billing/portal":    createPortal,
        "GET /v1/notifications/preferences":  getPreferences,
        "POST /v1/notifications/preferences": updatePreferences,
        "POST /v1/notifications/test":        sendTest,
        "POST /v1/assistant/query":           assistantQuery,
        "GET /v1/assistant/usage":            assistantUsage,
        "POST /v1/assistant/byok":            assistantSetByok,
        "POST /v1/assistant/ollama":          assistantSetOllama,
        "POST /v1/me/delete":                 deleteAccount,
        "POST /v1/auth/device/authorize":     authorizeDeviceAuth,
        "GET /v1/referrals/me":               getMyReferral,
        "POST /v1/referrals/claim":           claimReferral,
        "GET /v1/me/export":                  exportData,
        "GET /v1/me/stats":                   getStats,
        "GET /v1/me/audit":                   listAudit,
        "GET /v1/me/mfa":                     getMfaStatus,
        "POST /v1/webhooks":                  createWebhook,
        "GET /v1/webhooks":                   listWebhooks,
        "POST /v1/webhooks/delete":           deleteWebhook,
        "POST /v1/webhooks/test":             testWebhook,
        "POST /v1/teams":                     createTeam,
        "GET /v1/teams":                      listTeams,
        "POST /v1/teams/invite":              inviteMember,
        "GET /v1/teams/invites":              listInvites,
        "POST /v1/teams/accept":              acceptInvite,
        "POST /v1/teams/leave":               leaveTeam,
        "GET /v1/threats":                    getThreats,
        "GET /v1/threats/stats":              getThreatStats,
      };
      const routeKey = `${req.method} ${path}`;
      const handler = authedRoutes[routeKey];
      if (handler) {
        const key = extractKey(req);
        if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);
        const user = await findUserByKey(env, key);
        if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);
        return handler(req, env, { id: user.id, email: user.email }, cors);
      }

      return json({ error: "not_found", path }, { status: 404 }, cors);
    } catch (err) {
      const message = err instanceof Error ? err.message : "unknown_error";
      console.error("[api] unhandled", message);
      return json({ error: "internal", message }, { status: 500 }, cors);
    }
  },
};
