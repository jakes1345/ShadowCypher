/**
 * Thin Supabase REST helper for Cloudflare Workers.
 * Uses PostgREST endpoints under /rest/v1/ with the service_role key (bypasses RLS).
 * Keeps our dependency footprint at zero and avoids the Node-targeted supabase-js client.
 */

import type { Env } from "./index";

interface QueryOptions {
  select?: string;
  filters?: Record<string, string>; // e.g. { user_id: "eq.<uuid>" }
  order?: string;                   // e.g. "created_at.desc"
  limit?: number;
  offset?: number;
  single?: boolean;
}

function buildUrl(env: Env, table: string, opts: QueryOptions = {}): string {
  const url = new URL(`${env.SUPABASE_URL}/rest/v1/${table}`);
  if (opts.select) url.searchParams.set("select", opts.select);
  if (opts.order) url.searchParams.set("order", opts.order);
  if (opts.limit !== undefined) url.searchParams.set("limit", String(opts.limit));
  if (opts.offset !== undefined) url.searchParams.set("offset", String(opts.offset));
  if (opts.filters) {
    for (const [k, v] of Object.entries(opts.filters)) {
      url.searchParams.set(k, v);
    }
  }
  return url.toString();
}

function authHeaders(env: Env, prefer?: string): HeadersInit {
  const h: Record<string, string> = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
  };
  if (prefer) h["Prefer"] = prefer;
  return h;
}

export async function dbSelect<T = unknown>(env: Env, table: string, opts: QueryOptions = {}): Promise<T[]> {
  const url = buildUrl(env, table, opts);
  const headers = authHeaders(env, opts.single ? "return=representation" : undefined);
  const resp = await fetch(url, { headers });
  if (!resp.ok) throw new Error(`db_select_failed:${table}:${resp.status}:${await resp.text()}`);
  return (await resp.json()) as T[];
}

export async function dbInsert<T = unknown>(env: Env, table: string, row: Record<string, unknown>): Promise<T> {
  const url = `${env.SUPABASE_URL}/rest/v1/${table}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: authHeaders(env, "return=representation"),
    body: JSON.stringify(row),
  });
  if (!resp.ok) throw new Error(`db_insert_failed:${table}:${resp.status}:${await resp.text()}`);
  const rows = (await resp.json()) as T[];
  return rows[0];
}

export async function dbUpsert<T = unknown>(
  env: Env,
  table: string,
  row: Record<string, unknown>,
  onConflict: string
): Promise<T> {
  const url = `${env.SUPABASE_URL}/rest/v1/${table}?on_conflict=${encodeURIComponent(onConflict)}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: authHeaders(env, "return=representation,resolution=merge-duplicates"),
    body: JSON.stringify(row),
  });
  if (!resp.ok) throw new Error(`db_upsert_failed:${table}:${resp.status}:${await resp.text()}`);
  const rows = (await resp.json()) as T[];
  return rows[0];
}

export async function dbUpdate<T = unknown>(
  env: Env,
  table: string,
  filters: Record<string, string>,
  patch: Record<string, unknown>
): Promise<T[]> {
  const url = buildUrl(env, table, { filters });
  const resp = await fetch(url, {
    method: "PATCH",
    headers: authHeaders(env, "return=representation"),
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`db_update_failed:${table}:${resp.status}:${await resp.text()}`);
  return (await resp.json()) as T[];
}
