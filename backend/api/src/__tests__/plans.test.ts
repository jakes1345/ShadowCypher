import { describe, it, expect } from "vitest";
import {
  getEffectivePlan,
  trialDaysRemaining,
  getLimits,
  PLAN_LIMITS,
  type ProfileForPlan,
} from "../plans";

function futureIso(daysFromNow: number): string {
  const d = new Date(Date.now() + daysFromNow * 86_400_000);
  return d.toISOString();
}

function pastIso(daysAgo: number): string {
  return futureIso(-daysAgo);
}

// ── getEffectivePlan ──────────────────────────────────────────────────────────

describe("getEffectivePlan", () => {
  it("returns community for null input", () => {
    expect(getEffectivePlan(null)).toBe("community");
  });

  it("returns community for undefined input", () => {
    expect(getEffectivePlan(undefined)).toBe("community");
  });

  it("returns community when plan=community with no trial", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: null,
      subscription_status: null,
      current_period_end: null,
    };
    expect(getEffectivePlan(p)).toBe("community");
  });

  it("returns guardian_pro for active guardian_pro subscription", () => {
    const p: ProfileForPlan = {
      plan: "guardian_pro",
      trial_ends_at: null,
      subscription_status: "active",
      current_period_end: futureIso(30),
    };
    expect(getEffectivePlan(p)).toBe("guardian_pro");
  });

  it("returns operator for active operator subscription", () => {
    const p: ProfileForPlan = {
      plan: "operator",
      trial_ends_at: null,
      subscription_status: "active",
      current_period_end: futureIso(30),
    };
    expect(getEffectivePlan(p)).toBe("operator");
  });

  it("returns guardian_pro for trialing guardian_pro subscription", () => {
    const p: ProfileForPlan = {
      plan: "guardian_pro",
      trial_ends_at: futureIso(5),
      subscription_status: "trialing",
      current_period_end: futureIso(30),
    };
    expect(getEffectivePlan(p)).toBe("guardian_pro");
  });

  it("returns community when subscription_status=canceled (even with paid plan)", () => {
    const p: ProfileForPlan = {
      plan: "guardian_pro",
      trial_ends_at: null,
      subscription_status: "canceled",
      current_period_end: pastIso(5),
    };
    expect(getEffectivePlan(p)).toBe("community");
  });

  it("returns guardian_pro when community plan is in active trial", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: futureIso(7),
      subscription_status: null,
      current_period_end: null,
    };
    expect(getEffectivePlan(p)).toBe("guardian_pro");
  });

  it("returns community when trial_ends_at is in the past", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: pastIso(1),
      subscription_status: null,
      current_period_end: null,
    };
    expect(getEffectivePlan(p)).toBe("community");
  });

  it("returns community for malformed trial date", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: "not-a-date",
      subscription_status: null,
      current_period_end: null,
    };
    expect(getEffectivePlan(p)).toBe("community");
  });

  it("returns community when subscription_status=past_due", () => {
    const p: ProfileForPlan = {
      plan: "guardian_pro",
      trial_ends_at: null,
      subscription_status: "past_due",
      current_period_end: futureIso(5),
    };
    expect(getEffectivePlan(p)).toBe("community");
  });
});

// ── trialDaysRemaining ────────────────────────────────────────────────────────

describe("trialDaysRemaining", () => {
  it("returns 0 for null profile", () => {
    expect(trialDaysRemaining(null)).toBe(0);
  });

  it("returns 0 when trial_ends_at is null", () => {
    expect(trialDaysRemaining({ plan: "community", trial_ends_at: null, subscription_status: null, current_period_end: null })).toBe(0);
  });

  it("returns ~14 when trial ends in 14 days", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: futureIso(14),
      subscription_status: null,
      current_period_end: null,
    };
    const days = trialDaysRemaining(p);
    expect(days).toBeGreaterThanOrEqual(13);
    expect(days).toBeLessThanOrEqual(14);
  });

  it("returns 1 for a trial expiring in just under 24h", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: futureIso(0.9),
      subscription_status: null,
      current_period_end: null,
    };
    expect(trialDaysRemaining(p)).toBe(1);
  });

  it("returns 0 when trial already expired", () => {
    const p: ProfileForPlan = {
      plan: "community",
      trial_ends_at: pastIso(2),
      subscription_status: null,
      current_period_end: null,
    };
    expect(trialDaysRemaining(p)).toBe(0);
  });

  it("returns 0 for malformed date", () => {
    expect(trialDaysRemaining({ plan: "community", trial_ends_at: "bad-date", subscription_status: null, current_period_end: null })).toBe(0);
  });
});

// ── getLimits ─────────────────────────────────────────────────────────────────

describe("getLimits", () => {
  it("returns community limits", () => {
    const limits = getLimits("community");
    expect(limits.maxAgents).toBe(1);
    expect(limits.alertsEnabled).toBe(false);
    expect(limits.teamFeatures).toBe(false);
    expect(limits.scanHistoryDays).toBe(7);
  });

  it("returns guardian_pro limits", () => {
    const limits = getLimits("guardian_pro");
    expect(limits.maxAgents).toBe(10);
    expect(limits.alertsEnabled).toBe(true);
    expect(limits.teamFeatures).toBe(false);
    expect(limits.scanHistoryDays).toBe(90);
  });

  it("returns operator limits", () => {
    const limits = getLimits("operator");
    expect(limits.maxAgents).toBeGreaterThan(100);
    expect(limits.alertsEnabled).toBe(true);
    expect(limits.teamFeatures).toBe(true);
    expect(limits.scanHistoryDays).toBeGreaterThan(365);
  });

  it("PLAN_LIMITS contains exactly the three tiers", () => {
    const keys = Object.keys(PLAN_LIMITS);
    expect(keys).toContain("community");
    expect(keys).toContain("guardian_pro");
    expect(keys).toContain("operator");
    expect(keys).toHaveLength(3);
  });

  it("operator has the most agents of any plan", () => {
    expect(getLimits("operator").maxAgents).toBeGreaterThan(getLimits("guardian_pro").maxAgents);
    expect(getLimits("guardian_pro").maxAgents).toBeGreaterThan(getLimits("community").maxAgents);
  });
});
