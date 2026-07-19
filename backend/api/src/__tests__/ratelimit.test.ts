import { describe, it, expect, beforeEach } from "vitest";
import { rateLimit, clearRateLimitState } from "../ratelimit";

beforeEach(() => {
  clearRateLimitState();
});

describe("rateLimit", () => {
  it("allows the first request", () => {
    expect(rateLimit("rl-test-1", 5, 60_000)).toBe(true);
  });

  it("allows requests up to the limit", () => {
    const key = "rl-test-2";
    for (let i = 0; i < 5; i++) {
      expect(rateLimit(key, 5, 60_000)).toBe(true);
    }
  });

  it("blocks the request that exceeds the limit", () => {
    const key = "rl-test-3";
    for (let i = 0; i < 5; i++) rateLimit(key, 5, 60_000);
    expect(rateLimit(key, 5, 60_000)).toBe(false);
  });

  it("blocks all subsequent requests once limit is hit", () => {
    const key = "rl-test-4";
    for (let i = 0; i < 3; i++) rateLimit(key, 3, 60_000);
    expect(rateLimit(key, 3, 60_000)).toBe(false);
    expect(rateLimit(key, 3, 60_000)).toBe(false);
  });

  it("uses separate counters for different keys", () => {
    const a = "rl-test-5a";
    const b = "rl-test-5b";
    for (let i = 0; i < 3; i++) rateLimit(a, 3, 60_000);
    expect(rateLimit(a, 3, 60_000)).toBe(false);
    expect(rateLimit(b, 3, 60_000)).toBe(true);
  });

  it("allows requests again after the window expires", async () => {
    const key = "rl-test-6";
    for (let i = 0; i < 2; i++) rateLimit(key, 2, 50);
    expect(rateLimit(key, 2, 50)).toBe(false);
    await new Promise((r) => setTimeout(r, 60));
    expect(rateLimit(key, 2, 50)).toBe(true);
  });

  it("maxReqs=1 allows exactly one request per window", () => {
    const key = "rl-test-7";
    expect(rateLimit(key, 1, 60_000)).toBe(true);
    expect(rateLimit(key, 1, 60_000)).toBe(false);
  });

  it("handles many concurrent keys without interference", () => {
    for (let i = 0; i < 100; i++) {
      const key = `rl-test-bulk-${i}`;
      expect(rateLimit(key, 1, 60_000)).toBe(true);
      expect(rateLimit(key, 1, 60_000)).toBe(false);
    }
  });

  it("sliding window slides: old hits drop off, new requests flow", async () => {
    const key = "rl-test-8";
    // 2 hits in the window
    rateLimit(key, 3, 80);
    rateLimit(key, 3, 80);
    // wait for those 2 to expire
    await new Promise((r) => setTimeout(r, 90));
    // now we can do 3 more
    expect(rateLimit(key, 3, 80)).toBe(true);
    expect(rateLimit(key, 3, 80)).toBe(true);
    expect(rateLimit(key, 3, 80)).toBe(true);
    expect(rateLimit(key, 3, 80)).toBe(false);
  });
});
