/**
 * Plan tier definitions, limits, and gating helpers.
 *
 * Free (community)  — basic discovery, 1 agent, 7 days history, no alerts
 * Guardian Pro      — 10 agents, 90 days history, real-time alerts
 * Operator          — unlimited agents, unlimited history, alerts, team features
 *
 * 14-day Pro trial automatically granted on signup. Trial users get full
 * Guardian Pro features. After expiry, downgraded to community unless
 * they have an active Stripe subscription.
 */

export type PlanName = "community" | "guardian_pro" | "operator";

export interface PlanLimits {
  maxAgents: number;
  scanHistoryDays: number;
  alertsEnabled: boolean;
  teamFeatures: boolean;
}

export const PLAN_LIMITS: Record<PlanName, PlanLimits> = {
  community: {
    maxAgents: 1,
    scanHistoryDays: 7,
    alertsEnabled: false,
    teamFeatures: false,
  },
  guardian_pro: {
    maxAgents: 10,
    scanHistoryDays: 90,
    alertsEnabled: true,
    teamFeatures: false,
  },
  operator: {
    maxAgents: 9999,
    scanHistoryDays: 36500, // ~100 years, effectively unlimited
    alertsEnabled: true,
    teamFeatures: true,
  },
};

export interface ProfileForPlan {
  plan: string;
  trial_ends_at: string | null;
  subscription_status: string | null;
  current_period_end: string | null;
}

/**
 * Given a profile row, return the plan the user effectively has right now.
 * Prefer paid plan; otherwise honor trial; otherwise community.
 */
export function getEffectivePlan(profile: ProfileForPlan | null | undefined): PlanName {
  if (!profile) return "community";

  // Active paid subscription wins
  const okStatuses = new Set(["active", "trialing"]);
  if (
    (profile.plan === "guardian_pro" || profile.plan === "operator") &&
    profile.subscription_status &&
    okStatuses.has(profile.subscription_status)
  ) {
    return profile.plan as PlanName;
  }

  // Trial period
  if (profile.trial_ends_at) {
    const ends = new Date(profile.trial_ends_at).getTime();
    if (Number.isFinite(ends) && ends > Date.now()) {
      return "guardian_pro";
    }
  }

  // Anything else falls back to community
  return "community";
}

export function trialDaysRemaining(profile: ProfileForPlan | null | undefined): number {
  if (!profile?.trial_ends_at) return 0;
  const ends = new Date(profile.trial_ends_at).getTime();
  if (!Number.isFinite(ends)) return 0;
  const ms = ends - Date.now();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

export function getLimits(plan: PlanName): PlanLimits {
  return PLAN_LIMITS[plan] ?? PLAN_LIMITS.community;
}

/** Build a 402 Payment Required response. */
export function planRequired(
  required: PlanName | PlanName[],
  current: PlanName,
  reason: string,
  cors: HeadersInit
): Response {
  const requiredArr = Array.isArray(required) ? required : [required];
  return new Response(
    JSON.stringify({
      error: "plan_required",
      reason,
      current_plan: current,
      required_plan: requiredArr,
      upgrade_url: "https://shadowcypher.site/?nav=pricing",
    }),
    {
      status: 402,
      headers: { "Content-Type": "application/json", ...cors },
    }
  );
}
