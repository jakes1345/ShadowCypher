/**
 * Mail at rest, encrypted to the mailbox owner's identity key.
 *
 * Every copy of a message the Worker stores (inbound from the internet, internal
 * delivery, and the sender's own sent copy) is sealed to the OpenPGP public key of
 * the account it is stored for, when that account has one (POST /v1/identity/me).
 * The body then lives only in `body_pgp`; `body_text` and `body_html` stay empty,
 * and only the owner's browser, holding the unlocked private key, can read it.
 *
 * Mail from outside arrives in the clear over SMTP, so the Worker sees it once on
 * the way in, as any zero-access mail host does. It is never written in the clear
 * for an account with a key. Subject, sender and recipient stay readable: the inbox
 * list, search and notifications use them.
 *
 * Accounts without an identity key keep the old plaintext columns.
 */

import * as openpgp from "openpgp";
import type { Env } from "./index";
import { dbSelect } from "./supabase";

/** What the sealed message holds, before armoring. */
export interface SealedBody {
  v: 1;
  text: string | null;
  html: string | null;
}

export interface BodyColumns {
  body_text: string | null;
  body_html: string | null;
  body_pgp: string | null;
}

/** The armored public key for [userId], or null when the account has none. */
export async function mailboxKey(env: Env, userId: string): Promise<string | null> {
  const rows = await dbSelect<{ public_key: string }>(env, "user_keys", {
    select: "public_key",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return rows[0]?.public_key ?? null;
}

/** Encrypts the two bodies to [armoredPublicKey] as one armored OpenPGP message. */
export async function sealBody(armoredPublicKey: string, text: string | null, html: string | null): Promise<string> {
  const key = await openpgp.readKey({ armoredKey: armoredPublicKey });
  const payload: SealedBody = { v: 1, text, html };
  const message = await openpgp.createMessage({ text: JSON.stringify(payload) });
  return (await openpgp.encrypt({ message, encryptionKeys: key, format: "armored" })) as string;
}

/**
 * The body columns to store for [userId]: sealed when the account has a key,
 * plaintext otherwise. A key that cannot be used (it was checked when it was
 * saved, so this should not happen) falls back to plaintext rather than losing
 * the message, and says so in the log.
 */
export async function bodyColumnsFor(env: Env, userId: string, text: string | null, html: string | null): Promise<BodyColumns> {
  let key: string | null = null;
  try {
    key = await mailboxKey(env, userId);
  } catch (e) {
    console.error("mail_crypto: key lookup failed", e);
  }
  if (!key) return { body_text: text, body_html: html, body_pgp: null };
  try {
    return { body_text: null, body_html: null, body_pgp: await sealBody(key, text, html) };
  } catch (e) {
    console.error("mail_crypto: sealing failed, storing in the clear", e);
    return { body_text: text, body_html: html, body_pgp: null };
  }
}

/** The preview a webhook or push notification may carry: none for sealed mail. */
export function previewFor(cols: BodyColumns, text: string | null): string {
  if (cols.body_pgp) return "";
  return (text ?? "").trim().slice(0, 280).replace(/\s+/g, " ");
}
