/**
 * Phase 4L — referral program.
 *
 * Each user has a unique 8-character referral code. New signups attribute themselves
 * via /r/<code> (cookie set client-side, then claimed via POST /v1/referrals/claim
 * on first authenticated request).
 *
 * Reward model (simplest possible v1): when a referee subscribes to a paid plan,
 * the referrer gets +30 days extension on their trial_ends_at. Tracked in
 * public.referral_redemptions so we never double-pay.
 *
 * Endpoints:
 *   GET  /v1/referrals/me       — return my code + counts
 *   POST /v1/referrals/claim    — { code } — set referred_by on my profile (only once, only if I'm new)
 *
 * Internal: applyReferralReward() called from billing webhook on subscription.created.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate } from "./supabase";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

interface ProfileRow {
  user_id: string;
  email: string | null;
  referral_code: string;
  referred_by: string | null;
  trial_ends_at: string | null;
  created_at: string;
}

export async function getMyReferral(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const profiles = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id,referral_code,referred_by",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!profiles[0]) return json({ error: "profile_not_found" }, { status: 404 }, cors);

  // Count people I've referred
  const referred = await dbSelect<{ user_id: string }>(env, "profiles", {
    select: "user_id",
    filters: { referred_by: `eq.${user.id}` },
    limit: 100,
  });
  // Count completed redemptions
  const redemptions = await dbSelect<{ id: string }>(env, "referral_redemptions", {
    select: "id",
    filters: { referrer_id: `eq.${user.id}` },
    limit: 100,
  });

  const code = profiles[0].referral_code;
  return json({
    code,
    share_url: `https://shadowcypher.site/r/${code}`,
    signups_attributed: referred.length,
    rewards_earned: redemptions.length,
    days_credited_total: redemptions.length * 30,
  }, {}, cors);
}

export async function claimReferral(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { code?: string };
  if (!body.code) return json({ error: "code_required" }, { status: 400 }, cors);
  const code = body.code.trim().toLowerCase();

  // Look up MY profile first to check eligibility
  const me = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id,referral_code,referred_by,created_at",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!me[0]) return json({ error: "profile_not_found" }, { status: 404 }, cors);

  if (me[0].referred_by) return json({ error: "already_referred" }, { status: 409 }, cors);
  if (me[0].referral_code === code) return json({ error: "cannot_self_refer" }, { status: 400 }, cors);

  // Only allow attribution within 7 days of signup (prevents cold backfill abuse)
  const ageMs = Date.now() - new Date(me[0].created_at).getTime();
  if (ageMs > 7 * 86400000) {
    return json({ error: "claim_window_expired" }, { status: 410 }, cors);
  }

  const referrer = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id",
    filters: { referral_code: `eq.${code}` },
    limit: 1,
  });
  if (!referrer[0]) return json({ error: "invalid_code" }, { status: 404 }, cors);

  await dbUpdate(env, "profiles", { user_id: `eq.${user.id}` }, { referred_by: referrer[0].user_id });
  return json({ ok: true, referrer_attributed: true }, {}, cors);
}

/**
 * Called from billing webhook when a referee starts paying.
 * Extends the referrer's trial by 30 days (or stacks if already in trial).
 */
export async function applyReferralReward(env: Env, refereeUserId: string): Promise<void> {
  // Already redeemed?
  const existing = await dbSelect<{ id: string }>(env, "referral_redemptions", {
    select: "id",
    filters: { referee_id: `eq.${refereeUserId}` },
    limit: 1,
  });
  if (existing[0]) return;

  // Who referred this person?
  const referee = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id,referred_by",
    filters: { user_id: `eq.${refereeUserId}` },
    limit: 1,
  });
  const referrerId = referee[0]?.referred_by;
  if (!referrerId) return;

  // Pull referrer's current trial_ends_at, extend 30 days
  const referrer = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id,trial_ends_at",
    filters: { user_id: `eq.${referrerId}` },
    limit: 1,
  });
  if (!referrer[0]) return;

  const currentEnd = referrer[0].trial_ends_at ? new Date(referrer[0].trial_ends_at).getTime() : Date.now();
  const newEnd = new Date(Math.max(currentEnd, Date.now()) + 30 * 86400000).toISOString();

  await dbUpdate(env, "profiles", { user_id: `eq.${referrerId}` }, { trial_ends_at: newEnd });
  await dbInsert(env, "referral_redemptions", {
    referrer_id: referrerId,
    referee_id: refereeUserId,
    credit_days: 30,
  }).catch((e) => console.warn("[referral] redemption insert failed", e instanceof Error ? e.message : e));
}
