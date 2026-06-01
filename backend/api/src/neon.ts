/**
 * Neon (PostgreSQL) helper for Cloudflare Workers.
 * Runs alongside Supabase — both active simultaneously.
 * Uses @neondatabase/serverless HTTP driver (no TCP, works in Workers).
 */

import { neon as neonHttp } from "@neondatabase/serverless";
import type { Env } from "./index";

function sql(env: Env) {
  return neonHttp(env.NEON_DATABASE_URL);
}

/**
 * Look up a user by api_key in Neon.
 * Returns the same shape as Supabase's findUserByKey so callers are interchangeable.
 */
export async function neonFindUserByKey(
  env: Env,
  key: string
): Promise<{ id: string; email: string; created_at: string; user_metadata: Record<string, unknown>; app_metadata: Record<string, unknown> } | null> {
  if (!env.NEON_DATABASE_URL) return null;
  try {
    const db = sql(env);
    const rows = await db`
      SELECT u.id, u.email, u.created_at, p.plan, p.handle
      FROM public.api_keys ak
      JOIN public.users u ON u.id = ak.user_id
      LEFT JOIN public.profiles p ON p.user_id = u.id
      WHERE ak.key = ${key} AND ak.revoked = false
      LIMIT 1
    `;
    if (!rows.length) return null;
    const r = rows[0];
    return {
      id: r.id,
      email: r.email,
      created_at: r.created_at,
      user_metadata: { api_key: key, plan: r.plan ?? "community", handle: r.handle ?? r.email.split("@")[0] },
      app_metadata: {},
    };
  } catch (e) {
    console.error("[neon] findUserByKey failed:", e);
    return null;
  }
}

/**
 * Mirror a new user + api_key into Neon (called after successful Supabase registration).
 */
export async function neonRegisterUser(env: Env, userId: string, email: string, apiKey: string): Promise<void> {
  if (!env.NEON_DATABASE_URL) return;
  try {
    const db = sql(env);
    await db`INSERT INTO public.users (id, email, password_hash) VALUES (${userId}, ${email}, '') ON CONFLICT (id) DO NOTHING`;
    await db`INSERT INTO public.profiles (user_id, email, handle, plan) VALUES (${userId}, ${email}, ${email.split("@")[0]}, 'community') ON CONFLICT (user_id) DO NOTHING`;
    await db`INSERT INTO public.api_keys (key, user_id) VALUES (${apiKey}, ${userId}) ON CONFLICT DO NOTHING`;
  } catch (e) {
    console.error("[neon] registerUser failed:", e);
  }
}

/**
 * Mirror an api_key rotation into Neon.
 */
export async function neonRotateKey(env: Env, userId: string, oldKey: string, newKey: string): Promise<void> {
  if (!env.NEON_DATABASE_URL) return;
  try {
    const db = sql(env);
    await db`UPDATE public.api_keys SET revoked = true WHERE user_id = ${userId} AND key = ${oldKey}`;
    await db`INSERT INTO public.api_keys (key, user_id) VALUES (${newKey}, ${userId}) ON CONFLICT DO NOTHING`;
  } catch (e) {
    console.error("[neon] rotateKey failed:", e);
  }
}

/**
 * Mirror a key revocation into Neon.
 */
export async function neonRevokeKey(env: Env, userId: string, key: string): Promise<void> {
  if (!env.NEON_DATABASE_URL) return;
  try {
    const db = sql(env);
    await db`UPDATE public.api_keys SET revoked = true WHERE user_id = ${userId} AND key = ${key}`;
  } catch (e) {
    console.error("[neon] revokeKey failed:", e);
  }
}
