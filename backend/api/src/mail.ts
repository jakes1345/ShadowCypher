/**
 * Shadow Mail — inbound storage + REST API
 *
 * Inbound flow:  Cloudflare Email Worker → storeInboundMail() → mail_messages table
 * Outbound flow: POST /v1/mail/send → Resend → stored as direction='outbound'
 * Internal flow: mail to another handle@shadowcypher.site skips Resend and is
 *                written straight into the recipient's inbox
 * Role addresses: mail for a reserved name (security@, privacy@, billing@ …)
 *                goes to the operator's inbox, and no other account may send
 *                as one. See reserved.ts.
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
import { dbSelect, dbInsert, dbUpdate, dbCount, findAuthUserByEmail } from "./supabase";
import { dispatchMailWebhook } from "./webhooks";
import { dispatchMailPushNotification } from "./notifications";
import { decodeMimeWords, decodeQuotedPrintable, decodeBase64Body, parseHeaders, parseMimeParts, escapeRegex, extractBodies } from "./mime";
import type { MimePart } from "./mime";
import { inboxFor, isBlockedSender } from "./reserved";
import { bodyColumnsFor, previewFor } from "./mail_crypto";

interface MailRow {
  id: string;
  user_id: string;
  message_id: string | null;
  from_addr: string;
  to_addr: string;
  subject: string;
  body_text: string | null;
  body_html: string | null;
  body_pgp: string | null;
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
  // Role addresses land in the operator's inbox; to_addr below keeps the address that was written to.
  const userEmail = inboxFor(handle);

  const user = await findAuthUserByEmail(env, userEmail);
  if (!user) return;

  const subject = decodeMimeWords(message.headers.get("subject") ?? "(no subject)");
  const messageId = message.headers.get("message-id") ?? null;
  const dateStr = message.headers.get("date") ?? new Date().toISOString();

  const { text, html } = extractBodies(rawBody);

  const receivedAt = new Date(dateStr).toISOString();
  const body = await bodyColumnsFor(env, user.id, text, html);

  await dbInsert(env, "mail_messages", {
    user_id: user.id,
    message_id: messageId,
    from_addr: message.from,
    to_addr: message.to,
    subject,
    ...body,
    direction: "inbound",
    is_read: false,
    received_at: receivedAt,
  });

  // Notify any mail.received webhooks (Slack, Teams, Zoom, Discord, custom).
  // Sealed mail carries no body preview: it would leave the platform in the clear.
  const preview = previewFor(body, text);
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

// ── Internal delivery (user → user on shadowcypher.site, never leaves the platform) ──

const INTERNAL_ADDR = /^[a-z0-9_]{2,32}@shadowcypher\.site$/;

export function bareAddress(addr: string): string {
  const m = addr.match(/<([^>]+)>/);
  return (m ? m[1] : addr).trim().toLowerCase();
}

export function isInternalAddress(addr: string): boolean {
  return INTERNAL_ADDR.test(bareAddress(addr));
}

type InternalResult = { ok: true; messageId: string } | { ok: false };

async function deliverInternal(
  env: Env,
  fromAddr: string,
  toAddr: string,
  subject: string,
  text: string | null,
  html: string | null
): Promise<InternalResult> {
  const recipient = await findAuthUserByEmail(env, inboxFor(toAddr.split("@")[0]));
  if (!recipient) return { ok: false };

  const messageId = `<${crypto.randomUUID()}@shadowcypher.site>`;
  const receivedAt = new Date().toISOString();
  const body = await bodyColumnsFor(env, recipient.id, text, html);
  await dbInsert(env, "mail_messages", {
    user_id: recipient.id,
    message_id: messageId,
    from_addr: fromAddr,
    to_addr: toAddr,
    subject,
    ...body,
    direction: "inbound",
    is_read: false,
    received_at: receivedAt,
  });

  const preview = previewFor(body, text);
  dispatchMailWebhook(env, { from: fromAddr, to: toAddr, subject, preview, received_at: receivedAt, user_id: recipient.id }).catch(() => null);
  dispatchMailPushNotification(env, recipient.id, { from: fromAddr, subject, preview }).catch(() => null);

  return { ok: true, messageId };
}

async function storeSentCopy(
  env: Env,
  userId: string,
  messageId: string | null,
  fromAddr: string,
  toAddr: string,
  subject: string,
  text: string | null,
  html: string | null
): Promise<void> {
  const body = await bodyColumnsFor(env, userId, text, html);
  await dbInsert(env, "mail_messages", {
    user_id: userId,
    message_id: messageId,
    from_addr: fromAddr,
    to_addr: toAddr,
    subject,
    ...body,
    direction: "outbound",
    is_read: true,
    received_at: new Date().toISOString(),
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

  const [rows, total] = await Promise.all([
    dbSelect<MailRow>(env, "mail_messages", {
      select: "id,from_addr,to_addr,subject,direction,is_read,received_at",
      filters,
      order: "received_at.desc",
      limit,
      offset,
    }),
    dbCount(env, "mail_messages", filters),
  ]);

  return json({ messages: rows, total }, {}, cors);
}

export async function getMailCount(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  const [total, unread] = await Promise.all([
    dbCount(env, "mail_messages", { user_id: `eq.${user.id}` }),
    dbCount(env, "mail_messages", { user_id: `eq.${user.id}`, is_read: "eq.false" }),
  ]);
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
  const body = (await req.json().catch(() => null)) as {
    to?: string;
    subject?: string;
    text?: string;
    html?: string;
  } | null;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!body?.to || !emailRegex.test(body.to) || !body.subject?.trim())
    return json({ error: "to_and_subject_required" }, { status: 400 }, cors);

  if (isBlockedSender(user.email)) return json({ error: "reserved_sender" }, { status: 403 }, cors);

  const subject = body.subject.trim();
  const text = body.text ?? null;
  const html = body.html ?? null;

  if (isInternalAddress(body.to)) {
    const to = bareAddress(body.to);
    const sent = await deliverInternal(env, user.email, to, subject, text, html);
    if (!sent.ok) return json({ error: "recipient_not_found" }, { status: 404 }, cors);
    await storeSentCopy(env, user.id, sent.messageId, user.email, to, subject, text, html);
    return json({ ok: true, id: sent.messageId, internal: true }, {}, cors);
  }

  if (!env.RESEND_API_KEY) return json({ error: "mail_not_configured" }, { status: 503 }, cors);

  const handle = user.email.split("@")[0];
  const from = user.email.endsWith("@shadowcypher.site")
    ? `${handle} <${user.email}>`
    : env.RESEND_FROM_EMAIL || "ShadowCypher <noreply@shadowcypher.site>";
  const sendResp = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from,
      to: body.to,
      subject,
      ...(html ? { html } : { text: text ?? "" }),
    }),
  });

  if (!sendResp.ok) return json({ error: "send_failed" }, { status: 502 }, cors);
  const sendData = (await sendResp.json()) as { id?: string };

  await storeSentCopy(env, user.id, sendData.id ?? null, user.email, body.to, subject, text, html);
  return json({ ok: true, id: sendData.id }, {}, cors);
}

export async function replyMail(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
  messageId: string
): Promise<Response> {
  const orig = await dbSelect<MailRow>(env, "mail_messages", {
    select: "id,user_id,message_id,from_addr,subject",
    filters: { id: `eq.${messageId}`, user_id: `eq.${user.id}` },
    limit: 1,
  }).then((r) => r[0] ?? null);
  if (!orig) return json({ error: "not_found" }, { status: 404 }, cors);

  const body = (await req.json().catch(() => null)) as { text?: string } | null;
  const replyText = body?.text?.trim() ?? "";
  if (!replyText) return json({ error: "text_required" }, { status: 400 }, cors);
  if (isBlockedSender(user.email)) return json({ error: "reserved_sender" }, { status: 403 }, cors);

  const replyTo = orig.from_addr;
  const replySubject = /^re:/i.test(orig.subject) ? orig.subject : `Re: ${orig.subject}`;

  if (isInternalAddress(replyTo)) {
    const to = bareAddress(replyTo);
    const sent = await deliverInternal(env, user.email, to, replySubject, replyText, null);
    if (!sent.ok) return json({ error: "recipient_not_found" }, { status: 404 }, cors);
    await storeSentCopy(env, user.id, sent.messageId, user.email, to, replySubject, replyText, null);
    return json({ ok: true, id: sent.messageId, internal: true }, {}, cors);
  }

  if (!env.RESEND_API_KEY) return json({ error: "mail_not_configured" }, { status: 503 }, cors);

  const handle = user.email.split("@")[0];
  const fromAddr = user.email.endsWith("@shadowcypher.site")
    ? `${handle} <${user.email}>`
    : user.email;

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

  await storeSentCopy(env, user.id, sendData.id ?? null, fromAddr, replyTo, replySubject, replyText, null);

  return json({ ok: true, id: sendData.id }, {}, cors);
}
