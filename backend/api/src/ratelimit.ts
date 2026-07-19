const _rl = new Map<string, number[]>();

export function rateLimit(key: string, maxReqs: number, windowMs: number): boolean {
  const now = Date.now();
  const hits = (_rl.get(key) ?? []).filter((t) => now - t < windowMs);
  if (hits.length >= maxReqs) return false;
  hits.push(now);
  _rl.set(key, hits);
  if (_rl.size > 10_000) {
    const oldest = [..._rl.entries()].sort((a, b) => (a[1][0] ?? 0) - (b[1][0] ?? 0));
    for (let i = 0; i < 1000; i++) _rl.delete(oldest[i][0]);
  }
  return true;
}

export function clearRateLimitState(): void {
  _rl.clear();
}
