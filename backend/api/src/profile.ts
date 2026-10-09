/**
 * User profiles — public identity cards for team members.
 *
 * GET  /v1/profile/:handle  — public, no auth required
 * PATCH /v1/me/profile       — update own profile (authed)
 *
 * Supabase table DDL:
 * create table user_profiles (
 *   user_id    uuid primary key references auth.users(id) on delete cascade,
 *   handle     text,
 *   bio        text,
 *   avatar_url text,
 *   website    text,
 *   twitter    text,
 *   github     text,
 *   discord    text,
 *   location   text,
 *   is_public  boolean default true,
 *   updated_at timestamptz default now()
 * );
 */

import type { Env } from "./index";
import { dbSelect, dbUpsert } from "./supabase";

interface SupabaseAuthUser {
  id: string;
  email: string;
  created_at: string;
  user_metadata?: { handle?: string };
}

interface UserProfile {
  user_id: string;
  handle: string | null;
  bio: string | null;
  avatar_url: string | null;
  website: string | null;
  twitter: string | null;
  github: string | null;
  discord: string | null;
  location: string | null;
  is_public: boolean;
  updated_at: string;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });

async function lookupUserByHandle(env: Env, handle: string): Promise<SupabaseAuthUser | null> {
  const email = `${handle.toLowerCase().replace(/[^a-z0-9_-]/g, "")}@shadowcypher.site`;
  const resp = await fetch(
    `${env.SUPABASE_URL}/auth/v1/admin/users?email=${encodeURIComponent(email)}`,
    {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      },
    }
  );
  if (!resp.ok) return null;
  const body = (await resp.json()) as { users?: SupabaseAuthUser[] };
  return body.users?.[0] ?? null;
}

/** GET /v1/profile/:handle — no auth required */
export async function getProfile(
  _req: Request,
  env: Env,
  handle: string,
  cors: HeadersInit
): Promise<Response> {
  const cleaned = handle.toLowerCase().replace(/[^a-z0-9_-]/g, "");
  if (!cleaned) return json({ error: "invalid_handle" }, { status: 400 }, cors);

  const authUser = await lookupUserByHandle(env, cleaned);
  if (!authUser) return json({ error: "user_not_found" }, { status: 404 }, cors);

  const profiles = await dbSelect<UserProfile>(env, "user_profiles", {
    filters: { user_id: `eq.${authUser.id}` },
    limit: 1,
  }).catch(() => [] as UserProfile[]);

  const profile = profiles[0];
  const resolvedHandle = profile?.handle
    ?? authUser.user_metadata?.handle
    ?? authUser.email.split("@")[0];

  if (!profile || !profile.is_public) {
    return json({
      handle: resolvedHandle,
      joined_at: authUser.created_at,
    }, {}, cors);
  }

  return json({
    handle: resolvedHandle,
    bio: profile.bio,
    avatar_url: profile.avatar_url,
    website: profile.website,
    twitter: profile.twitter,
    github: profile.github,
    discord: profile.discord,
    location: profile.location,
    joined_at: authUser.created_at,
    updated_at: profile.updated_at,
  }, {}, cors);
}

/** PATCH /v1/me/profile — authed */
export async function updateProfile(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit
): Promise<Response> {
  let body: Partial<{
    bio: string;
    avatar_url: string;
    website: string;
    twitter: string;
    github: string;
    discord: string;
    location: string;
    is_public: boolean;
  }>;
  try { body = await req.json() as typeof body; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  if (body.bio != null && body.bio.length > 280) {
    return json({ error: "bio_too_long", max: 280 }, { status: 400 }, cors);
  }
  if (body.avatar_url !== undefined && body.avatar_url && !body.avatar_url.startsWith("https://")) {
    return json({ error: "avatar_url_must_be_https" }, { status: 400 }, cors);
  }

  // Derive handle from user email/metadata
  const handle = user.email.split("@")[0];

  const row: Record<string, unknown> = {
    user_id: user.id,
    handle,
    updated_at: new Date().toISOString(),
  };
  if (body.bio !== undefined)        row.bio        = body.bio        || null;
  if (body.avatar_url !== undefined) row.avatar_url = body.avatar_url || null;
  if (body.website !== undefined)    row.website    = body.website    || null;
  if (body.twitter !== undefined)    row.twitter    = (body.twitter || "").replace(/^@/, "") || null;
  if (body.github !== undefined)     row.github     = body.github     || null;
  if (body.discord !== undefined)    row.discord    = body.discord    || null;
  if (body.location !== undefined)   row.location   = body.location   || null;
  if (body.is_public !== undefined)  row.is_public  = !!body.is_public;

  const profile = await dbUpsert<UserProfile>(env, "user_profiles", row, "user_id");
  return json({ ok: true, profile }, {}, cors);
}
