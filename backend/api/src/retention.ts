/**
 * Scan-history retention.
 *
 * Each plan keeps scan history for a set number of days (PLAN_LIMITS in
 * plans.ts). Reads already hide anything older; this job deletes it, so the
 * limit is what is actually stored and not only what is shown.
 */

import type { Env } from "./index";
import { getEffectivePlan, getLimits, type PlanName, type ProfileForPlan } from "./plans";
import { dbDelete, dbSelectAll } from "./supabase";

/** PLAN_LIMITS uses a value this large to mean "keep everything". */
const KEEP_FOREVER_DAYS = 36500;
const DAY_MS = 86_400_000;
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ID_CHUNK = 100;

const RANK: Record<PlanName, number> = { community: 0, guardian_pro: 1, operator: 2 };

/**
 * The plan whose retention window applies to stored history.
 *
 * Never narrower than what the user can currently see. It is wider in one
 * case: while Stripe is still retrying a failed payment the subscription is
 * "past_due", paid features are paused, but the paid plan's history is kept so
 * that settling the invoice brings everything back.
 */
export function retentionPlan(profile: ProfileForPlan | null | undefined): PlanName {
  const effective = getEffectivePlan(profile);
  if (
    profile &&
    profile.subscription_status === "past_due" &&
    (profile.plan === "guardian_pro" || profile.plan === "operator") &&
    RANK[profile.plan] > RANK[effective]
  ) {
    return profile.plan;
  }
  return effective;
}

/** Days of scan history to keep for this profile, or null to keep everything. */
export function retentionDays(profile: ProfileForPlan | null | undefined): number | null {
  const days = getLimits(retentionPlan(profile)).scanHistoryDays;
  return days >= KEEP_FOREVER_DAYS ? null : days;
}

interface ProfileRow extends ProfileForPlan {
  user_id: string;
}

export interface PurgeResult {
  profiles: number;
  deleted: number;
}

/** Deletes every scan older than its owner's retention window. */
export async function purgeExpiredScans(env: Env, now: number = Date.now()): Promise<PurgeResult> {
  const { rows, truncated } = await dbSelectAll<ProfileRow>(env, "profiles", {
    select: "user_id,plan,trial_ends_at,subscription_status,current_period_end",
    order: "user_id.asc",
    maxRows: 500_000,
  });
  if (truncated) console.warn("[retention] profile list truncated; later accounts wait for the next run");

  const byDays = new Map<number, string[]>();
  for (const p of rows) {
    if (!UUID_RE.test(p.user_id)) continue;
    const days = retentionDays(p);
    if (days === null) continue;
    const ids = byDays.get(days);
    if (ids) ids.push(p.user_id);
    else byDays.set(days, [p.user_id]);
  }

  let deleted = 0;
  for (const [days, ids] of byDays) {
    const cutoff = new Date(now - days * DAY_MS).toISOString();
    for (let i = 0; i < ids.length; i += ID_CHUNK) {
      deleted += await dbDelete(env, "scans", {
        user_id: `in.(${ids.slice(i, i + ID_CHUNK).join(",")})`,
        started_at: `lt.${cutoff}`,
      });
    }
  }
  return { profiles: rows.length, deleted };
}
