import { describe, it, expect, beforeEach } from "vitest";
import { rateLimit, clearRateLimitState } from "../ratelimit";

// Tests exercise the in-memory fallback path (kv = undefined).
// KV-backed behaviour is integration-tested against a real KV namespace.

beforeEach(() => {
  clearRateLimitState();
});

describe("rateLimit", () => {
  it("allows the first request", async () => {
    expect(await rateLimit(undefined, "rl-test-1", 5, 60_000)).toBe(true);
  });

  it("allows requests up to the limit", async () => {
    const key = "rl-test-2";
    for (let i = 0; i < 5; i++) {
      expect(await rateLimit(undefined, key, 5, 60_000)).toBe(true);
    }
  });

  it("blocks the request that exceeds the limit", async () => {
    const key = "rl-test-3";
    for (let i = 0; i < 5; i++) await rateLimit(undefined, key, 5, 60_000);
    expect(await rateLimit(undefined, key, 5, 60_000)).toBe(false);
  });

  it("blocks all subsequent requests once limit is hit", async () => {
    const key = "rl-test-4";
    for (let i = 0; i < 3; i++) await rateLimit(undefined, key, 3, 60_000);
    expect(await rateLimit(undefined, key, 3, 60_000)).toBe(false);
    expect(await rateLimit(undefined, key, 3, 60_000)).toBe(false);
  });

  it("uses separate counters for different keys", async () => {
    const a = "rl-test-5a";
    const b = "rl-test-5b";
    for (let i = 0; i < 3; i++) await rateLimit(undefined, a, 3, 60_000);
    expect(await rateLimit(undefined, a, 3, 60_000)).toBe(false);
    expect(await rateLimit(undefined, b, 3, 60_000)).toBe(true);
  });

  it("allows requests again after the window expires", async () => {
    const key = "rl-test-6";
    for (let i = 0; i < 2; i++) await rateLimit(undefined, key, 2, 50);
    expect(await rateLimit(undefined, key, 2, 50)).toBe(false);
    await new Promise((r) => setTimeout(r, 60));
    expect(await rateLimit(undefined, key, 2, 50)).toBe(true);
  });

  it("maxReqs=1 allows exactly one request per window", async () => {
    const key = "rl-test-7";
    expect(await rateLimit(undefined, key, 1, 60_000)).toBe(true);
    expect(await rateLimit(undefined, key, 1, 60_000)).toBe(false);
  });

  it("handles many concurrent keys without interference", async () => {
    for (let i = 0; i < 100; i++) {
      const key = `rl-test-bulk-${i}`;
      expect(await rateLimit(undefined, key, 1, 60_000)).toBe(true);
      expect(await rateLimit(undefined, key, 1, 60_000)).toBe(false);
    }
  });

  it("sliding window slides: old hits drop off, new requests flow", async () => {
    const key = "rl-test-8";
    await rateLimit(undefined, key, 3, 80);
    await rateLimit(undefined, key, 3, 80);
    await new Promise((r) => setTimeout(r, 90));
    expect(await rateLimit(undefined, key, 3, 80)).toBe(true);
    expect(await rateLimit(undefined, key, 3, 80)).toBe(true);
    expect(await rateLimit(undefined, key, 3, 80)).toBe(true);
    expect(await rateLimit(undefined, key, 3, 80)).toBe(false);
  });
});
