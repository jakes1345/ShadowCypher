/**
 * Phase 4B — notifications.
 *
 * Email via Resend (https://resend.com — 100/day free, 3000/month).
 * Web push is wired but optional: if no VAPID keys configured, push is no-op.
 *
 * Endpoints:
 *   GET  /v1/notifications/preferences
 *   POST /v1/notifications/preferences   { email_enabled, email_severity, push_enabled, push_subscription }
 *   POST /v1/notifications/test          — send a test email/push to verify
 *
 * Internal: dispatchIncidentNotification() called from guardian.createIncident()
 *
 * Secrets:
 *   RESEND_API_KEY            — re_… (from resend.com/api-keys)
 *   RESEND_FROM_EMAIL         — e.g. "ShadowCypher <alerts@yourdomain>"
 *   PUSH_VAPID_PRIVATE_KEY    — optional, base64url
 *   PUSH_VAPID_PUBLIC_KEY     — optional, base64url
 *   PUSH_VAPID_SUBJECT        — mailto: or https://...
 */

import type { Env } from "./index";
import { dbSelect, dbUpsert } from "./supabase";
import { getEffectivePlan, getLimits } from "./plans";

interface AuthedUser { id: string; email: string; }

interface NotificationPrefs {
  user_id: string;
  email_enabled: boolean;
  email_severity: "info" | "warning" | "critical";
  push_enabled: boolean;
  push_subscription: PushSubscriptionJSON | null;
}

interface PushSubscriptionJSON {
  endpoint: string;
  keys?: { p256dh: string; auth: string };
}

interface IncidentForNotify {
  id: string;
  severity: "info" | "warning" | "critical";
  category: string;
  title: string;
  detail: string | null;
  user_id: string;
}

const SEVERITY_RANK: Record<string, number> = { info: 1, warning: 2, critical: 3 };

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

// ─── Endpoints ──────────────────────────────────────────────────────────────

export async function getPreferences(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const rows = await dbSelect<NotificationPrefs>(env, "notification_prefs", {
    select: "user_id,email_enabled,email_severity,push_enabled,push_subscription",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  const prefs = rows[0] || {
    user_id: user.id,
    email_enabled: true,
    email_severity: "warning",
    push_enabled: false,
    push_subscription: null,
  };
  return json({ preferences: prefs }, {}, cors);
}

export async function updatePreferences(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const body = (await req.json().catch(() => ({}))) as Partial<NotificationPrefs>;
  const patch: Record<string, unknown> = {
    user_id: user.id,
    updated_at: new Date().toISOString(),
  };
  if (body.email_enabled !== undefined) patch.email_enabled = !!body.email_enabled;
  if (body.email_severity && ["info", "warning", "critical"].includes(body.email_severity)) {
    patch.email_severity = body.email_severity;
  }
  if (body.push_enabled !== undefined) patch.push_enabled = !!body.push_enabled;
  if (body.push_subscription !== undefined) patch.push_subscription = body.push_subscription;

  const saved = await dbUpsert<NotificationPrefs>(env, "notification_prefs", patch, "user_id");
  return json({ preferences: saved }, {}, cors);
}

export async function sendTest(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const fakeIncident: IncidentForNotify = {
    id: "test",
    severity: "warning",
    category: "test",
    title: "Test alert from ShadowCypher",
    detail: "If you got this, your notifications are wired up correctly.",
    user_id: user.id,
  };
  const result = await dispatchIncidentNotification(env, fakeIncident, user.email);
  return json({ ok: true, ...result }, {}, cors);
}

// ─── Dispatch (called from guardian.ts when an incident is created) ─────────

export async function dispatchIncidentNotification(
  env: Env,
  incident: IncidentForNotify,
  userEmail?: string
): Promise<{ email_sent: boolean; push_sent: boolean; reason?: string }> {
  // Plan gate — alerts are a Pro feature
  const profileRows = await dbSelect<{ plan: string; trial_ends_at: string | null; subscription_status: string | null; current_period_end: string | null }>(
    env, "profiles",
    {
      select: "plan,trial_ends_at,subscription_status,current_period_end",
      filters: { user_id: `eq.${incident.user_id}` },
      limit: 1,
    }
  );
  const plan = getEffectivePlan(profileRows[0]);
  if (!getLimits(plan).alertsEnabled) {
    return { email_sent: false, push_sent: false, reason: "alerts_require_pro" };
  }

  const prefRows = await dbSelect<NotificationPrefs>(env, "notification_prefs", {
    select: "email_enabled,email_severity,push_enabled,push_subscription",
    filters: { user_id: `eq.${incident.user_id}` },
    limit: 1,
  });
  const prefs = prefRows[0] || {
    user_id: incident.user_id,
    email_enabled: true,
    email_severity: "warning" as const,
    push_enabled: false,
    push_subscription: null,
  };

  let emailSent = false;
  let pushSent = false;

  // Threshold check
  const incidentRank = SEVERITY_RANK[incident.severity] ?? 1;
  const minRank = SEVERITY_RANK[prefs.email_severity] ?? 2;

  if (prefs.email_enabled && incidentRank >= minRank && userEmail && env.RESEND_API_KEY) {
    emailSent = await sendEmail(env, userEmail, incident);
  }

  if (prefs.push_enabled && prefs.push_subscription && env.PUSH_VAPID_PRIVATE_KEY) {
    pushSent = await sendWebPush(env, prefs.push_subscription, incident);
  }

  return { email_sent: emailSent, push_sent: pushSent };
}

// ─── Email via Resend ───────────────────────────────────────────────────────

async function sendEmail(env: Env, to: string, incident: IncidentForNotify): Promise<boolean> {
  if (!env.RESEND_API_KEY) return false;
  const from = env.RESEND_FROM_EMAIL || "ShadowCypher <alerts@shadowcypher.site>";
  const sevColor = { info: "#7eb6ff", warning: "#ffb84d", critical: "#ff3b6b" }[incident.severity] || "#aaa";
  const sevLabel = incident.severity.toUpperCase();

  const html = `
    <div style="font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 0 auto; background: #03030a; color: #e6e6e6; padding: 32px 24px;">
      <div style="border-left: 4px solid #b44aff; padding-left: 16px; margin-bottom: 24px;">
        <div style="font-size: 12px; letter-spacing: 3px; color: #b44aff; text-transform: uppercase; font-weight: 700;">SHADOWCYPHER · GUARDIAN</div>
        <div style="font-size: 11px; color: ${sevColor}; letter-spacing: 2px; font-weight: 700; margin-top: 6px;">${sevLabel}</div>
      </div>
      <h2 style="font-size: 20px; color: #fff; margin: 0 0 12px;">${escapeHtml(incident.title)}</h2>
      ${incident.detail ? `<p style="color: #aaa; font-size: 14px; line-height: 1.6;">${escapeHtml(incident.detail)}</p>` : ""}
      <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #222;">
        <a href="https://shadowcypher.site/?nav=account" style="display: inline-block; background: #b44aff; color: #000; padding: 12px 24px; text-decoration: none; font-weight: 700; font-size: 13px; letter-spacing: 1px;">VIEW DASHBOARD</a>
      </div>
      <p style="color: #555; font-size: 11px; margin-top: 32px;">Alert ID: ${incident.id} · Category: ${escapeHtml(incident.category)}</p>
    </div>
  `;

  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to,
        subject: `[${sevLabel}] ${incident.title}`,
        html,
      }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

// ─── Web Push (VAPID + RFC 8291 aes128gcm encryption, no library) ──────────

async function sendWebPush(
  env: Env,
  sub: PushSubscriptionJSON,
  incident: IncidentForNotify
): Promise<boolean> {
  if (!env.PUSH_VAPID_PRIVATE_KEY || !env.PUSH_VAPID_PUBLIC_KEY) return false;
  if (!sub.keys?.p256dh || !sub.keys?.auth) return false;
  try {
    const audience = new URL(sub.endpoint).origin;
    const jwt = await mintVapidJwt(env, audience);
    const payload = JSON.stringify({
      title: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      body: incident.detail || incident.category,
      severity: incident.severity,
      url: `/?nav=account&incident=${incident.id}`,
      tag: `sc-${incident.id}`,
    });
    const encrypted = await encryptWebPushPayload(sub, payload);
    const resp = await fetch(sub.endpoint, {
      method: "POST",
      headers: {
        Authorization: `vapid t=${jwt}, k=${env.PUSH_VAPID_PUBLIC_KEY}`,
        "Content-Type": "application/octet-stream",
        "Content-Encoding": "aes128gcm",
        TTL: "86400",
        Urgency: incident.severity === "critical" ? "high" : "normal",
      },
      body: encrypted,
    });
    return resp.ok || resp.status === 201;
  } catch {
    return false;
  }
}

// RFC 8291 — Message Encryption for Web Push (aes128gcm)
async function encryptWebPushPayload(sub: PushSubscriptionJSON, payload: string): Promise<Uint8Array> {
  const receiverPublicKey = b64urlDecode(sub.keys!.p256dh);  // 65-byte uncompressed P-256 point
  const authSecret = b64urlDecode(sub.keys!.auth);            // 16-byte auth secret

  // Ephemeral sender ECDH key pair
  const senderKey = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const senderPublicKeyRaw = new Uint8Array(await crypto.subtle.exportKey("raw", senderKey.publicKey));

  // ECDH shared secret (32 bytes)
  const receiverKey = await crypto.subtle.importKey("raw", receiverPublicKey, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const sharedSecret = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: receiverKey }, senderKey.privateKey, 256));

  // Random 16-byte salt
  const salt = crypto.getRandomValues(new Uint8Array(16));

  // HKDF-Extract: PRK = HMAC-SHA256(auth_secret, shared_secret)
  const hmacKey = await crypto.subtle.importKey("raw", authSecret, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const prk = new Uint8Array(await crypto.subtle.sign("HMAC", hmacKey, sharedSecret));

  // HKDF-Expand: IKM = PRK + "WebPush: info\0" || receiver_pub || sender_pub → 32 bytes
  const authInfo = wpConcat(new TextEncoder().encode("WebPush: info\x00"), receiverPublicKey, senderPublicKeyRaw);
  const ikm = await wpHkdfExpand(prk, authInfo, 32);

  // Derive CEK (16 bytes) and NONCE (12 bytes) via HKDF(salt, ikm, info)
  const cek = await wpHkdf(salt, ikm, new TextEncoder().encode("Content-Encoding: aes128gcm\x00"), 16);
  const nonce = await wpHkdf(salt, ikm, new TextEncoder().encode("Content-Encoding: nonce\x00"), 12);

  // AES-128-GCM encrypt — WebCrypto appends the 16-byte GCM tag to ciphertext
  const aesKey = await crypto.subtle.importKey("raw", cek, { name: "AES-GCM" }, false, ["encrypt"]);
  const paddedPlaintext = wpConcat(new TextEncoder().encode(payload), new Uint8Array([0x02]));
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce, tagLength: 128 }, aesKey, paddedPlaintext));

  // RFC 8188 aes128gcm content: salt(16) | rs(4 BE) | idlen(1) | sender_pub(65) | ciphertext
  const rs = 4096;
  return wpConcat(
    salt,
    new Uint8Array([(rs >> 24) & 0xff, (rs >> 16) & 0xff, (rs >> 8) & 0xff, rs & 0xff]),
    new Uint8Array([senderPublicKeyRaw.length]),
    senderPublicKeyRaw,
    ciphertext
  );
}

// HKDF-Expand T(1) = HMAC-SHA256(PRK, info || 0x01) — sufficient for L ≤ 32
async function wpHkdfExpand(prk: Uint8Array, info: Uint8Array, length: number): Promise<Uint8Array> {
  const k = await crypto.subtle.importKey("raw", prk, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", k, wpConcat(info, new Uint8Array([1])))).slice(0, length);
}

// Full HKDF (extract + expand) via WebCrypto built-in
async function wpHkdf(salt: Uint8Array, ikm: Uint8Array, info: Uint8Array, length: number): Promise<Uint8Array> {
  const k = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info } as HkdfParams, k, length * 8));
}

function wpConcat(...arrays: Uint8Array[]): Uint8Array {
  let len = 0; for (const a of arrays) len += a.length;
  const out = new Uint8Array(len); let off = 0;
  for (const a of arrays) { out.set(a, off); off += a.length; }
  return out;
}

async function mintVapidJwt(env: Env, audience: string): Promise<string> {
  const header = { alg: "ES256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    aud: audience,
    exp: now + 12 * 60 * 60,
    sub: env.PUSH_VAPID_SUBJECT || "mailto:alerts@shadowcypher.site",
  };
  const toB64Url = (obj: unknown) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const signingInput = `${toB64Url(header)}.${toB64Url(payload)}`;
  const keyBytes = b64urlDecode(env.PUSH_VAPID_PRIVATE_KEY);
  const key = await crypto.subtle.importKey(
    "pkcs8",
    keyBytes,
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["sign"]
  );
  const sig = new Uint8Array(
    await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, new TextEncoder().encode(signingInput))
  );
  return `${signingInput}.${b64urlEncode(sig)}`;
}

function b64urlDecode(s: string): Uint8Array {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const bin = atob(s);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function b64urlEncode(b: Uint8Array): string {
  let s = "";
  for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));
}
