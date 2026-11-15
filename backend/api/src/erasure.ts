/**
 * Account erasure: everything "delete my account" has to remove.
 *
 * Deleting the Supabase auth user cascades to the tables that reference it,
 * but that leaves a lot behind: files in R2, chat and mission rows that carry
 * a user id without a foreign key, the Neon mirror (which key lookups read
 * first), and a Stripe customer that would keep being billed.
 *
 * Steps run in an order that is safe to repeat. Each one is a no-op when its
 * data is already gone, and the auth user goes last, so a failure part-way
 * leaves an account that can still sign in and try again.
 */

import type { Env } from "./index";
import { dbDelete, dbSelect, dbUpdate } from "./supabase";
import { neonDeleteUser } from "./neon";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Upper bound on listing passes when emptying a prefix: 5,000 passes of 1,000 objects. */
const MAX_DELETE_PASSES = 5000;

/** Tables holding a user's rows with no foreign key to auth.users, in delete order. */
const UNLINKED_TABLES = ["chat_reactions", "chat_messages", "chat_presence", "dm_read_receipts", "missions"] as const;

export interface ErasureReport {
  /** "cancelled": the Stripe customer and any subscription were removed. */
  billing: "cancelled" | "none";
  files: number;
  rows: Record<string, number>;
}

/** Names the step that failed, so the caller can report it without leaking provider detail. */
export class ErasureError extends Error {
  constructor(public readonly step: string, cause: unknown) {
    super(`erasure_failed:${step}:${cause instanceof Error ? cause.message : String(cause)}`);
    this.name = "ErasureError";
  }
}

async function step<T>(name: string, run: () => Promise<T>): Promise<T> {
  try {
    return await run();
  } catch (e) {
    throw new ErasureError(name, e);
  }
}

/** Deletes every object under the user's prefix: uploads, docs and sheets. */
export async function deleteUserFiles(env: Env, userId: string): Promise<number> {
  if (!UUID_RE.test(userId)) throw new Error("invalid_user_id");
  if (!env.SHADOW_FILES) return 0;
  // Always take the first page again rather than following a cursor: the
  // listing shrinks as we delete, and a cursor into a shrinking list can skip keys.
  let deleted = 0;
  for (let pass = 0; pass < MAX_DELETE_PASSES; pass++) {
    const page = await env.SHADOW_FILES.list({ prefix: `${userId}/`, limit: 1000 });
    const keys = page.objects.map((o) => o.key);
    if (keys.length === 0) return deleted;
    await env.SHADOW_FILES.delete(keys);
    deleted += keys.length;
  }
  throw new Error("file_delete_did_not_finish");
}

/**
 * Deletes the Stripe customer, which also cancels any active subscription at once.
 * Stripe keeps its own invoice and payment records as the law requires of it.
 */
async function cancelBilling(env: Env, userId: string): Promise<ErasureReport["billing"]> {
  const rows = await dbSelect<{ stripe_customer_id: string | null }>(env, "profiles", {
    select: "stripe_customer_id",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  const customerId = rows[0]?.stripe_customer_id;
  if (!customerId) return "none";
  if (!env.STRIPE_SECRET_KEY) throw new Error("stripe_not_configured");
  const resp = await fetch(`https://api.stripe.com/v1/customers/${encodeURIComponent(customerId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}` },
  });
  // 404: a previous attempt already removed it.
  if (!resp.ok && resp.status !== 404) throw new Error(`stripe_${resp.status}`);
  return "cancelled";
}

async function deleteAuthUser(env: Env, userId: string): Promise<void> {
  const resp = await fetch(`${env.SUPABASE_URL}/auth/v1/admin/users/${userId}`, {
    method: "DELETE",
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!resp.ok && resp.status !== 404) throw new Error(`auth_delete_${resp.status}`);
}

/**
 * Removes a user and everything stored for them. Throws ErasureError naming
 * the first step that failed; nothing after that step has run.
 */
export async function eraseUser(env: Env, userId: string): Promise<ErasureReport> {
  if (!UUID_RE.test(userId)) throw new ErasureError("validate", "invalid_user_id");

  // Billing first: whatever else happens, a deleted account must stop being charged.
  const billing = await step("billing", () => cancelBilling(env, userId));
  const files = await step("files", () => deleteUserFiles(env, userId));

  const rows: Record<string, number> = {};
  for (const table of UNLINKED_TABLES) {
    rows[table] = await step(table, () => dbDelete(env, table, { user_id: `eq.${userId}` }));
  }
  // Rooms the user created stay for the people still in them, without the creator's id.
  await step("chat_rooms", async () => {
    try {
      await dbUpdate(env, "chat_rooms", { created_by: `eq.${userId}` }, { created_by: null });
    } catch (e) {
      if (!String(e).includes(":404:")) throw e;
    }
  });

  // The mirror before the auth user: key lookups read Neon first, so a row
  // surviving there would keep the deleted account's API key working.
  await step("mirror", () => neonDeleteUser(env, userId));

  // Last. Cascades through every table that references auth.users.
  await step("auth", () => deleteAuthUser(env, userId));

  return { billing, files, rows };
}
