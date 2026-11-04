/**
 * Identity keys for zero-access encryption.
 *
 *   GET  /v1/auth/kdf?handle=        — public: password-stretching params for login
 *   GET  /v1/identity/lookup?handle= — public: a user's public key
 *   GET  /v1/identity/me             — authed: own key bundle (private keys locked)
 *   POST /v1/identity/me             — authed: store or update own key bundle
 *
 * Keys are generated and unlocked only in the client (www/js/identity.js).
 * The server checks that what it stores is well-formed and still locked.
 */

import * as openpgp from "openpgp";
import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate, lookupAuthUserByEmail } from "./supabase";
import { audit, clientHints } from "./audit";

interface AuthedUser { id: string; email: string; handle?: string }

interface KeyRow {
  user_id: string;
  handle: string;
  fingerprint: string;
  public_key: string;
  encrypted_private_key: string;
  recovery_private_key: string | null;
  updated_at: string;
}

const HANDLE_RE = /^[a-z0-9_]{2,32}$/;
const MAX_PUBLIC = 16_384;
const MAX_PRIVATE = 32_768;
const DOMAIN = "shadowcypher.site";

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...cors, ...(init.headers || {}) },
  });

function handleParam(req: Request): string | null {
  const h = new URL(req.url).searchParams.get("handle")?.trim().toLowerCase().replace(/^@/, "") ?? "";
  return HANDLE_RE.test(h) ? h : null;
}

// Mirrors validateKdf in www/js/identity.js.
function sanitizeKdf(raw: unknown): Record<string, unknown> | null {
  const k = raw as { v?: unknown; alg?: unknown; m?: unknown; t?: unknown; p?: unknown; salt?: unknown } | null;
  if (!k || k.v !== 1 || k.alg !== "argon2id") return null;
  const int = (x: unknown, lo: number, hi: number) => Number.isInteger(x) && (x as number) >= lo && (x as number) <= hi;
  if (!int(k.m, 19456, 262144) || !int(k.t, 1, 10) || !int(k.p, 1, 4)) return null;
  if (typeof k.salt !== "string" || !/^[A-Za-z0-9+/]{22,88}={0,2}$/.test(k.salt)) return null;
  return { v: 1, alg: "argon2id", m: k.m, t: k.t, p: k.p, salt: k.salt };
}

export async function getKdfParams(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const handle = handleParam(req);
  if (!handle) return json({ error: "invalid_handle" }, { status: 400 }, cors);
  let user;
  try {
    user = await lookupAuthUserByEmail(env, `${handle}@${DOMAIN}`);
  } catch {
    // Never answer "legacy" when we couldn't check: the client would send the raw password.
    return json({ error: "lookup_unavailable" }, { status: 503 }, cors);
  }
  // Unknown and not-yet-upgraded accounts look the same: v0 means "send the password as-is".
  return json(sanitizeKdf(user?.user_metadata?.kdf) ?? { v: 0 }, {}, cors);
}

export async function lookupIdentity(req: Request, env: Env, cors: HeadersInit): Promise<Response> {
  const handle = handleParam(req);
  if (!handle) return json({ error: "invalid_handle" }, { status: 400 }, cors);
  const rows = await dbSelect<KeyRow>(env, "user_keys", {
    select: "handle,fingerprint,public_key",
    filters: { handle: `eq.${handle}` },
    limit: 1,
  });
  if (!rows.length) return json({ error: "no_identity" }, { status: 404 }, cors);
  const { fingerprint, public_key } = rows[0];
  return json({ handle, fingerprint, public_key }, {}, cors);
}

export async function getMyIdentity(_req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const rows = await dbSelect<KeyRow>(env, "user_keys", {
    select: "fingerprint,public_key,encrypted_private_key,recovery_private_key,updated_at",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!rows.length) return json({ error: "no_identity" }, { status: 404 }, cors);
  return json(rows[0], {}, cors);
}

type Checked = { fingerprint: string; publicKey: string; locked: string; recovery?: string };

async function checkBundle(body: Record<string, unknown>, handle: string): Promise<Checked | string> {
  const { public_key, encrypted_private_key, recovery_private_key } = body;
  if (typeof public_key !== "string" || public_key.length > MAX_PUBLIC) return "invalid_public_key";
  if (typeof encrypted_private_key !== "string" || encrypted_private_key.length > MAX_PRIVATE) return "invalid_private_key";
  if (recovery_private_key !== undefined && (typeof recovery_private_key !== "string" || recovery_private_key.length > MAX_PRIVATE))
    return "invalid_recovery_key";

  let pub: openpgp.Key;
  try { pub = await openpgp.readKey({ armoredKey: public_key }); } catch { return "invalid_public_key"; }
  if (pub.isPrivate()) return "public_key_is_private";
  const fingerprint = pub.getFingerprint();
  if (!pub.getUserIDs().some((id) => id.toLowerCase().includes(`<${handle}@${DOMAIN}>`))) return "user_id_mismatch";

  const lockedCopies = [encrypted_private_key, ...(typeof recovery_private_key === "string" ? [recovery_private_key] : [])];
  for (const armored of lockedCopies) {
    let priv: openpgp.PrivateKey;
    try { priv = await openpgp.readPrivateKey({ armoredKey: armored }); } catch { return "invalid_private_key"; }
    if (priv.getFingerprint() !== fingerprint) return "fingerprint_mismatch";
    // A private key stored unlocked would defeat the whole design.
    if (priv.isDecrypted()) return "private_key_not_encrypted";
  }
  return {
    fingerprint,
    publicKey: public_key,
    locked: encrypted_private_key,
    recovery: typeof recovery_private_key === "string" ? recovery_private_key : undefined,
  };
}

export async function saveMyIdentity(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const handle = user.handle?.toLowerCase();
  if (!handle || !HANDLE_RE.test(handle)) return json({ error: "account_has_no_handle" }, { status: 400 }, cors);

  const raw = await req.text();
  if (raw.length > 2 * MAX_PRIVATE + MAX_PUBLIC + 1024) return json({ error: "payload_too_large" }, { status: 413 }, cors);
  let body: Record<string, unknown>;
  try { body = JSON.parse(raw) as Record<string, unknown>; } catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const checked = await checkBundle(body, handle);
  if (typeof checked === "string") return json({ error: checked }, { status: 400 }, cors);

  const existing = (await dbSelect<KeyRow>(env, "user_keys", {
    select: "fingerprint",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  }))[0];
  const now = new Date().toISOString();

  if (!existing) {
    await dbInsert(env, "user_keys", {
      user_id: user.id,
      handle,
      fingerprint: checked.fingerprint,
      public_key: checked.publicKey,
      encrypted_private_key: checked.locked,
      recovery_private_key: checked.recovery ?? null,
    });
    void audit(env, user.id, "identity_created", { ...clientHints(req), metadata: { fingerprint: checked.fingerprint } });
    return json({ fingerprint: checked.fingerprint, created: true }, {}, cors);
  }

  if (existing.fingerprint === checked.fingerprint) {
    // Same key, re-locked (password change or new recovery phrase).
    const update: Record<string, unknown> = { encrypted_private_key: checked.locked, updated_at: now };
    if (checked.recovery) update.recovery_private_key = checked.recovery;
    await dbUpdate(env, "user_keys", { user_id: `eq.${user.id}` }, update);
    return json({ fingerprint: checked.fingerprint, created: false }, {}, cors);
  }

  // A different key makes anything encrypted to the old one unreadable; require intent.
  if (body.replace !== true) {
    return json({ error: "identity_exists", fingerprint: existing.fingerprint }, { status: 409 }, cors);
  }
  await dbUpdate(env, "user_keys", { user_id: `eq.${user.id}` }, {
    handle,
    fingerprint: checked.fingerprint,
    public_key: checked.publicKey,
    encrypted_private_key: checked.locked,
    recovery_private_key: checked.recovery ?? null,
    updated_at: now,
  });
  void audit(env, user.id, "identity_replaced", {
    ...clientHints(req),
    metadata: { old_fingerprint: existing.fingerprint, fingerprint: checked.fingerprint },
  });
  return json({ fingerprint: checked.fingerprint, created: true, replaced: true }, {}, cors);
}
