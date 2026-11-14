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

export interface AuthUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
}

const USER_PAGE = 50;
const USER_MAX_PAGES = 20;

/**
 * Finds the auth user with exactly this email, or null.
 * GoTrue's list endpoint has no `email` parameter (it is silently ignored and
 * returns every user); `filter` is a substring match, so the result is
 * re-checked for an exact match rather than trusting the first row.
 */
export async function findAuthUserByEmail(env: Env, email: string): Promise<AuthUser | null> {
  return lookupAuthUserByEmail(env, email).catch(() => null);
}

/** Like findAuthUserByEmail, but throws when the auth API fails instead of reporting "not found". */
export async function lookupAuthUserByEmail(env: Env, email: string): Promise<AuthUser | null> {
  const want = email.trim().toLowerCase();
  for (let page = 1; page <= USER_MAX_PAGES; page++) {
    const url = `${env.SUPABASE_URL}/auth/v1/admin/users?filter=${encodeURIComponent(want)}&per_page=${USER_PAGE}&page=${page}`;
    const resp = await fetch(url, { headers: authHeaders(env) });
    if (!resp.ok) throw new Error(`auth_lookup_failed:${resp.status}`);
    const users = ((await resp.json()) as { users?: AuthUser[] }).users ?? [];
    const match = users.find((u) => u.email?.toLowerCase() === want);
    if (match) return match;
    if (users.length < USER_PAGE) return null;
  }
  return null;
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

export async function dbCount(env: Env, table: string, filters: Record<string, string> = {}): Promise<number> {
  const url = buildUrl(env, table, { filters, select: "id", limit: 1 });
  const headers = {
    ...authHeaders(env, "count=exact"),
    "Range-Unit": "items",
    "Range": "0-0",
  } as Record<string, string>;
  const resp = await fetch(url, { headers });
  const range = resp.headers.get("Content-Range"); // "0-0/1234" or "*/0"
  if (!range) return 0;
  const total = range.split("/")[1];
  return total && total !== "*" ? parseInt(total, 10) : 0;
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

/**
 * Deletes the rows matching `filters` and returns how many went.
 * Refuses to run without a filter, so a caller can never empty a table by accident.
 * A table that does not exist counts as nothing to delete: self-hosted
 * databases may not have every optional table.
 */
export async function dbDelete(env: Env, table: string, filters: Record<string, string>): Promise<number> {
  if (Object.keys(filters).length === 0) throw new Error(`db_delete_unfiltered:${table}`);
  const resp = await fetch(buildUrl(env, table, { filters }), {
    method: "DELETE",
    headers: authHeaders(env, "count=exact,return=minimal"),
  });
  if (resp.status === 404) return 0;
  if (!resp.ok) throw new Error(`db_delete_failed:${table}:${resp.status}:${await resp.text()}`);
  const total = resp.headers.get("Content-Range")?.split("/")[1]; // "*/12"
  return total && total !== "*" ? parseInt(total, 10) : 0;
}

const SELECT_PAGE = 1000; // PostgREST's default row cap per request

/**
 * Reads every row matching the query, one page at a time.
 * `order` must name a unique column so pages neither overlap nor skip rows.
 * Stops at `maxRows` and reports `truncated` instead of returning a silent partial set.
 */
export async function dbSelectAll<T = unknown>(
  env: Env,
  table: string,
  opts: { select?: string; filters?: Record<string, string>; order: string; maxRows?: number },
): Promise<{ rows: T[]; truncated: boolean }> {
  const maxRows = opts.maxRows ?? 100_000;
  const rows: T[] = [];
  for (let offset = 0; offset < maxRows; offset += SELECT_PAGE) {
    const page = await dbSelect<T>(env, table, {
      select: opts.select,
      filters: opts.filters,
      order: opts.order,
      limit: Math.min(SELECT_PAGE, maxRows - offset),
      offset,
    });
    rows.push(...page);
    if (page.length < SELECT_PAGE) return { rows, truncated: false };
  }
  return { rows, truncated: true };
}
