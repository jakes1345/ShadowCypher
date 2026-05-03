/**
 * Phase 4J — TOTP / 2FA via Supabase Auth MFA.
 *
 * Supabase has native MFA support — we surface it through our API so it shows up
 * in the dashboard alongside other settings. The actual enrollment / verification
 * happens client-side via supabase-js (passes the user's session JWT directly to
 * Supabase Auth). Our endpoints exist mainly to:
 *   - Read enrollment status from auth.mfa_factors via service-role
 *   - Audit-log enable/disable events
 *   - Return a "you have N TOTP factors" summary for /v1/me
 *
 * Endpoints:
 *   GET /v1/me/mfa  — list factors + status
 */

import type { Env } from "./index";

interface AuthedUser { id: string; email: string; }

interface MfaFactor {
  id: string;
  factor_type: string;        // 'totp' | 'phone'
  status: string;             // 'verified' | 'unverified'
  friendly_name: string | null;
  created_at: string;
  updated_at: string;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

export async function getMfaStatus(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  // Fetch the user's MFA factors via Supabase Admin API
  const url = `${env.SUPABASE_URL}/auth/v1/admin/users/${user.id}`;
  const resp = await fetch(url, {
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!resp.ok) {
    return json({ error: "supabase_admin_failed", status: resp.status }, { status: 500 }, cors);
  }
  const userData = (await resp.json()) as { factors?: MfaFactor[] };
  const factors = userData.factors || [];
  const verified = factors.filter((f) => f.status === "verified");
  return json({
    enabled: verified.length > 0,
    factor_count: verified.length,
    factors: verified.map((f) => ({
      id: f.id,
      type: f.factor_type,
      friendly_name: f.friendly_name,
      created_at: f.created_at,
    })),
  }, {}, cors);
}
