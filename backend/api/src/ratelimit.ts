/**
 * KV-backed rate limiter using a fixed-window counter.
 *
 * Each window is identified by `${key}:${Math.floor(Date.now() / windowMs)}`.
 * We store the hit count in KV with a TTL of 2× the window so old entries
 * expire automatically. Reads the current count, rejects if already at the
 * limit, then increments — accepted by rate-limiter semantics (a small burst
 * window exists between read and write, which is acceptable for abuse defence).
 *
 * Falls back to an in-process Map only when KV is unavailable (local dev).
 */

const _fallback = new Map<string, number[]>();

export async function rateLimit(
  kv: KVNamespace | undefined,
  key: string,
  maxReqs: number,
  windowMs: number,
): Promise<boolean> {
  if (kv) {
    return kvRateLimit(kv, key, maxReqs, windowMs);
  }
  return memRateLimit(key, maxReqs, windowMs);
}

async function kvRateLimit(
  kv: KVNamespace,
  key: string,
  maxReqs: number,
  windowMs: number,
): Promise<boolean> {
  const window = Math.floor(Date.now() / windowMs);
  const kvKey = `rl:${key}:${window}`;
  const ttlSeconds = Math.ceil((windowMs * 2) / 1000);

  const raw = await kv.get(kvKey);
  const count = raw === null ? 0 : parseInt(raw, 10);

  if (count >= maxReqs) return false;

  // Best-effort increment — if the put races with another isolate we may
  // allow one extra request, which is acceptable for rate-limit purposes.
  await kv.put(kvKey, String(count + 1), { expirationTtl: ttlSeconds });
  return true;
}

function memRateLimit(key: string, maxReqs: number, windowMs: number): boolean {
  const now = Date.now();
  const hits = (_fallback.get(key) ?? []).filter((t) => now - t < windowMs);
  if (hits.length >= maxReqs) return false;
  hits.push(now);
  _fallback.set(key, hits);
  if (_fallback.size > 10_000) {
    const oldest = [..._fallback.entries()].sort((a, b) => (a[1][0] ?? 0) - (b[1][0] ?? 0));
    for (let i = 0; i < 1_000; i++) _fallback.delete(oldest[i][0]);
  }
  return true;
}

/** Exposed for tests only — clears the in-process fallback state. */
export function clearRateLimitState(): void {
  _fallback.clear();
}
