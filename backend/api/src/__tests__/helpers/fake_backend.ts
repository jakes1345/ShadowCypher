/**
 * In-memory stand-ins for the services the Worker talks to, for tests that
 * need to see what was read and what was removed: PostgREST and the auth admin
 * API on Supabase, Stripe's customer endpoint, and an R2 bucket.
 */
import type { Env } from "../../index";

export type Row = Record<string, unknown>;

const SUPABASE = "https://db.example";

function matches(row: Row, col: string, expr: string): boolean {
  const dot = expr.indexOf(".");
  const op = expr.slice(0, dot);
  const val = expr.slice(dot + 1);
  const cell = row[col];
  switch (op) {
    case "eq": return String(cell) === val;
    case "lt": return String(cell) < val;
    case "gte": return String(cell) >= val;
    case "in": return val.slice(1, -1).split(",").includes(String(cell));
    default: throw new Error(`fake postgrest: unsupported operator ${op}`);
  }
}

function filterRows(rows: Row[], params: URLSearchParams): Row[] {
  let out = rows;
  for (const [key, expr] of params) {
    if (["select", "order", "limit", "offset", "on_conflict"].includes(key)) continue;
    if (key === "or") {
      const alts = expr.slice(1, -1).split(",").map((a) => {
        const i = a.indexOf(".");
        return [a.slice(0, i), a.slice(i + 1)] as const;
      });
      out = out.filter((r) => alts.some(([c, e]) => matches(r, c, e)));
    } else {
      out = out.filter((r) => matches(r, key, expr));
    }
  }
  return out;
}

export interface FakeBackend {
  env: Env;
  tables: Record<string, Row[]>;
  /** R2 objects: key → custom metadata. */
  objects: Map<string, Record<string, string>>;
  authUsers: Set<string>;
  /** Sign-in address per auth user id, for the admin "find user by email" lookup. */
  authEmails: Map<string, string>;
  stripeCustomers: Set<string>;
  /** Every outward call, in order: "DELETE scans", "stripe DELETE cus_1", "auth DELETE <id>", "r2 delete 3". */
  calls: string[];
  /** Make a matching call fail: (label) => status to return, or undefined to let it through. */
  failWith: (label: string) => number | undefined;
  fetch: typeof fetch;
}

export function fakeBackend(seed: {
  tables?: Record<string, Row[]>;
  objects?: Record<string, Record<string, string>>;
  authUsers?: string[];
  authEmails?: Record<string, string>;
  stripeCustomers?: string[];
} = {}): FakeBackend {
  const tables: Record<string, Row[]> = {};
  for (const [name, rows] of Object.entries(seed.tables ?? {})) tables[name] = rows.map((r) => ({ ...r }));
  const objects = new Map(Object.entries(seed.objects ?? {}));
  const authEmails = new Map(Object.entries(seed.authEmails ?? {}));
  const authUsers = new Set([...(seed.authUsers ?? []), ...authEmails.keys()]);
  const stripeCustomers = new Set(seed.stripeCustomers ?? []);
  const calls: string[] = [];

  const backend = { tables, objects, authUsers, authEmails, stripeCustomers, calls, failWith: () => undefined } as unknown as FakeBackend;

  const respond = (label: string, ok: () => Response): Response => {
    calls.push(label);
    const status = backend.failWith(label);
    return status ? new Response("forced failure", { status }) : ok();
  };

  backend.fetch = (async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(typeof input === "string" ? input : (input as Request).url ?? String(input));
    const method = (init.method ?? "GET").toUpperCase();

    if (url.hostname === "api.stripe.com") {
      const id = decodeURIComponent(url.pathname.split("/").pop()!);
      return respond(`stripe ${method} ${id}`, () => {
        if (!stripeCustomers.delete(id)) return new Response("{}", { status: 404 });
        return new Response(JSON.stringify({ id, deleted: true }));
      });
    }

    if (url.origin === SUPABASE && url.pathname === "/auth/v1/admin/users") {
      // GoTrue's `filter` is a substring match, like the real thing.
      const filter = url.searchParams.get("filter") ?? "";
      return respond("auth LIST", () => {
        const users = [...authEmails].filter(([id, email]) => authUsers.has(id) && email.includes(filter))
          .map(([id, email]) => ({ id, email }));
        return new Response(JSON.stringify({ users }));
      });
    }

    if (url.origin === SUPABASE && url.pathname.startsWith("/auth/v1/admin/users/")) {
      const id = url.pathname.split("/").pop()!;
      return respond(`auth ${method} ${id}`, () => {
        if (!authUsers.delete(id)) return new Response("{}", { status: 404 });
        return new Response("{}");
      });
    }

    if (url.origin === SUPABASE && url.pathname.startsWith("/rest/v1/")) {
      const table = url.pathname.slice("/rest/v1/".length);
      return respond(`${method} ${table}`, () => {
        if (!(table in tables)) return new Response(JSON.stringify({ code: "PGRST205" }), { status: 404 });
        const hit = filterRows(tables[table], url.searchParams);
        if (method === "DELETE") {
          tables[table] = tables[table].filter((r) => !hit.includes(r));
          return new Response(null, { status: 204, headers: { "Content-Range": `*/${hit.length}` } });
        }
        if (method === "POST") {
          const row = JSON.parse(String(init.body)) as Row;
          tables[table].push(row);
          return new Response(JSON.stringify([row]), { status: 201 });
        }
        if (method === "PATCH") {
          const patch = JSON.parse(String(init.body)) as Row;
          for (const r of hit) Object.assign(r, patch);
          return new Response(JSON.stringify(hit));
        }
        let rows = hit;
        const order = url.searchParams.get("order");
        if (order) {
          const cols = order.split(",").map((o) => o.split(".")[0]);
          rows = [...rows].sort((a, b) => {
            for (const c of cols) {
              if (String(a[c]) !== String(b[c])) return String(a[c]) < String(b[c]) ? -1 : 1;
            }
            return 0;
          });
        }
        const offset = Number(url.searchParams.get("offset") ?? 0);
        const limit = Number(url.searchParams.get("limit") ?? 1000);
        rows = rows.slice(offset, offset + Math.min(limit, 1000)); // PostgREST caps a page at 1000
        const select = url.searchParams.get("select");
        if (select && select !== "*") {
          const cols = select.split(",");
          rows = rows.map((r) => Object.fromEntries(cols.map((c) => [c, r[c]])));
        }
        return new Response(JSON.stringify(rows));
      });
    }

    throw new Error(`fake backend: unexpected request ${method} ${url}`);
  }) as typeof fetch;

  const bucket = {
    async list(opts: { prefix?: string; cursor?: string; limit?: number }) {
      const keys = [...objects.keys()].filter((k) => k.startsWith(opts.prefix ?? "")).sort();
      const start = opts.cursor ? Number(opts.cursor) : 0;
      const limit = opts.limit ?? 1000;
      const slice = keys.slice(start, start + limit);
      const truncated = start + limit < keys.length;
      return {
        objects: slice.map((key) => ({ key, size: key.length, customMetadata: objects.get(key), uploaded: new Date(0) })),
        truncated,
        cursor: truncated ? String(start + limit) : undefined,
      };
    },
    async delete(keys: string | string[]) {
      const list = Array.isArray(keys) ? keys : [keys];
      calls.push(`r2 delete ${list.length}`);
      const status = backend.failWith("r2 delete");
      if (status) throw new Error(`r2 failure ${status}`);
      for (const k of list) objects.delete(k);
    },
  };

  backend.env = {
    SUPABASE_URL: SUPABASE,
    SUPABASE_SERVICE_ROLE_KEY: "svc",
    STRIPE_SECRET_KEY: "sk_test",
    SHADOW_FILES: bucket,
  } as unknown as Env;

  return backend;
}
