import { describe, it, expect } from "vitest";
import { planFromPriceId, verifyStripeSignature } from "../billing";
import type { Env } from "../index";

const testEnv = {
  STRIPE_PRICE_GUARDIAN_PRO: "price_gp_monthly",
  STRIPE_PRICE_OPERATOR: "price_op_monthly",
  STRIPE_PRICE_GUARDIAN_PRO_ANNUAL: "price_gp_annual",
  STRIPE_PRICE_OPERATOR_ANNUAL: "price_op_annual",
} as unknown as Env;

// ── planFromPriceId ───────────────────────────────────────────────────────────

describe("planFromPriceId", () => {
  it("resolves guardian_pro monthly", () => {
    const result = planFromPriceId(testEnv, "price_gp_monthly");
    expect(result.plan).toBe("guardian_pro");
    expect(result.interval).toBe("month");
  });

  it("resolves operator monthly", () => {
    const result = planFromPriceId(testEnv, "price_op_monthly");
    expect(result.plan).toBe("operator");
    expect(result.interval).toBe("month");
  });

  it("resolves guardian_pro annual", () => {
    const result = planFromPriceId(testEnv, "price_gp_annual");
    expect(result.plan).toBe("guardian_pro");
    expect(result.interval).toBe("year");
  });

  it("resolves operator annual", () => {
    const result = planFromPriceId(testEnv, "price_op_annual");
    expect(result.plan).toBe("operator");
    expect(result.interval).toBe("year");
  });

  it("falls back to community for an unknown price ID", () => {
    const result = planFromPriceId(testEnv, "price_unknown_xyz");
    expect(result.plan).toBe("community");
    expect(result.interval).toBe("month");
  });

  it("falls back to community for an empty string price ID", () => {
    const result = planFromPriceId(testEnv, "");
    expect(result.plan).toBe("community");
  });
});

// ── verifyStripeSignature ─────────────────────────────────────────────────────

async function buildStripeHeader(payload: string, secret: string, tsOverride?: number): Promise<string> {
  const t = tsOverride ?? Math.floor(Date.now() / 1000);
  const signedPayload = `${t}.${payload}`;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sigBytes = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(signedPayload)));
  const v1 = Array.from(sigBytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `t=${t},v1=${v1}`;
}

describe("verifyStripeSignature", () => {
  const secret = "whsec_test_secret_1234567890abcdef";
  const payload = JSON.stringify({ type: "customer.subscription.updated", data: { object: {} } });

  it("accepts a valid signature with a current timestamp", async () => {
    const header = await buildStripeHeader(payload, secret);
    const valid = await verifyStripeSignature(payload, header, secret);
    expect(valid).toBe(true);
  });

  it("rejects a tampered payload", async () => {
    const header = await buildStripeHeader(payload, secret);
    const valid = await verifyStripeSignature(payload + "X", header, secret);
    expect(valid).toBe(false);
  });

  it("rejects a tampered signature", async () => {
    const header = await buildStripeHeader(payload, secret);
    const tampered = header.replace(/v1=[0-9a-f]{10}/, "v1=000000000000");
    const valid = await verifyStripeSignature(payload, tampered, secret);
    expect(valid).toBe(false);
  });

  it("rejects a signature produced with the wrong secret", async () => {
    const header = await buildStripeHeader(payload, "wrong_secret");
    const valid = await verifyStripeSignature(payload, header, secret);
    expect(valid).toBe(false);
  });

  it("rejects a timestamp older than 300 seconds", async () => {
    const oldTs = Math.floor(Date.now() / 1000) - 400;
    const header = await buildStripeHeader(payload, secret, oldTs);
    const valid = await verifyStripeSignature(payload, header, secret);
    expect(valid).toBe(false);
  });

  it("rejects a missing v1 field in the header", async () => {
    const t = Math.floor(Date.now() / 1000);
    const valid = await verifyStripeSignature(payload, `t=${t}`, secret);
    expect(valid).toBe(false);
  });

  it("rejects an empty header string", async () => {
    const valid = await verifyStripeSignature(payload, "", secret);
    expect(valid).toBe(false);
  });

  it("rejects a non-numeric timestamp", async () => {
    const valid = await verifyStripeSignature(payload, "t=notanumber,v1=aabbcc", secret);
    expect(valid).toBe(false);
  });

  it("accepts a timestamp within the 300s tolerance window", async () => {
    const recentTs = Math.floor(Date.now() / 1000) - 250;
    const header = await buildStripeHeader(payload, secret, recentTs);
    const valid = await verifyStripeSignature(payload, header, secret);
    expect(valid).toBe(true);
  });
});
