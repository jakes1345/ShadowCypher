/**
 * Phase 4G — Outbound webhooks for Pro users.
 *
 * Lets users register URLs (Slack, Discord, PagerDuty, custom) that fire on incidents.
 * HMAC-SHA256 signed with a per-webhook secret so receivers can verify authenticity.
 *
 * Endpoints:
 *   POST   /v1/webhooks          — create
 *   GET    /v1/webhooks          — list mine
 *   POST   /v1/webhooks/delete   — { id }
 *   POST   /v1/webhooks/test     — { id } send a synthetic incident
 *
 * Internal: dispatchIncidentWebhook() called from guardian.createIncident()
 *
 * Plan gate: webhooks are Pro+ feature.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate } from "./supabase";
import { getEffectivePlan, planRequired, type ProfileForPlan } from "./plans";

interface AuthedUser { id: string; email: string; }

interface WebhookRow {
  id: string;
  user_id: string;
  url: string;
  label: string | null;
  events: string[];
  min_severity: "info" | "warning" | "critical";
  signing_secret: string;
  is_active: boolean;
  last_called_at: string | null;
  last_status: number | null;
  failure_count: number;
  created_at: string;
}

const SEVERITY_RANK: Record<string, number> = { info: 1, warning: 2, critical: 3 };
const ALLOWED_EVENTS = new Set(["incident.created", "incident.acknowledged", "scan.completed", "cve.matched"]);

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

function generateSecret(): string {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return "whsec_" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function getProfilePlan(env: Env, userId: string): Promise<"community" | "guardian_pro" | "operator"> {
  const rows = await dbSelect<ProfileForPlan>(env, "profiles", {
    select: "plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return getEffectivePlan(rows[0]);
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

export async function createWebhook(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const plan = await getProfilePlan(env, user.id);
  if (plan === "community") return planRequired(["guardian_pro", "operator"], plan, "Webhooks require Pro.", cors);

  const body = (await req.json().catch(() => ({}))) as {
    url?: string;
    label?: string;
    events?: string[];
    min_severity?: "info" | "warning" | "critical";
  };
  if (!body.url || !/^https:\/\//.test(body.url)) {
    return json({ error: "https_url_required" }, { status: 400 }, cors);
  }
  // Block obvious private hosts (SSRF prevention)
  try {
    const u = new URL(body.url);
    const blocked = /^(localhost|127\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.|192\.168\.|169\.254\.)/i;
    if (blocked.test(u.hostname)) return json({ error: "private_host_not_allowed" }, { status: 400 }, cors);
  } catch {
    return json({ error: "invalid_url" }, { status: 400 }, cors);
  }
  const events = (body.events || ["incident.created"]).filter((e) => ALLOWED_EVENTS.has(e));
  if (!events.length) return json({ error: "no_valid_events" }, { status: 400 }, cors);
  const min_severity = ["info", "warning", "critical"].includes(body.min_severity || "")
    ? body.min_severity
    : "warning";

  const wh = await dbInsert<WebhookRow>(env, "webhooks", {
    user_id: user.id,
    url: body.url,
    label: body.label?.slice(0, 64) ?? null,
    events,
    min_severity,
    signing_secret: generateSecret(),
    is_active: true,
  });
  return json({ id: wh.id, label: wh.label, signing_secret: wh.signing_secret, events: wh.events }, {}, cors);
}

export async function listWebhooks(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const rows = await dbSelect<WebhookRow>(env, "webhooks", {
    select: "id,url,label,events,min_severity,is_active,last_called_at,last_status,failure_count,created_at",
    filters: { user_id: `eq.${user.id}` },
    order: "created_at.desc",
    limit: 50,
  });
  return json({ webhooks: rows }, {}, cors);
}

export async function deleteWebhook(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { id?: string };
  if (!body.id) return json({ error: "id_required" }, { status: 400 }, cors);

  await dbUpdate(env, "webhooks", { id: `eq.${body.id}`, user_id: `eq.${user.id}` }, { is_active: false });
  return json({ deleted: true }, {}, cors);
}

export async function testWebhook(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { id?: string };
  if (!body.id) return json({ error: "id_required" }, { status: 400 }, cors);

  const rows = await dbSelect<WebhookRow>(env, "webhooks", {
    select: "*",
    filters: { id: `eq.${body.id}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!rows[0]) return json({ error: "not_found" }, { status: 404 }, cors);

  const synthetic = {
    id: "test-incident",
    severity: "warning" as const,
    category: "test",
    title: "Test webhook from ShadowCypher",
    detail: "If you received this, the webhook is wired correctly.",
    user_id: user.id,
  };
  const result = await deliverOne(env, rows[0], synthetic);
  return json(result, {}, cors);
}

// ─── Dispatch (called from guardian.createIncident) ─────────────────────────

interface IncidentForWebhook {
  id: string;
  severity: "info" | "warning" | "critical";
  category: string;
  title: string;
  detail: string | null;
  user_id: string;
}

export async function dispatchIncidentWebhook(env: Env, incident: IncidentForWebhook): Promise<{ delivered: number }> {
  const plan = await getProfilePlan(env, incident.user_id);
  if (plan === "community") return { delivered: 0 };

  const rows = await dbSelect<WebhookRow>(env, "webhooks", {
    select: "*",
    filters: { user_id: `eq.${incident.user_id}`, is_active: `eq.true` },
    limit: 20,
  });

  const incidentRank = SEVERITY_RANK[incident.severity] ?? 1;
  let delivered = 0;
  for (const wh of rows) {
    if (!wh.events.includes("incident.created")) continue;
    if (incidentRank < (SEVERITY_RANK[wh.min_severity] ?? 2)) continue;
    const result = await deliverOne(env, wh, incident);
    if (result.ok) delivered++;
  }
  return { delivered };
}

async function deliverOne(env: Env, wh: WebhookRow, incident: IncidentForWebhook): Promise<{ ok: boolean; status: number; reason?: string }> {
  const isSlack       = /hooks\.slack\.com\//.test(wh.url);
  const isDiscord     = /discord(?:app)?\.com\/api\/webhooks\//.test(wh.url);
  const isSplunk      = /\/services\/collector/.test(wh.url);
  const isDatadog     = /datadoghq\.com/.test(wh.url);
  const isConnectWise = /connectwise/i.test(wh.url);
  const isPagerDuty   = /events\.pagerduty\.com/.test(wh.url);
  const isOpsGenie    = /api\.opsgenie\.com/.test(wh.url);

  let body: string;
  let contentType = "application/json";

  if (isSlack) {
    body = JSON.stringify({
      text: `*[${incident.severity.toUpperCase()}]* ${incident.title}`,
      attachments: [{
        color: incident.severity === "critical" ? "#ff3b6b" : incident.severity === "warning" ? "#ffb84d" : "#7eb6ff",
        text: incident.detail || incident.category,
        footer: "ShadowCypher",
        ts: Math.floor(Date.now() / 1000),
      }],
    });
  } else if (isDiscord) {
    body = JSON.stringify({
      embeds: [{
        title: `[${incident.severity.toUpperCase()}] ${incident.title}`,
        description: incident.detail || incident.category,
        color: incident.severity === "critical" ? 0xff3b6b : incident.severity === "warning" ? 0xffb84d : 0x7eb6ff,
        footer: { text: "ShadowCypher" },
        timestamp: new Date().toISOString(),
      }],
    });
  } else if (isSplunk) {
    body = JSON.stringify({
      time: Date.now() / 1000,
      source: "shadowcypher",
      sourcetype: "security_alert",
      index: "main",
      event: {
        id: incident.id,
        severity: incident.severity,
        category: incident.category,
        title: incident.title,
        detail: incident.detail,
      },
    });
  } else if (isDatadog) {
    const alertType = incident.severity === "critical" ? "error" : incident.severity === "warning" ? "warning" : "info";
    body = JSON.stringify({
      title: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      text: `%%% \n**Category:** ${incident.category}\n**Detail:** ${incident.detail || "—"}\n %%%`,
      alert_type: alertType,
      source_type_name: "ShadowCypher",
      tags: [`severity:${incident.severity}`, `category:${incident.category}`, "source:shadowcypher"],
    });
  } else if (isConnectWise) {
    const priority = incident.severity === "critical" ? "High" : incident.severity === "warning" ? "Medium" : "Low";
    body = JSON.stringify({
      summary: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      initialDescription: `Severity: ${incident.severity.toUpperCase()}\nCategory: ${incident.category}\n\n${incident.detail || ""}`,
      board: { name: "ShadowCypher" },
      priority: { name: priority },
      status: { name: "New" },
    });
  } else if (isPagerDuty) {
    const pdSeverity = incident.severity === "critical" ? "critical" : incident.severity === "warning" ? "warning" : "info";
    body = JSON.stringify({
      routing_key: new URL(wh.url).searchParams.get("routing_key") || "",
      event_action: "trigger",
      payload: {
        summary: `[${incident.severity.toUpperCase()}] ${incident.title}`,
        severity: pdSeverity,
        source: "ShadowCypher",
        custom_details: {
          category: incident.category,
          detail: incident.detail,
          incident_id: incident.id,
        },
      },
      client: "ShadowCypher",
    });
  } else if (isOpsGenie) {
    const ogPriority = incident.severity === "critical" ? "P1" : incident.severity === "warning" ? "P2" : "P3";
    body = JSON.stringify({
      message: `[${incident.severity.toUpperCase()}] ${incident.title}`,
      description: `Category: ${incident.category}\n\n${incident.detail || ""}`,
      priority: ogPriority,
      source: "ShadowCypher",
      tags: [incident.severity, incident.category, "shadowcypher"],
      details: { incident_id: incident.id },
    });
  } else {
    body = JSON.stringify({
      event: "incident.created",
      timestamp: new Date().toISOString(),
      incident: {
        id: incident.id,
        severity: incident.severity,
        category: incident.category,
        title: incident.title,
        detail: incident.detail,
      },
    });
  }

  const signature = await hmacSha256(wh.signing_secret, body);
  try {
    const resp = await fetch(wh.url, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
        "User-Agent": "ShadowCypher-Webhook/1.0",
        "X-ShadowCypher-Signature": `sha256=${signature}`,
        "X-ShadowCypher-Event": "incident.created",
        "X-ShadowCypher-Delivery": incident.id,
      },
      body,
      signal: AbortSignal.timeout(8000),
    });
    const ok = resp.ok;
    dbUpdate(env, "webhooks",
      { id: `eq.${wh.id}` },
      {
        last_called_at: new Date().toISOString(),
        last_status: resp.status,
        failure_count: ok ? 0 : (wh.failure_count ?? 0) + 1,
      }
    ).catch(() => null);
    return { ok, status: resp.status };
  } catch (e) {
    return { ok: false, status: 0, reason: e instanceof Error ? e.message : "unknown" };
  }
}

async function hmacSha256(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload)));
  return Array.from(sig, (b) => b.toString(16).padStart(2, "0")).join("");
}

// ─── CVE webhook dispatch ────────────────────────────────────────────────────

export interface CveMatchPayload {
  cve_id: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE";
  cvss: number | null;
  description: string;
  cve_url: string;
  device_id: string;
  device_name: string;
  device_ip: string;
  matched_on: string[];
}

export async function dispatchCveWebhook(
  env: Env,
  userId: string,
  payload: CveMatchPayload
): Promise<{ delivered: number }> {
  const plan = await getProfilePlan(env, userId);
  if (plan === "community") return { delivered: 0 };

  const rows = await dbSelect<WebhookRow>(env, "webhooks", {
    select: "*",
    filters: { user_id: `eq.${userId}`, is_active: `eq.true` },
    limit: 20,
  });

  const severityMap: Record<string, number> = { CRITICAL: 3, HIGH: 2, MEDIUM: 1, LOW: 0, NONE: 0 };
  let delivered = 0;
  for (const wh of rows) {
    if (!wh.events.includes("cve.matched")) continue;
    const minRank = SEVERITY_RANK[wh.min_severity] ?? 2;
    if ((severityMap[payload.severity] ?? 0) < minRank) continue;
    const result = await deliverCveOne(env, wh, payload);
    if (result.ok) delivered++;
  }
  return { delivered };
}

async function deliverCveOne(
  env: Env,
  wh: WebhookRow,
  payload: CveMatchPayload
): Promise<{ ok: boolean; status: number }> {
  const isSlack       = /hooks\.slack\.com\//.test(wh.url);
  const isDiscord     = /discord(?:app)?\.com\/api\/webhooks\//.test(wh.url);
  const isSplunk      = /\/services\/collector/.test(wh.url);
  const isDatadog     = /datadoghq\.com/.test(wh.url);
  const isConnectWise = /connectwise/i.test(wh.url);
  const isPagerDuty   = /events\.pagerduty\.com/.test(wh.url);
  const isOpsGenie    = /api\.opsgenie\.com/.test(wh.url);

  const title = `[${payload.severity}] ${payload.cve_id} affects ${payload.device_name}`;
  const text = `${payload.description}\nDevice: ${payload.device_ip} | Matched on: ${payload.matched_on.join(", ")}\n${payload.cve_url}`;
  const color = payload.severity === "CRITICAL" ? "#ff3b6b" : "#ffb84d";

  let body: string;
  if (isSlack) {
    body = JSON.stringify({
      text: `*${title}*`,
      attachments: [{ color, text, footer: "ShadowCypher CVE Alert", ts: Math.floor(Date.now() / 1000) }],
    });
  } else if (isDiscord) {
    body = JSON.stringify({
      embeds: [{
        title,
        description: text,
        color: payload.severity === "CRITICAL" ? 0xff3b6b : 0xffb84d,
        footer: { text: "ShadowCypher CVE Alert" },
        timestamp: new Date().toISOString(),
      }],
    });
  } else if (isSplunk) {
    body = JSON.stringify({
      time: Date.now() / 1000,
      source: "shadowcypher",
      sourcetype: "cve_alert",
      index: "main",
      event: {
        cve_id: payload.cve_id,
        severity: payload.severity,
        cvss: payload.cvss,
        description: payload.description,
        device_ip: payload.device_ip,
        device_name: payload.device_name,
        matched_on: payload.matched_on,
        cve_url: payload.cve_url,
      },
    });
  } else if (isDatadog) {
    const alertType = payload.severity === "CRITICAL" ? "error" : "warning";
    body = JSON.stringify({
      title,
      text: `%%% \n${text}\n %%%`,
      alert_type: alertType,
      source_type_name: "ShadowCypher",
      tags: [`severity:${payload.severity.toLowerCase()}`, `cve:${payload.cve_id}`, "source:shadowcypher"],
    });
  } else if (isConnectWise) {
    const priority = payload.severity === "CRITICAL" ? "High" : "Medium";
    body = JSON.stringify({
      summary: title,
      initialDescription: text,
      board: { name: "ShadowCypher" },
      priority: { name: priority },
      status: { name: "New" },
    });
  } else if (isPagerDuty) {
    const pdSeverity = payload.severity === "CRITICAL" ? "critical" : "warning";
    body = JSON.stringify({
      routing_key: new URL(wh.url).searchParams.get("routing_key") || "",
      event_action: "trigger",
      payload: {
        summary: title,
        severity: pdSeverity,
        source: "ShadowCypher",
        custom_details: {
          cve_id: payload.cve_id,
          cvss: payload.cvss,
          device_ip: payload.device_ip,
          device_name: payload.device_name,
          matched_on: payload.matched_on,
          cve_url: payload.cve_url,
        },
      },
      client: "ShadowCypher",
    });
  } else if (isOpsGenie) {
    const ogPriority = payload.severity === "CRITICAL" ? "P1" : "P2";
    body = JSON.stringify({
      message: title,
      description: text,
      priority: ogPriority,
      source: "ShadowCypher",
      tags: [payload.severity.toLowerCase(), payload.cve_id, "shadowcypher"],
      details: { cvss: String(payload.cvss ?? ""), cve_url: payload.cve_url },
    });
  } else {
    const canonical = JSON.stringify({ event: "cve.matched", fired_at: new Date().toISOString(), data: payload });
    const signature = await hmacSha256(wh.signing_secret, canonical);
    try {
      const resp = await fetch(wh.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Agent": "ShadowCypher-Webhook/1.0",
          "X-ShadowCypher-Signature": `sha256=${signature}`,
          "X-ShadowCypher-Event": "cve.matched",
        },
        body: canonical,
        signal: AbortSignal.timeout(8000),
      });
      const ok = resp.ok || resp.status === 204;
      dbUpdate(env, "webhooks", { id: `eq.${wh.id}` }, {
        last_called_at: new Date().toISOString(),
        last_status: resp.status,
        failure_count: ok ? 0 : (wh.failure_count ?? 0) + 1,
      }).catch(() => null);
      return { ok, status: resp.status };
    } catch {
      return { ok: false, status: 0 };
    }
  }

  try {
    const resp = await fetch(wh.url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "User-Agent": "ShadowCypher-Webhook/1.0" },
      body,
      signal: AbortSignal.timeout(8000),
    });
    const ok = resp.ok || resp.status === 204;
    dbUpdate(env, "webhooks", { id: `eq.${wh.id}` }, {
      last_called_at: new Date().toISOString(),
      last_status: resp.status,
      failure_count: ok ? 0 : (wh.failure_count ?? 0) + 1,
    }).catch(() => null);
    return { ok, status: resp.status };
  } catch {
    return { ok: false, status: 0 };
  }
}
