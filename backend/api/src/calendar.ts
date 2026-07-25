/**
 * Calendar — CRUD for personal events.
 *
 * Routes (all authenticated):
 *   GET    /v1/calendar/events?from=ISO&to=ISO  — events overlapping [from, to]
 *   POST   /v1/calendar/events                  — create event
 *   PATCH  /v1/calendar/events/:id              — update event (owner only)
 *   DELETE /v1/calendar/events/:id              — delete event (owner only)
 */

import type { Env } from "./index";

interface CalEvent {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  all_day: boolean;
  color: string;
  location: string | null;
  created_at: string;
}

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });
}

function sbHeaders(env: Env): HeadersInit {
  return {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    "Prefer": "return=representation",
  };
}

function isValidIso(s: unknown): s is string {
  return typeof s === "string" && !isNaN(Date.parse(s));
}

export async function listEvents(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const now = new Date();
  const from = url.searchParams.get("from") || new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
  const to   = url.searchParams.get("to")   || new Date(now.getFullYear(), now.getMonth() + 2, 1).toISOString();

  const q = new URL(`${env.SUPABASE_URL}/rest/v1/calendar_events`);
  q.searchParams.set("select", "*");
  q.searchParams.set("user_id", `eq.${user.id}`);
  q.searchParams.set("start_at", `lt.${to}`);
  q.searchParams.set("end_at", `gt.${from}`);
  q.searchParams.set("order", "start_at.asc");
  q.searchParams.set("limit", "500");

  const resp = await fetch(q.toString(), { headers: sbHeaders(env) });
  if (!resp.ok) return json({ error: "db_error", detail: await resp.text() }, { status: 500 }, cors);
  const events = (await resp.json()) as CalEvent[];
  return json({ events }, {}, cors);
}

export async function createEvent(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  let body: Record<string, unknown>;
  try { body = await req.json() as Record<string, unknown>; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const title = (typeof body.title === "string" ? body.title : "").trim().slice(0, 200);
  if (!title) return json({ error: "title_required" }, { status: 400 }, cors);
  if (!isValidIso(body.start_at)) return json({ error: "start_at_required" }, { status: 400 }, cors);
  if (!isValidIso(body.end_at))   return json({ error: "end_at_required" }, { status: 400 }, cors);
  if (new Date(body.end_at) < new Date(body.start_at))
    return json({ error: "end_before_start" }, { status: 400 }, cors);

  const COLORS = new Set(["#b44aff","#ef4444","#f97316","#22c55e","#3b82f6","#14b8a6"]);
  const color = typeof body.color === "string" && COLORS.has(body.color) ? body.color : "#b44aff";

  const row = {
    user_id:     user.id,
    title,
    description: typeof body.description === "string" ? body.description.slice(0, 2000) : null,
    start_at:    body.start_at,
    end_at:      body.end_at,
    all_day:     body.all_day === true,
    color,
    location:    typeof body.location === "string" ? body.location.slice(0, 500) : null,
  };

  const url = `${env.SUPABASE_URL}/rest/v1/calendar_events`;
  const resp = await fetch(url, { method: "POST", headers: sbHeaders(env), body: JSON.stringify(row) });
  if (!resp.ok) return json({ error: "db_error", detail: await resp.text() }, { status: 500 }, cors);
  const rows = (await resp.json()) as CalEvent[];
  return json({ event: rows[0] }, { status: 201 }, cors);
}

export async function updateEvent(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit, eventId: string
): Promise<Response> {
  let body: Record<string, unknown>;
  try { body = await req.json() as Record<string, unknown>; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const allowed = ["title","description","start_at","end_at","all_day","color","location"];
  const patch: Record<string, unknown> = {};
  for (const k of allowed) if (k in body) patch[k] = body[k];

  if (patch.title !== undefined) {
    patch.title = (String(patch.title)).trim().slice(0, 200);
    if (!patch.title) return json({ error: "title_required" }, { status: 400 }, cors);
  }
  if (patch.start_at !== undefined && !isValidIso(patch.start_at))
    return json({ error: "invalid_start_at" }, { status: 400 }, cors);
  if (patch.end_at !== undefined && !isValidIso(patch.end_at))
    return json({ error: "invalid_end_at" }, { status: 400 }, cors);

  const COLORS = new Set(["#b44aff","#ef4444","#f97316","#22c55e","#3b82f6","#14b8a6"]);
  if (patch.color !== undefined && !COLORS.has(patch.color as string)) delete patch.color;

  const url = new URL(`${env.SUPABASE_URL}/rest/v1/calendar_events`);
  url.searchParams.set("id", `eq.${eventId}`);
  url.searchParams.set("user_id", `eq.${user.id}`);

  const resp = await fetch(url.toString(), {
    method: "PATCH",
    headers: sbHeaders(env),
    body: JSON.stringify(patch),
  });
  if (!resp.ok) return json({ error: "db_error", detail: await resp.text() }, { status: 500 }, cors);
  const rows = (await resp.json()) as CalEvent[];
  if (!rows.length) return json({ error: "not_found" }, { status: 404 }, cors);
  return json({ event: rows[0] }, {}, cors);
}

export async function deleteEvent(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit, eventId: string
): Promise<Response> {
  const url = new URL(`${env.SUPABASE_URL}/rest/v1/calendar_events`);
  url.searchParams.set("id", `eq.${eventId}`);
  url.searchParams.set("user_id", `eq.${user.id}`);

  const resp = await fetch(url.toString(), {
    method: "DELETE",
    headers: sbHeaders(env),
  });
  if (!resp.ok) return json({ error: "db_error", detail: await resp.text() }, { status: 500 }, cors);
  return json({ ok: true }, {}, cors);
}
