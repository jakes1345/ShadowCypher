/**
 * Account utility endpoints (export, usage stats).
 *
 *   GET /v1/me/export   — JSON bundle of everything stored for the user (GDPR portability)
 *   GET /v1/me/stats    — usage analytics for dashboard
 */

import type { Env } from "./index";
import { dbSelect, dbSelectAll } from "./supabase";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body, null, 2), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

/** A table of the user's rows: how to find them and a unique column to page by. */
interface Collection {
  key: string;
  table: string;
  filters: (id: string) => Record<string, string>;
  order: string;
  select?: string;
}

const owned = (id: string) => ({ user_id: `eq.${id}` });

/**
 * Every table that holds rows for a user. Secrets the user never chose are
 * left out (webhook signing secrets, pending device-login codes); everything
 * else is exported as stored.
 */
const COLLECTIONS: Collection[] = [
  { key: "agents", table: "agents", filters: owned, order: "id.asc" },
  { key: "devices", table: "devices", filters: owned, order: "id.asc" },
  { key: "scans", table: "scans", filters: owned, order: "id.asc" },
  { key: "incidents", table: "incidents", filters: owned, order: "id.asc" },
  { key: "cve_alerts", table: "cve_alerts_sent", filters: owned, order: "id.asc" },
  { key: "missions", table: "missions", filters: owned, order: "id.asc" },
  { key: "mail", table: "mail_messages", filters: owned, order: "id.asc" },
  { key: "chat_messages", table: "chat_messages", filters: owned, order: "id.asc" },
  { key: "chat_reactions", table: "chat_reactions", filters: owned, order: "message_id.asc,emoji.asc" },
  { key: "chat_presence", table: "chat_presence", filters: owned, order: "room_id.asc" },
  { key: "chat_read_receipts", table: "dm_read_receipts", filters: owned, order: "room_id.asc" },
  { key: "chat_rooms_created", table: "chat_rooms", filters: (id) => ({ created_by: `eq.${id}` }), order: "id.asc" },
  { key: "calendar_events", table: "calendar_events", filters: owned, order: "id.asc" },
  { key: "teams_owned", table: "teams", filters: (id) => ({ owner_id: `eq.${id}` }), order: "id.asc" },
  { key: "team_memberships", table: "team_members", filters: owned, order: "team_id.asc" },
  {
    key: "referrals", table: "referral_redemptions", order: "id.asc",
    filters: (id) => ({ or: `(referrer_id.eq.${id},referee_id.eq.${id})` }),
  },
  { key: "audit_log", table: "audit_log", filters: owned, order: "id.asc" },
  {
    key: "webhooks", table: "webhooks", filters: owned, order: "id.asc",
    select: "id,url,label,events,min_severity,is_active,last_called_at,last_status,failure_count,created_at",
  },
  {
    key: "device_logins", table: "device_auth_codes", filters: owned, order: "device_code.asc",
    select: "client_label,status,created_at,authorized_at,consumed_at,expires_at",
  },
];

/** One-row-per-user tables. */
const SINGLETONS: { key: string; table: string }[] = [
  { key: "profile", table: "profiles" },
  { key: "public_profile", table: "user_profiles" },
  { key: "notification_prefs", table: "notification_prefs" },
  { key: "identity_keys", table: "user_keys" },
];

interface StoredObject {
  key: string;
  name: string;
  size: number;
  updated_at: string | null;
  /** API path that returns the content, with the same API key. */
  download: string;
}

/** Lists the user's uploads, docs and sheets in R2, with the route that serves each one. */
async function listStoredObjects(env: Env, userId: string) {
  const out: { files: StoredObject[]; docs: StoredObject[]; sheets: StoredObject[] } = { files: [], docs: [], sheets: [] };
  if (!env.SHADOW_FILES) return out;
  let cursor: string | undefined;
  do {
    const page = await env.SHADOW_FILES.list({ prefix: `${userId}/`, cursor, limit: 1000, include: ["customMetadata"] });
    for (const obj of page.objects) {
      const rest = obj.key.slice(userId.length + 1);
      const meta = obj.customMetadata ?? {};
      const base = { key: obj.key, size: obj.size, updated_at: meta.updated_at ?? meta.uploaded_at ?? obj.uploaded?.toISOString() ?? null };
      const doc = rest.match(/^docs\/([^/]+)\.html$/);
      const sheet = rest.match(/^sheets\/([^/]+)\.json$/);
      if (doc) out.docs.push({ ...base, name: meta.title ?? "Untitled", download: `/v1/docs/${doc[1]}` });
      else if (sheet) out.sheets.push({ ...base, name: meta.title ?? "Untitled Sheet", download: `/v1/sheets/${sheet[1]}` });
      else out.files.push({ ...base, name: meta.original_name ?? rest, download: `/v1/files/${obj.key}` });
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return out;
}

/**
 * Builds the export bundle. A collection that cannot be read, or that is too
 * large to return whole, is named in `incomplete` so the export never passes
 * off a partial copy as the full one.
 */
export async function buildExport(env: Env, user: AuthedUser): Promise<Record<string, unknown>> {
  const incomplete: string[] = [];
  const bundle: Record<string, unknown> = {
    exported_at: new Date().toISOString(),
    user: { id: user.id, email: user.email },
  };

  await Promise.all(SINGLETONS.map(async ({ key, table }) => {
    try {
      const rows = await dbSelect<unknown>(env, table, { select: "*", filters: owned(user.id), limit: 1 });
      bundle[key] = rows[0] ?? null;
    } catch {
      bundle[key] = null;
      incomplete.push(key);
    }
  }));

  const counts: Record<string, number> = {};
  await Promise.all(COLLECTIONS.map(async (c) => {
    try {
      const { rows, truncated } = await dbSelectAll<unknown>(env, c.table, {
        select: c.select ?? "*",
        filters: c.filters(user.id),
        order: c.order,
      });
      bundle[c.key] = rows;
      counts[c.key] = rows.length;
      if (truncated) incomplete.push(c.key);
    } catch {
      bundle[c.key] = [];
      counts[c.key] = 0;
      incomplete.push(c.key);
    }
  }));

  try {
    const stored = await listStoredObjects(env, user.id);
    bundle.files = stored.files;
    bundle.docs = stored.docs;
    bundle.sheets = stored.sheets;
    counts.files = stored.files.length;
    counts.docs = stored.docs.length;
    counts.sheets = stored.sheets.length;
  } catch {
    bundle.files = [];
    bundle.docs = [];
    bundle.sheets = [];
    incomplete.push("files", "docs", "sheets");
  }

  bundle.counts = counts;
  bundle.incomplete = incomplete.sort();
  return bundle;
}

export async function exportData(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const bundle = await buildExport(env, user);
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
