/**
 * Shadow Sheets — spreadsheet CRUD backed by R2.
 *
 * Keys in R2: `{user_id}/sheets/{uuid}.json`
 * Custom metadata: title, updated_at, user_id
 *
 * Routes (all authenticated):
 *   GET    /v1/sheets          — list user's sheets
 *   POST   /v1/sheets          — create blank sheet { title? }
 *   GET    /v1/sheets/:id      — fetch sheet data + meta
 *   PUT    /v1/sheets/:id      — save sheet { data, title? }
 *   DELETE /v1/sheets/:id      — delete sheet
 */

import type { Env } from "./index";

const SHEET_MAX = 2 * 1024 * 1024; // 2 MB
const CT_JSON   = "application/json; charset=utf-8";

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });
}

function idFromKey(key: string): string {
  return key.split("/").pop()!.replace(/\.json$/, "");
}

export async function listSheets(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  const result = await env.SHADOW_FILES.list({ prefix: `${user.id}/sheets/`, limit: 500 });
  const sheets = result.objects.map(obj => ({
    id:         idFromKey(obj.key),
    title:      obj.customMetadata?.title ?? "Untitled Sheet",
    updated_at: obj.customMetadata?.updated_at ?? obj.uploaded?.toISOString() ?? null,
    size:       obj.size,
  })).sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
  return json({ sheets }, {}, cors);
}

export async function createSheet(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  let body: Record<string, unknown> = {};
  try { body = await req.json() as Record<string, unknown>; } catch { /* empty body ok */ }
  const title = typeof body.title === "string" ? body.title.trim().slice(0, 200) || "Untitled Sheet" : "Untitled Sheet";
  const id  = crypto.randomUUID();
  const key = `${user.id}/sheets/${id}.json`;
  await env.SHADOW_FILES.put(key, "{}", {
    httpMetadata:   { contentType: CT_JSON },
    customMetadata: { title, updated_at: new Date().toISOString(), user_id: user.id },
  });
  return json({ id, title }, { status: 201 }, cors);
}

export async function getSheet(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  const key = `${user.id}/sheets/${id}.json`;
  const obj = await env.SHADOW_FILES.get(key);
  if (!obj) return json({ error: "not_found" }, { status: 404 }, cors);
  let data: Record<string, string> = {};
  try { data = JSON.parse(await obj.text()) as Record<string, string>; } catch { /* ignore corrupt data */ }
  return json({
    id,
    title:      obj.customMetadata?.title ?? "Untitled Sheet",
    updated_at: obj.customMetadata?.updated_at ?? null,
    data,
  }, {}, cors);
}

export async function saveSheet(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  let body: Record<string, unknown>;
  try { body = await req.json() as Record<string, unknown>; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const key      = `${user.id}/sheets/${id}.json`;
  const existing = await env.SHADOW_FILES.head(key);
  if (!existing) return json({ error: "not_found" }, { status: 404 }, cors);

  const rawData = body.data && typeof body.data === "object" ? body.data : {};
  const payload = JSON.stringify(rawData);
  if (payload.length > SHEET_MAX) return json({ error: "sheet_too_large" }, { status: 413 }, cors);

  const title = typeof body.title === "string"
    ? body.title.trim().slice(0, 200) || "Untitled Sheet"
    : (existing.customMetadata?.title ?? "Untitled Sheet");

  await env.SHADOW_FILES.put(key, payload, {
    httpMetadata:   { contentType: CT_JSON },
    customMetadata: { title: title || "Untitled Sheet", updated_at: new Date().toISOString(), user_id: user.id },
  });
  return json({ ok: true, title }, {}, cors);
}

export async function deleteSheet(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  await env.SHADOW_FILES.delete(`${user.id}/sheets/${id}.json`);
  return json({ ok: true }, {}, cors);
}
