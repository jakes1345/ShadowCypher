import { describe, it, expect, vi, afterEach } from "vitest";
import { fakeBackend } from "./helpers/fake_backend";
import { purgeExpiredScans, retentionDays, retentionPlan } from "../retention";
import { getEffectivePlan, type ProfileForPlan } from "../plans";

const NOW = Date.parse("2026-11-14T12:00:00Z");
const DAY = 86_400_000;
const daysAgo = (n: number) => new Date(NOW - n * DAY).toISOString();
const inDays = (n: number) => new Date(Date.now() + n * DAY).toISOString();

const profile = (p: Partial<ProfileForPlan>): ProfileForPlan => ({
  plan: "community", trial_ends_at: null, subscription_status: null, current_period_end: null, ...p,
});

afterEach(() => vi.unstubAllGlobals());

describe("retentionDays", () => {
  it("is 7 days on the free tier, and for an account with no profile", () => {
    expect(retentionDays(profile({}))).toBe(7);
    expect(retentionDays(null)).toBe(7);
  });

  it("is 90 days during the trial and on Guardian Pro", () => {
    expect(retentionDays(profile({ trial_ends_at: inDays(3) }))).toBe(90);
    expect(retentionDays(profile({ plan: "guardian_pro", subscription_status: "active" }))).toBe(90);
  });

  it("keeps everything on Operator", () => {
    expect(retentionDays(profile({ plan: "operator", subscription_status: "active" }))).toBeNull();
  });

  it("drops to 7 days once the trial has ended or the subscription is cancelled", () => {
    expect(retentionDays(profile({ trial_ends_at: new Date(Date.now() - DAY).toISOString() }))).toBe(7);
    expect(retentionDays(profile({ plan: "community", subscription_status: "canceled" }))).toBe(7);
  });

  it("keeps the paid window while Stripe is still retrying a failed payment", () => {
    expect(retentionDays(profile({ plan: "guardian_pro", subscription_status: "past_due" }))).toBe(90);
    expect(retentionDays(profile({ plan: "operator", subscription_status: "past_due" }))).toBeNull();
  });

  it("is never narrower than what the user is allowed to see", () => {
    const rank = { community: 0, guardian_pro: 1, operator: 2 } as const;
    for (const plan of ["community", "guardian_pro", "operator"]) {
      for (const status of [null, "active", "trialing", "past_due", "canceled", "unpaid", "incomplete"]) {
        for (const trial of [null, inDays(5), new Date(Date.now() - 5 * DAY).toISOString()]) {
          const p = profile({ plan, subscription_status: status, trial_ends_at: trial });
          expect(rank[retentionPlan(p)]).toBeGreaterThanOrEqual(rank[getEffectivePlan(p)]);
        }
      }
    }
  });
});

describe("purgeExpiredScans", () => {
  const FREE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const PRO = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const OPERATOR = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

  it("deletes each owner's scans past their window and leaves the rest", async () => {
    const be = fakeBackend({
      tables: {
        profiles: [
          { user_id: FREE, plan: "community", trial_ends_at: null, subscription_status: null, current_period_end: null },
          { user_id: PRO, plan: "guardian_pro", trial_ends_at: null, subscription_status: "active", current_period_end: null },
          { user_id: OPERATOR, plan: "operator", trial_ends_at: null, subscription_status: "active", current_period_end: null },
        ],
        scans: [
          { id: "f-new", user_id: FREE, started_at: daysAgo(6) },
          { id: "f-old", user_id: FREE, started_at: daysAgo(8) },
          { id: "p-mid", user_id: PRO, started_at: daysAgo(8) },
          { id: "p-edge", user_id: PRO, started_at: daysAgo(89) },
          { id: "p-old", user_id: PRO, started_at: daysAgo(91) },
          { id: "o-ancient", user_id: OPERATOR, started_at: daysAgo(900) },
        ],
      },
    });
    vi.stubGlobal("fetch", be.fetch);

    const result = await purgeExpiredScans(be.env, NOW);

    expect(result).toEqual({ profiles: 3, deleted: 2 });
    expect(be.tables.scans.map((s) => s.id).sort()).toEqual(["f-new", "o-ancient", "p-edge", "p-mid"]);
  });

  it("sends ids in batches so the request never grows with the user count", async () => {
    const profiles = Array.from({ length: 250 }, (_, i) => ({
      user_id: `aaaaaaaa-aaaa-4aaa-8aaa-${String(i).padStart(12, "0")}`,
      plan: "community", trial_ends_at: null, subscription_status: null, current_period_end: null,
    }));
    const be = fakeBackend({ tables: { profiles, scans: [{ id: "old", user_id: profiles[249].user_id, started_at: daysAgo(30) }] } });
    vi.stubGlobal("fetch", be.fetch);

    const result = await purgeExpiredScans(be.env, NOW);

    expect(result).toEqual({ profiles: 250, deleted: 1 });
    expect(be.calls.filter((c) => c === "DELETE scans")).toHaveLength(3);
    expect(be.tables.scans).toEqual([]);
  });

  it("does nothing when there is nobody to purge for", async () => {
    const be = fakeBackend({ tables: { profiles: [], scans: [{ id: "s", user_id: FREE, started_at: daysAgo(400) }] } });
    vi.stubGlobal("fetch", be.fetch);
    expect(await purgeExpiredScans(be.env, NOW)).toEqual({ profiles: 0, deleted: 0 });
    expect(be.calls.includes("DELETE scans")).toBe(false);
  });
});
