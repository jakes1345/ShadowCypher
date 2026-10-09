/**
 * Shadow Docs — rich-text document CRUD backed by R2.
 *
 * Keys in R2: `{user_id}/docs/{uuid}.html`
 * Content-Type stored: text/html; charset=utf-8
 * Custom metadata: title, updated_at, user_id
 *
 * Routes (all authenticated):
 *   GET    /v1/docs          — list user's docs
 *   POST   /v1/docs          — create blank doc { title? }
 *   GET    /v1/docs/:id      — fetch doc HTML + meta
 *   PUT    /v1/docs/:id      — save doc { html, title? }
 *   DELETE /v1/docs/:id      — delete doc
 */

import type { Env } from "./index";

const DOC_MAX  = 5 * 1024 * 1024; // 5 MB
const CT_HTML  = "text/html; charset=utf-8";

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });
}

function idFromKey(key: string): string {
  return key.split("/").pop()!.replace(/\.html$/, "");
}

export async function listDocs(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  const result = await env.SHADOW_FILES.list({ prefix: `${user.id}/docs/`, limit: 500 });
  const docs = result.objects.map(obj => ({
    id:         idFromKey(obj.key),
    title:      obj.customMetadata?.title ?? "Untitled",
    updated_at: obj.customMetadata?.updated_at ?? obj.uploaded?.toISOString() ?? null,
    size:       obj.size,
  })).sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""));
  return json({ docs }, {}, cors);
}

export async function createDoc(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  let body: Record<string, unknown> = {};
  try { body = await req.json() as Record<string, unknown>; } catch { /* empty body ok */ }
  const title = typeof body.title === "string" ? body.title.trim().slice(0, 200) || "Untitled" : "Untitled";
  const id  = crypto.randomUUID();
  const key = `${user.id}/docs/${id}.html`;
  await env.SHADOW_FILES.put(key, "<p><br></p>", {
    httpMetadata:   { contentType: CT_HTML },
    customMetadata: { title, updated_at: new Date().toISOString(), user_id: user.id },
  });
  return json({ id, title }, { status: 201 }, cors);
}

export async function getDoc(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  const key = `${user.id}/docs/${id}.html`;
  const obj = await env.SHADOW_FILES.get(key);
  if (!obj) return json({ error: "not_found" }, { status: 404 }, cors);
  const html = await obj.text();
  return json({
    id,
    title:      obj.customMetadata?.title ?? "Untitled",
    updated_at: obj.customMetadata?.updated_at ?? null,
    html,
  }, {}, cors);
}

export async function saveDoc(
  req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  let body: Record<string, unknown>;
  try { body = await req.json() as Record<string, unknown>; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const key      = `${user.id}/docs/${id}.html`;
  const existing = await env.SHADOW_FILES.head(key);
  if (!existing) return json({ error: "not_found" }, { status: 404 }, cors);

  const html  = typeof body.html === "string"  ? body.html.slice(0, DOC_MAX)    : "<p><br></p>";
  const title = typeof body.title === "string" ? body.title.trim().slice(0, 200)
                                               : (existing.customMetadata?.title ?? "Untitled");

  await env.SHADOW_FILES.put(key, html, {
    httpMetadata:   { contentType: CT_HTML },
    customMetadata: { title: title || "Untitled", updated_at: new Date().toISOString(), user_id: user.id },
  });
  return json({ ok: true, title }, {}, cors);
}

export async function deleteDoc(
  _req: Request, env: Env, user: { id: string }, cors: HeadersInit, id: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);
  await env.SHADOW_FILES.delete(`${user.id}/docs/${id}.html`);
  return json({ ok: true }, {}, cors);
}
