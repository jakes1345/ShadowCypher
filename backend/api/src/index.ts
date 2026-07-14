/**
 * ShadowCypher Backend API — Cloudflare Worker entry point.
 *
 * v1/auth:
 *   GET  /v1/health                        — liveness probe (no auth)
 *   GET  /v1/me                            — current user profile
 *   POST /v1/keys/rotate                   — issue a new api key (sends key-rotated email)
 *   POST /v1/keys/revoke                   — invalidate current key
 *
 * v1/auth (unauthenticated):
 *   POST /v1/auth/send-recovery-kit        — send recovery codes to disposal email (discarded after)
 *   POST /v1/auth/recover                  — validate recovery code → issue session for password reset
 *
 * v1/internal (secret-gated, not for clients):
 *   POST /v1/internal/supabase-event       — Supabase auth webhook (new user → welcome email)
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
  listCveAlerts,
  guardianSummary,
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
  createMission,
  getPendingMissions,
  reportMissionResult,
  getMission,
  listMissions,
} from "./missions";
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
import { runCveMatchingCron } from "./cve_matcher";
import { getAgentVersion } from "./agent_version";
import { getWeather, getCurrency, getCve, getIpReputation, checkBreach, dnsLookup, webSearch, wikiSummary, ddgInstant } from "./shadow_apis";
import { getOtaManifest, updateOtaManifest } from "./ota";
import { listRooms, getMessages, sendMessage, updatePresence, getOnlineUsers, openDm, listDms } from "./chat";
import { uploadFile, downloadFile, deleteFile } from "./files";
export { ChatRoom } from "./chat_do";
import { dbSelect } from "./supabase";
import { neonFindUserByKey, neonRotateKey, neonRevokeKey, neonRegisterUser } from "./neon";
import { getEffectivePlan, trialDaysRemaining, type ProfileForPlan } from "./plans";
import { sendWelcomeEmail, sendKeyRotatedEmail, sendRecoveryKitEmail } from "./emails";
import {
  storeInboundMail,
  getInbox,
  getMailCount,
  getMail,
  markRead,
  replyMail,
  deleteMail,
  sendOutbound,
} from "./mail";

export interface Env {
  SUPABASE_URL: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
  ENVIRONMENT: string;
  ALLOWED_ORIGINS: string;
  // Supabase webhook secret (wrangler secret put SUPABASE_WEBHOOK_SECRET)
  SUPABASE_WEBHOOK_SECRET: string;
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
  // Agent auto-update
  AGENT_VERSION: string;
  AGENT_SHA256: string;
  // OTA manifest
  SHADOW_OTA: KVNamespace;
  SHADOW_ADMIN_KEY: string;
  // Neon (hot standby alongside Supabase)
  NEON_DATABASE_URL: string;
  // Optional: structured API keys (set via wrangler secret put)
  NVD_API_KEY?: string;
  ABUSEIPDB_KEY?: string;
  HIBP_KEY?: string;
  BRAVE_SEARCH_KEY?: string;
  OLLAMA_DEFAULT_MODEL?: string;
  // Durable Objects
  CHAT_ROOM: DurableObjectNamespace;
  // R2 file storage
  SHADOW_FILES: R2Bucket;
}

interface SupabaseUser {
  id: string;
  email: string;
  created_at: string;
  user_metadata: Record<string, unknown>;
  app_metadata: Record<string, unknown>;
}

const KEY_PATTERN = /^sc_live_[a-f0-9]{48}$/;

// ─── Rate limiting ──────────────────────────────────────────────────────────
// Module-scoped sliding window (per isolate). Not distributed — for true
// distributed rate limiting, configure Cloudflare Rate Limiting rules in the
// dashboard (Security → WAF → Rate Limiting Rules) on api.shadowcypher.site.
const _rl = new Map<string, number[]>();

function rateLimit(key: string, maxReqs: number, windowMs: number): boolean {
  const now = Date.now();
  const hits = (_rl.get(key) ?? []).filter((t) => now - t < windowMs);
  if (hits.length >= maxReqs) return false;
  hits.push(now);
  _rl.set(key, hits);
  if (_rl.size > 10_000) {
    const oldest = [..._rl.entries()].sort((a, b) => (a[1][0] ?? 0) - (b[1][0] ?? 0));
    for (let i = 0; i < 1000; i++) _rl.delete(oldest[i][0]);
  }
  return true;
}

// ─── CORS ───────────────────────────────────────────────────────────────────

function corsHeaders(origin: string | null, allowed: string): HeadersInit {
  const allowList = allowed.split(",").map((o) => o.trim());
  const allowOrigin = origin && allowList.includes(origin) ? origin : allowList[0];
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
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
  const key = m ? m[1].trim() : new URL(req.url).searchParams.get("key") ?? "";
  return KEY_PATTERN.test(key) ? key : null;
}

/**
 * Look up a user by api_key — races Supabase and Neon simultaneously.
 * Returns whichever responds first with a match. If one is down, the other wins.
 */
async function findUserByKey(env: Env, key: string): Promise<SupabaseUser | null> {
  // Supabase lookup (scans user_metadata)
  async function fromSupabase(): Promise<SupabaseUser | null> {
    let page = 1;
    const perPage = 1000;
    while (true) {
      const url = `${env.SUPABASE_URL}/auth/v1/admin/users?per_page=${perPage}&page=${page}`;
      const resp = await fetch(url, {
        headers: {
          apikey: env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
      });
      if (!resp.ok) return null;
      const body = (await resp.json()) as { users: SupabaseUser[] };
      for (const u of body.users) {
        if ((u.user_metadata as { api_key?: string })?.api_key === key) return u;
      }
      if (body.users.length < perPage) return null;
      page++;
    }
  }

  // Race both — first non-null result wins
  const [supabaseResult, neonResult] = await Promise.all([
    fromSupabase().catch(() => null),
    neonFindUserByKey(env, key).catch(() => null),
  ]);

  return supabaseResult ?? neonResult;
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
  const ip = req.headers.get("CF-Connecting-IP") ?? req.headers.get("X-Forwarded-For") ?? "unknown";
  const key = extractKey(req);
  if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);

  const user = await findUserByKey(env, key);
  if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);

  // Tighter rate limit: 5 rotations per hour per user
  if (!rateLimit(`rotate:${user.id}`, 5, 3_600_000))
    return json({ error: "rate_limited" }, { status: 429 }, cors);
  // Per-IP gate
  if (!rateLimit(`rotate_ip:${ip}`, 10, 3_600_000))
    return json({ error: "rate_limited" }, { status: 429 }, cors);

  const newKey = generateApiKey();
  const [ok] = await Promise.all([
    updateUserMetadata(env, user.id, {
      ...user.user_metadata,
      api_key: newKey,
      api_key_created_at: new Date().toISOString(),
      api_key_previous_revoked_at: new Date().toISOString(),
    }),
    neonRotateKey(env, user.id, key, newKey).catch(() => null),
  ]);
  if (!ok) return json({ error: "rotate_failed" }, { status: 500 }, cors);

  audit(env, user.id, "key_rotated", clientHints(req));
  const rotatedHandle = (user.user_metadata as { handle?: string }).handle ?? user.email.split("@")[0];
  sendKeyRotatedEmail(env, user.email, rotatedHandle).catch(() => null);
  return json({ api_key: newKey }, {}, cors);
}

async function handleRevoke(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const key = extractKey(req);
  if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);

  const user = await findUserByKey(env, key);
  if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);

  const [ok] = await Promise.all([
    updateUserMetadata(env, user.id, {
      ...user.user_metadata,
      api_key: null,
      api_key_revoked_at: new Date().toISOString(),
    }),
    neonRevokeKey(env, user.id, key).catch(() => null),
  ]);
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
                "DELETE /v1/teams/leave",
              ],
              chat: [
                "GET /v1/chat/rooms",
                "GET /v1/chat/messages?room=global&limit=50&before=<iso>",
                "POST /v1/chat/send",
                "POST /v1/chat/presence",
                "GET /v1/chat/online?room=global",
              ],
              shadow: [
                "GET /v1/shadow/weather?q=<city>",
                "GET /v1/shadow/currency?from=USD&to=EUR&amount=1",
                "GET /v1/shadow/cve?q=<keyword|CVE-ID>&limit=5",
                "GET /v1/shadow/ip?addr=<ip>",
                "GET /v1/shadow/breach?email=<email>",
                "GET /v1/shadow/dns?q=<domain>&type=A",
                "GET /v1/shadow/ota (public) — OTA version manifest",
                "POST /v1/shadow/ota (admin key) — publish new release",
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
      if (path === "/v1/agent/version" && req.method === "GET") {
        return getAgentVersion(env, cors);
      }
      if (path === "/v1/notifications/vapid-public-key" && req.method === "GET") {
        return json({ public_key: env.PUSH_VAPID_PUBLIC_KEY || null }, {}, cors);
      }
      // Stripe webhook is unauthenticated (signature-verified inside the handler).
      // Stripe sends raw body; we don't apply CORS here.
      if (path === "/v1/billing/webhook" && req.method === "POST") return handleWebhook(req, env, cors);

      // Device-authorization flow — kickoff + poll are unauthenticated (the device_code IS the secret)
      const ip = req.headers.get("CF-Connecting-IP") ?? req.headers.get("X-Forwarded-For") ?? "unknown";
      if (path === "/v1/auth/device" && req.method === "POST") {
        if (!rateLimit(`device:${ip}`, 5, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        return startDeviceAuth(req, env, undefined, cors);
      }
      if (path === "/v1/auth/device/poll" && req.method === "POST") {
        if (!rateLimit(`poll:${ip}`, 30, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        return pollDeviceAuth(req, env, undefined, cors);
      }

      // Public knowledge endpoints — no API key required
      if (path === "/v1/shadow/wiki" && req.method === "GET") return wikiSummary(req, env, cors);
      if (path === "/v1/shadow/instant" && req.method === "GET") return ddgInstant(req, env, cors);

      // OTA manifest — GET is public, POST is admin-key gated
      if (path === "/v1/shadow/ota" && req.method === "GET") return getOtaManifest(env);
      if (path === "/v1/shadow/ota" && req.method === "POST") return updateOtaManifest(req, env);

      // Supabase auth webhook — fires on new user INSERT (configure in Supabase dashboard:
      //   Database Webhooks → auth.users INSERT → POST https://api.shadowcypher.site/v1/internal/supabase-event
      //   Add header: x-webhook-secret: <SUPABASE_WEBHOOK_SECRET>)
      if (path === "/v1/internal/supabase-event" && req.method === "POST") {
        const secret = req.headers.get("x-webhook-secret") ?? "";
        if (!env.SUPABASE_WEBHOOK_SECRET || secret !== env.SUPABASE_WEBHOOK_SECRET)
          return json({ error: "forbidden" }, { status: 403 });
        const payload = (await req.json().catch(() => null)) as {
          type?: string;
          record?: { id?: string; email?: string; raw_user_meta_data?: { handle?: string } };
        } | null;
        if (payload?.type === "INSERT" && payload.record?.email) {
          const { id, email, raw_user_meta_data } = payload.record;
          const handle = raw_user_meta_data?.handle ?? email!.split("@")[0];
          sendWelcomeEmail(env, email!, handle).catch(() => null);
          // Also register the user in Neon if they don't exist yet
          if (id) neonRegisterUser(env, id, email!, handle).catch(() => null);
        }
        return json({ ok: true });
      }

      // POST /v1/auth/send-recovery-kit — fire-and-forget: sends codes to disposal email then discards it.
      // Disposal email is NEVER stored. Rate-limited to prevent abuse as a spam relay.
      if (path === "/v1/auth/send-recovery-kit" && req.method === "POST") {
        if (!rateLimit(`recovery-kit:${ip}`, 3, 3_600_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        const body = (await req.json().catch(() => null)) as {
          disposal_email?: string; codes?: string[]; handle?: string;
        } | null;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!body?.disposal_email || !emailRegex.test(body.disposal_email) || !body.codes?.length || !body.handle) {
          return json({ error: "invalid_request" }, { status: 400 }, cors);
        }
        // Validate codes are hex strings of expected length — never store them
        const validCodes = body.codes.filter(c => typeof c === "string" && c.length > 6 && c.length < 64);
        sendRecoveryKitEmail(env, body.disposal_email, body.handle, validCodes).catch(() => null);
        return json({ sent: true }, {}, cors);
      }

      // POST /v1/auth/recover — validate recovery code, return a session the client can set.
      if (path === "/v1/auth/recover" && req.method === "POST") {
        if (!rateLimit(`recover:${ip}`, 5, 3_600_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        const body = (await req.json().catch(() => null)) as { handle?: string; code?: string } | null;
        if (!body?.handle || !body.code) return json({ error: "handle_and_code_required" }, { status: 400 }, cors);

        const userEmail = `${body.handle.toLowerCase().replace(/^@/, "")}@shadowcypher.site`;
        // Look up the user by their handle-derived email
        const usersResp = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users?email=${encodeURIComponent(userEmail)}`, {
          headers: { apikey: env.SUPABASE_SERVICE_ROLE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}` },
        });
        if (!usersResp.ok) return json({ error: "user_not_found" }, { status: 404 }, cors);
        const usersBody = (await usersResp.json()) as { users?: SupabaseUser[] };
        const user = usersBody.users?.[0];
        if (!user) return json({ error: "user_not_found" }, { status: 404 }, cors);

        const storedHashes: string[] = (user.user_metadata as { recovery_codes?: string[] })?.recovery_codes ?? [];
        // Hash the submitted code and check against stored hashes
        const submittedHash = Array.from(
          new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body.code.trim().toLowerCase())))
        ).map(b => b.toString(16).padStart(2, "0")).join("");

        const matchIdx = storedHashes.indexOf(submittedHash);
        if (matchIdx === -1) return json({ error: "invalid_code" }, { status: 401 }, cors);

        // Burn the used code — remove it from the list
        const remaining = storedHashes.filter((_, i) => i !== matchIdx);
        await updateUserMetadata(env, user.id, { ...user.user_metadata, recovery_codes: remaining });

        // Issue a short-lived magic link session so the client can set a new password
        const linkResp = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${user.id}/generate-link`, {
          method: "POST",
          headers: {
            apikey: env.SUPABASE_SERVICE_ROLE_KEY,
            Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ type: "recovery" }),
        });
        if (!linkResp.ok) return json({ error: "session_issue_failed" }, { status: 500 }, cors);
        const linkBody = (await linkResp.json()) as { properties?: { access_token?: string; refresh_token?: string } };
        const { access_token, refresh_token } = linkBody.properties ?? {};
        if (!access_token) return json({ error: "session_issue_failed" }, { status: 500 }, cors);

        return json({ access_token, refresh_token: refresh_token ?? null }, {}, cors);
      }

      if (path === "/v1/me" && req.method === "GET") return handleMe(req, env, cors);
      if (path === "/v1/keys/rotate" && req.method === "POST") return handleRotate(req, env, cors);
      if (path === "/v1/keys/revoke" && req.method === "POST") return handleRevoke(req, env, cors);

      // Authed routes — resolve user once, dispatch
      const authedRoutes: Partial<Record<string, (req: Request, env: Env, user: { id: string; email: string }, cors: HeadersInit) => Promise<Response>>> = {
        "GET /v1/agents":             listAgents,
        "POST /v1/agents/register":   registerAgent,
        "POST /v1/agents/heartbeat":  heartbeatAgent,
        "POST /v1/scans":             uploadScan,
        "GET /v1/devices":            listDevices,
        "GET /v1/scans/recent":       recentScans,
        "POST /v1/incidents":         createIncident,
        "GET /v1/incidents":          listIncidents,
        "POST /v1/incidents/ack":     ackIncident,
        "GET /v1/cve-alerts":         listCveAlerts,
        "GET /v1/guardian/summary":   guardianSummary,
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
        "DELETE /v1/teams/leave":             leaveTeam,
        "GET /v1/threats":                    getThreats,
        "GET /v1/threats/stats":              getThreatStats,
        // Shadow structured APIs (no LLM)
        "GET /v1/shadow/weather":             getWeather,
        "GET /v1/shadow/currency":            getCurrency,
        "GET /v1/shadow/cve":                 getCve,
        "GET /v1/shadow/ip":                  getIpReputation,
        "GET /v1/shadow/breach":              checkBreach,
        "GET /v1/shadow/dns":                 dnsLookup,
        "GET /v1/shadow/search":              webSearch,
        // Chat
        "GET /v1/chat/rooms":                 listRooms,
        "GET /v1/chat/messages":              getMessages,
        "POST /v1/chat/send":                 sendMessage,
        "POST /v1/chat/presence":             updatePresence,
        "GET /v1/chat/online":                getOnlineUsers,
        "GET /v1/chat/dm":                    listDms,
        "POST /v1/chat/dm/open":              openDm,
        // File storage
        "POST /v1/files/upload":              uploadFile,
        // Shadow Mail
        "GET /v1/mail/inbox":                 getInbox,
        "GET /v1/mail/count":                 getMailCount,
        "POST /v1/mail/send":                 sendOutbound,
      };
      const routeKey = `${req.method} ${path}`;
      const handler = authedRoutes[routeKey];

      // ── Parameterized mission routes ────────────────────────────────────────
      // POST /v1/agents/:agent_id/missions
      // GET  /v1/agents/:agent_id/missions/pending
      // POST /v1/missions/:mission_id/result
      // GET  /v1/missions/:mission_id
      // GET  /v1/missions
      const agentMissionCreate = req.method === "POST" && /^\/v1\/agents\/[^/]+\/missions$/.test(path);
      const agentMissionPending = req.method === "GET"  && /^\/v1\/agents\/[^/]+\/missions\/pending$/.test(path);
      const missionResult       = req.method === "POST" && /^\/v1\/missions\/[^/]+\/result$/.test(path);
      const missionGet          = req.method === "GET"  && /^\/v1\/missions\/[^/]+$/.test(path) && path !== "/v1/missions";
      const missionList         = req.method === "GET"  && path === "/v1/missions";
      // Shadow Mail parameterized routes
      const mailGet    = req.method === "GET"    && /^\/v1\/mail\/[^/]+$/.test(path) && path !== "/v1/mail/inbox" && path !== "/v1/mail/count";
      const mailRead   = req.method === "POST"   && /^\/v1\/mail\/[^/]+\/read$/.test(path);
      const mailReply  = req.method === "POST"   && /^\/v1\/mail\/[^/]+\/reply$/.test(path);
      const mailDelete = req.method === "DELETE" && /^\/v1\/mail\/[^/]+$/.test(path);
      // File storage
      const fileGet    = req.method === "GET"    && /^\/v1\/files\/.+/.test(path);
      const fileDelete = req.method === "DELETE" && /^\/v1\/files\/.+/.test(path);

      const isParamRoute = handler || agentMissionCreate || agentMissionPending || missionResult || missionGet || missionList || mailGet || mailRead || mailReply || mailDelete || fileGet || fileDelete;
      if (isParamRoute) {
        const key = extractKey(req);
        if (!key) return json({ error: "missing_or_invalid_key" }, { status: 401 }, cors);
        // Per-IP gate before expensive Supabase lookup (120 req/min across all authed routes)
        if (!rateLimit(`auth:${ip}`, 120, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        const user = await findUserByKey(env, key);
        if (!user) return json({ error: "key_not_found" }, { status: 401 }, cors);
        // Tighter per-user limits on expensive/sensitive operations
        // Note: POST /v1/keys/rotate is handled directly above (has its own auth+rate-limit inside handleRotate)
        if (routeKey === "POST /v1/assistant/query" && !rateLimit(`ai:${user.id}`, 20, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        if (routeKey === "POST /v1/scans" && !rateLimit(`scan:${user.id}`, 30, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        if (routeKey === "POST /v1/incidents" && !rateLimit(`inc:${user.id}`, 60, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);
        if ((agentMissionCreate || agentMissionPending) && !rateLimit(`msn:${user.id}`, 10, 60_000))
          return json({ error: "rate_limited" }, { status: 429 }, cors);

        if (handler) return handler(req, env, { id: user.id, email: user.email }, cors);

        const parts = path.split("/");
        if (agentMissionCreate)  return createMission(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (agentMissionPending) return getPendingMissions(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (missionResult)       return reportMissionResult(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (missionGet)          return getMission(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (missionList)         return listMissions(req, env, { id: user.id, email: user.email }, cors);
        // Shadow Mail
        if (mailGet)    return getMail(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (mailRead)   return markRead(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (mailReply)  return replyMail(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        if (mailDelete) return deleteMail(req, env, { id: user.id, email: user.email }, cors, parts[3]);
        // File storage — key is everything after /v1/files/
        const fileKey = path.slice("/v1/files/".length);
        if (fileGet)    return downloadFile(req, env, { id: user.id, email: user.email }, cors, fileKey);
        if (fileDelete) return deleteFile(req, env, { id: user.id, email: user.email }, cors, fileKey);
      }

      // ── WebSocket upgrade: GET /v1/chat/ws?room=<name> ─────────────────────
      if (req.method === "GET" && path === "/v1/chat/ws" && req.headers.get("Upgrade") === "websocket") {
        const key = extractKey(req);
        if (!key) return new Response("missing_or_invalid_key", { status: 401 });
        const user = await findUserByKey(env, key);
        if (!user) return new Response("key_not_found", { status: 401 });

        const url = new URL(req.url);
        const roomName = (url.searchParams.get("room") ?? "global").slice(0, 64);

        // Resolve room to get its ID
        const rooms = await dbSelect<{ id: string; name: string; display_name: string; room_type: string; team_id: string | null }>(
          env, "chat_rooms", { select: "id,name,display_name,room_type,team_id", filters: { name: `eq.${roomName}` }, limit: 1 }
        );
        if (!rooms.length) return new Response("room_not_found", { status: 404 });
        const room = rooms[0];

        // Team room access check
        if (room.room_type === "team" && room.team_id) {
          const members = await dbSelect(env, "team_members", {
            filters: { team_id: `eq.${room.team_id}`, user_id: `eq.${user.id}` }, limit: 1,
          });
          if (!members.length) return new Response("forbidden", { status: 403 });
        }

        // DM room access check (display_name format: nick1:nick2:uid1:uid2)
        if (room.room_type === "dm") {
          const parts = room.display_name.split(":");
          const [uid1, uid2] = [parts[2], parts[3]]; // UIDs are 3rd and 4th colon-delimited fields
          if (uid1 !== user.id && uid2 !== user.id) return new Response("forbidden", { status: 403 });
        }

        const nick = user.email.split("@")[0].replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 20) || "user";
        const doId = env.CHAT_ROOM.idFromName(roomName);
        const stub = env.CHAT_ROOM.get(doId);

        const doUrl = new URL(req.url);
        doUrl.searchParams.set("user_id", user.id);
        doUrl.searchParams.set("nick", nick);
        doUrl.searchParams.set("room_id", room.id);
        doUrl.searchParams.set("room", roomName);
        return stub.fetch(new Request(doUrl.toString(), req));
      }

      return json({ error: "not_found", path }, { status: 404 }, cors);
    } catch (err) {
      const message = err instanceof Error ? err.message : "unknown_error";
      console.error("[api] unhandled", message);
      return json({ error: "internal", message }, { status: 500 }, cors);
    }
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runCveMatchingCron(env));
  },

  async email(message: ForwardableEmailMessage, env: Env, ctx: ExecutionContext): Promise<void> {
    // Read raw email body (cap at 10 MB to guard against oversized messages)
    const MAX_BYTES = 10 * 1024 * 1024;
    const reader = message.raw.getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done || !value) break;
      total += value.byteLength;
      if (total > MAX_BYTES) { message.setReject("Message too large"); return; }
      chunks.push(value);
    }
    const merged = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { merged.set(chunk, offset); offset += chunk.byteLength; }
    const rawBody = new TextDecoder("utf-8").decode(merged);
    ctx.waitUntil(storeInboundMail(env, message, rawBody));
  },
};
