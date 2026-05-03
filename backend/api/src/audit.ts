/**
 * Phase 4H — audit log.
 *
 * audit() inserts an entry; non-blocking, fire-and-forget.
 * /v1/me/audit returns the user's recent events for the dashboard "Recent activity" panel.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect } from "./supabase";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

export type AuditEvent =
  | "signin"
  | "signout"
  | "key_rotated"
  | "key_revoked"
  | "plan_changed"
  | "account_deleted"
  | "webhook_added"
  | "webhook_deleted"
  | "team_created"
  | "team_joined"
  | "totp_enabled"
  | "totp_disabled"
  | "export_downloaded"
  | "byok_set"
  | "byok_cleared";

/** Best-effort log entry. Never throws — silently swallows DB errors. */
export function audit(
  env: Env,
  userId: string,
  event_type: AuditEvent,
  meta: { ip?: string; user_agent?: string; metadata?: Record<string, unknown> } = {}
): Promise<void> {
  return dbInsert(env, "audit_log", {
    user_id: userId,
    event_type,
    ip: meta.ip ?? null,
    user_agent: meta.user_agent?.slice(0, 256) ?? null,
    metadata: meta.metadata ?? {},
  })
    .then(() => undefined)
    .catch((e) => {
      console.warn("[audit] insert failed", e instanceof Error ? e.message : e);
    });
}

export function clientHints(req: Request): { ip?: string; user_agent?: string } {
  const ip =
    req.headers.get("CF-Connecting-IP") ||
    req.headers.get("X-Forwarded-For")?.split(",")[0].trim() ||
    undefined;
  const ua = req.headers.get("User-Agent") || undefined;
  return { ip, user_agent: ua };
}

export async function listAudit(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const rows = await dbSelect(env, "audit_log", {
    select: "id,event_type,ip,user_agent,metadata,created_at",
    filters: { user_id: `eq.${user.id}` },
    order: "created_at.desc",
    limit: 50,
  });
  return json({ events: rows }, {}, cors);
}
