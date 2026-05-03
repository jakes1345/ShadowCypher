/**
 * Phase 4 — account utility endpoints (export, usage stats).
 *
 *   GET /v1/me/export   — JSON bundle of all the user's data (GDPR portability)
 *   GET /v1/me/stats    — usage analytics for dashboard
 */

import type { Env } from "./index";
import { dbSelect } from "./supabase";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body, null, 2), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

export async function exportData(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const filters = { user_id: `eq.${user.id}` };
  const [profile, agents, devices, scans, incidents, prefs, webhooks] = await Promise.all([
    dbSelect<unknown>(env, "profiles", { select: "*", filters, limit: 1 }),
    dbSelect<unknown>(env, "agents", { select: "*", filters, limit: 1000 }),
    dbSelect<unknown>(env, "devices", { select: "*", filters, limit: 5000 }),
    dbSelect<unknown>(env, "scans", { select: "*", filters, limit: 5000 }),
    dbSelect<unknown>(env, "incidents", { select: "*", filters, limit: 5000 }),
    dbSelect<unknown>(env, "notification_prefs", { select: "*", filters, limit: 1 }),
    dbSelect<unknown>(env, "webhooks", { select: "id,url,label,events,min_severity,is_active,created_at", filters, limit: 100 }),
  ]);

  const bundle = {
    exported_at: new Date().toISOString(),
    user: { id: user.id, email: user.email },
    profile: profile[0] ?? null,
    agents,
    devices,
    scans,
    incidents,
    notification_prefs: prefs[0] ?? null,
    webhooks,
    counts: {
      agents: agents.length,
      devices: devices.length,
      scans: scans.length,
      incidents: incidents.length,
      webhooks: webhooks.length,
    },
  };

  return new Response(JSON.stringify(bundle, null, 2), {
    headers: {
      "Content-Type": "application/json",
      "Content-Disposition": `attachment; filename="shadowcypher-export-${user.id.slice(0, 8)}-${Date.now()}.json"`,
      ...cors,
    },
  });
}

export async function getStats(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const filters = { user_id: `eq.${user.id}` };
  // Postgrest: use exact count via header
  const countHeader = async (table: string, extra: Record<string, string> = {}): Promise<number> => {
    const url = new URL(`${env.SUPABASE_URL}/rest/v1/${table}`);
    url.searchParams.set("select", "id");
    url.searchParams.set("user_id", `eq.${user.id}`);
    for (const [k, v] of Object.entries(extra)) url.searchParams.set(k, v);
    const resp = await fetch(url.toString(), {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        Prefer: "count=exact",
        Range: "0-0",
      },
    });
    const cr = resp.headers.get("content-range") || "";
    const m = cr.match(/\/(\d+)$/);
    return m ? parseInt(m[1], 10) : 0;
  };

  const [agents, devices, scans, incidents, openIncidents] = await Promise.all([
    countHeader("agents"),
    countHeader("devices"),
    countHeader("scans"),
    countHeader("incidents"),
    countHeader("incidents", { acknowledged: "eq.false" }),
  ]);

  // Last 30 days
  const since = new Date(Date.now() - 30 * 86400000).toISOString();
  const recent30 = await dbSelect<{ started_at: string; device_count: number | null }>(env, "scans", {
    select: "started_at,device_count",
    filters: { user_id: `eq.${user.id}`, started_at: `gte.${since}` },
    limit: 5000,
  });

  // Earliest activity
  const earliestRows = await dbSelect<{ created_at: string }>(env, "profiles", {
    select: "created_at",
    filters,
    limit: 1,
  });
  const memberSince = earliestRows[0]?.created_at || null;

  return json(
    {
      counts: { agents, devices, scans, incidents, open_incidents: openIncidents },
      last_30_days: {
        scans: recent30.length,
        peak_devices: recent30.reduce((m, s) => Math.max(m, s.device_count || 0), 0),
      },
      member_since: memberSince,
    },
    {},
    cors
  );
}
