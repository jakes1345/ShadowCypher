/**
 * Shadow Mail — inbound storage + REST API
 *
 * Inbound flow:  Cloudflare Email Worker → storeInboundMail() → mail_messages table
 * Outbound flow: POST /v1/mail/send → Resend → stored as direction='outbound'
 *
 * Routes (all authenticated):
 *   GET    /v1/mail/inbox          — paginated inbox (newest first)
 *   GET    /v1/mail/count          — unread + total counts
 *   GET    /v1/mail/:id            — single message (marks read)
 *   POST   /v1/mail/:id/read       — mark read without fetching body
 *   DELETE /v1/mail/:id            — delete
 *   POST   /v1/mail/send           — send outbound email via Resend
 */

import type { Env } from "./index";
import { dbSelect, dbInsert, dbUpdate } from "./supabase";
import { dispatchMailWebhook } from "./webhooks";
import { dispatchMailPushNotification } from "./notifications";
import { decodeMimeWords, decodeQuotedPrintable, decodeBase64Body, parseHeaders, parseMimeParts, escapeRegex, extractBodies } from "./mime";
import type { MimePart } from "./mime";

interface MailRow {
  id: string;
  user_id: string;
  message_id: string | null;
  from_addr: string;
  to_addr: string;
  subject: string;
  body_text: string | null;
  body_html: string | null;
  direction: "inbound" | "outbound";
  is_read: boolean;
  received_at: string;
}

function json(body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });
}

// ── Inbound mail storage (called from email event handler) ───────────────────

export async function storeInboundMail(
  env: Env,
  message: ForwardableEmailMessage,
  rawBody: string
): Promise<void> {
  const to = message.to.toLowerCase();
  const handleMatch = to.match(/^([a-z0-9_]{2,32})@shadowcypher\.site$/);
  if (!handleMatch) return; // not a valid handle address

  const handle = handleMatch[1];
  const userEmail = `${handle}@shadowcypher.site`;

  // Resolve user_id from email
  const usersResp = await fetch(
    `${env.SUPABASE_URL}/auth/v1/admin/users?email=${encodeURIComponent(userEmail)}`,
    {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      },
    }
  );
  if (!usersResp.ok) return;
  const usersBody = (await usersResp.json()) as { users?: { id: string }[] };
  const user = usersBody.users?.[0];
  if (!user) return;

  const subject = decodeMimeWords(message.headers.get("subject") ?? "(no subject)");
  const messageId = message.headers.get("message-id") ?? null;
  const dateStr = message.headers.get("date") ?? new Date().toISOString();

  const { text, html } = extractBodies(rawBody);

  const receivedAt = new Date(dateStr).toISOString();

  await dbInsert(env, "mail_messages", {
    user_id: user.id,
    message_id: messageId,
    from_addr: message.from,
    to_addr: message.to,
    subject,
    body_text: text,
    body_html: html,
    direction: "inbound",
    is_read: false,
    received_at: receivedAt,
  });

  // Notify any mail.received webhooks (Slack, Teams, Zoom, Discord, custom)
  const preview = (text ?? "").trim().slice(0, 280).replace(/\s+/g, " ");
  dispatchMailWebhook(env, {
    from: message.from,
    to: message.to,
    subject,
    preview,
    received_at: receivedAt,
    user_id: user.id,
  }).catch(() => null);

  // Web push notification for new inbound mail
  dispatchMailPushNotification(env, user.id, {
    from: message.from,
    subject,
    preview,
  }).catch(() => null);
}

// ── REST handlers ─────────────────────────────────────────────────────────────

export async function getInbox(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "50"), 100);
  const offset = parseInt(url.searchParams.get("offset") ?? "0");
  const q = url.searchParams.get("q")?.trim().slice(0, 100) ?? "";

  const filters: Record<string, string> = { user_id: `eq.${user.id}` };
  if (q) {
    // Escape ILIKE wildcards in the user query, then wrap with %
    const safe = q.replace(/[%_\\]/g, (c) => `\\${c}`);
    filters.or = `(subject.ilike.%${safe}%,from_addr.ilike.%${safe}%)`;
  }

  const rows = await dbSelect<MailRow>(env, "mail_messages", {
    select: "id,from_addr,to_addr,subject,direction,is_read,received_at",
    filters,
    order: "received_at.desc",
    limit,
  });

  return json({ messages: rows.slice(offset, offset + limit), total: rows.length }, {}, cors);
}

export async function getMailCount(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const rows = await dbSelect<{ is_read: boolean }>(env, "mail_messages", {
    select: "is_read",
    filters: { user_id: `eq.${user.id}` },
  });
  const total = rows.length;
  const unread = rows.filter((r) => !r.is_read).length;
  return json({ total, unread }, {}, cors);
}

export async function getMail(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  messageId: string
): Promise<Response> {
  const rows = await dbSelect<MailRow>(env, "mail_messages", {
    filters: { id: `eq.${messageId}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!rows.length) return json({ error: "not_found" }, { status: 404 }, cors);
  const row = rows[0];

  // mark read
  if (!row.is_read) {
    await dbUpdate(env, "mail_messages", { id: `eq.${messageId}`, user_id: `eq.${user.id}` }, { is_read: true });
  }

  return json(row, {}, cors);
}

export async function markRead(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  messageId: string
): Promise<Response> {
  await dbUpdate(env, "mail_messages", { id: `eq.${messageId}`, user_id: `eq.${user.id}` }, { is_read: true });
  return json({ ok: true }, {}, cors);
}

export async function deleteMail(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  messageId: string
): Promise<Response> {
  // PostgREST DELETE
  const url = `${env.SUPABASE_URL}/rest/v1/mail_messages?id=eq.${messageId}&user_id=eq.${user.id}`;
  const resp = await fetch(url, {
    method: "DELETE",
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!resp.ok) return json({ error: "delete_failed" }, { status: 500 }, cors);
  return json({ ok: true }, {}, cors);
}

export async function sendOutbound(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  if (!env.RESEND_API_KEY) return json({ error: "mail_not_configured" }, { status: 503 }, cors);

  const body = (await req.json().catch(() => null)) as {
    to?: string;
    subject?: string;
    text?: string;
    html?: string;
  } | null;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!body?.to || !emailRegex.test(body.to) || !body.subject?.trim())
    return json({ error: "to_and_subject_required" }, { status: 400 }, cors);

  const from = env.RESEND_FROM_EMAIL || "ShadowCypher <noreply@shadowcypher.site>";
  const sendResp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from,
      to: body.to,
      subject: body.subject.trim(),
      ...(body.html ? { html: body.html } : { text: body.text ?? "" }),
    }),
  });

  if (!sendResp.ok) return json({ error: "send_failed" }, { status: 502 }, cors);
  const sendData = (await sendResp.json()) as { id?: string };

  // Store a copy in outbox
  await dbInsert(env, "mail_messages", {
    user_id: user.id,
    message_id: sendData.id ?? null,
    from_addr: user.email,
    to_addr: body.to,
    subject: body.subject.trim(),
    body_text: body.text ?? null,
    body_html: body.html ?? null,
    direction: "outbound",
    is_read: true,
    received_at: new Date().toISOString(),
  }).catch(() => null);

  return json({ ok: true, id: sendData.id }, {}, cors);
}

export async function replyMail(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  messageId: string
): Promise<Response> {
  if (!env.RESEND_API_KEY) return json({ error: "mail_not_configured" }, { status: 503 }, cors);

  const orig = await dbSelect<MailRow>(env, "mail_messages", {
    select: "id,user_id,message_id,from_addr,subject",
    filters: { id: `eq.${messageId}`, user_id: `eq.${user.id}` },
    limit: 1,
  }).then((r) => r[0] ?? null);
  if (!orig) return json({ error: "not_found" }, { status: 404 }, cors);

  const body = (await req.json().catch(() => null)) as { text?: string } | null;
  const replyText = body?.text?.trim() ?? "";
  if (!replyText) return json({ error: "text_required" }, { status: 400 }, cors);

  const replyTo = orig.from_addr;
  const replySubject = /^re:/i.test(orig.subject) ? orig.subject : `Re: ${orig.subject}`;
  const fromAddr = user.email;

  const extraHeaders: Record<string, string> = {};
  if (orig.message_id) {
    extraHeaders["In-Reply-To"] = orig.message_id;
    extraHeaders["References"] = orig.message_id;
  }

  const sendResp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: fromAddr,
      to: replyTo,
      subject: replySubject,
      text: replyText,
      ...(Object.keys(extraHeaders).length ? { headers: extraHeaders } : {}),
    }),
  });

  if (!sendResp.ok) return json({ error: "send_failed" }, { status: 502 }, cors);
  const sendData = (await sendResp.json()) as { id?: string };

  await dbInsert(env, "mail_messages", {
    user_id: user.id,
    message_id: sendData.id ?? null,
    from_addr: fromAddr,
    to_addr: replyTo,
    subject: replySubject,
    body_text: replyText,
    body_html: null,
    direction: "outbound",
    is_read: true,
    received_at: new Date().toISOString(),
  }).catch(() => null);

  return json({ ok: true, id: sendData.id }, {}, cors);
}
