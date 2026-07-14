/**
 * R2 file storage — upload, download, delete.
 *
 * Routes (all authenticated):
 *   POST   /v1/files/upload   — multipart or raw body upload (max 10 MB)
 *   GET    /v1/files/:key     — stream file from R2 (any authed user)
 *   DELETE /v1/files/:key     — delete (owner only; key prefix = user_id/)
 */

import type { Env } from "./index";

const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

const ALLOWED_TYPES = new Set([
  "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
  "application/pdf",
  "text/plain", "text/markdown",
  "application/zip",
  "audio/mpeg", "audio/ogg", "audio/wav",
  "video/mp4", "video/webm",
]);

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });
}

export async function uploadFile(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);

  let fileData: ArrayBuffer;
  let fileName = "file";
  let mimeType = "application/octet-stream";

  const ct = req.headers.get("Content-Type") ?? "";

  if (ct.includes("multipart/form-data")) {
    const form = await req.formData().catch(() => null);
    if (!form) return json({ error: "invalid_form" }, { status: 400 }, cors);
    const file = form.get("file");
    if (!file || typeof file === "string")
      return json({ error: "file_field_required" }, { status: 400 }, cors);
    if ((file as File).size > MAX_BYTES)
      return json({ error: "file_too_large", max_bytes: MAX_BYTES }, { status: 413 }, cors);
    fileData = await (file as File).arrayBuffer();
    fileName = (file as File).name || "file";
    mimeType = (file as File).type || "application/octet-stream";
  } else {
    fileData = await req.arrayBuffer();
    if (fileData.byteLength > MAX_BYTES)
      return json({ error: "file_too_large", max_bytes: MAX_BYTES }, { status: 413 }, cors);
    const cd = req.headers.get("Content-Disposition") ?? "";
    const nameMatch = cd.match(/filename="?([^";]+)"?/i);
    if (nameMatch) fileName = nameMatch[1];
    mimeType = ct.split(";")[0].trim() || "application/octet-stream";
  }

  if (!ALLOWED_TYPES.has(mimeType))
    return json({ error: "unsupported_type", allowed: [...ALLOWED_TYPES] }, { status: 415 }, cors);

  const ext = fileName.includes(".") ? fileName.split(".").pop()!.slice(0, 10).toLowerCase() : "";
  const uuid = crypto.randomUUID();
  const key = `${user.id}/${uuid}${ext ? "." + ext : ""}`;
  const safeName = fileName.replace(/[^\w.\- ]/g, "_").slice(0, 200);

  await env.SHADOW_FILES.put(key, fileData, {
    httpMetadata: {
      contentType: mimeType,
      contentDisposition: `inline; filename="${safeName}"`,
    },
    customMetadata: {
      user_id: user.id,
      original_name: safeName,
      uploaded_at: new Date().toISOString(),
    },
  });

  return json({ ok: true, key, name: safeName, size: fileData.byteLength, type: mimeType }, {}, cors);
}

export async function downloadFile(
  _req: Request,
  env: Env,
  _user: { id: string; email: string },
  cors: HeadersInit,
  key: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);

  const obj = await env.SHADOW_FILES.get(key);
  if (!obj) return json({ error: "not_found" }, { status: 404 }, cors);

  const headers = new Headers(cors as Record<string, string>);
  headers.set("Content-Type", obj.httpMetadata?.contentType ?? "application/octet-stream");
  if (obj.httpMetadata?.contentDisposition)
    headers.set("Content-Disposition", obj.httpMetadata.contentDisposition);
  headers.set("Cache-Control", "private, max-age=3600");
  if (obj.size) headers.set("Content-Length", String(obj.size));

  return new Response(obj.body, { headers });
}

export async function deleteFile(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  key: string
): Promise<Response> {
  if (!env.SHADOW_FILES) return json({ error: "storage_not_configured" }, { status: 503 }, cors);

  if (!key.startsWith(`${user.id}/`))
    return json({ error: "forbidden" }, { status: 403 }, cors);

  await env.SHADOW_FILES.delete(key);
  return json({ ok: true }, {}, cors);
}
