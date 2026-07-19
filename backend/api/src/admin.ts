/**
 * Admin endpoints — only accessible to shadow@shadowcypher.site.
 *
 * GET /v1/admin/overview  — platform stats (users, agents, missions)
 * GET /v1/admin/users     — paginated user list with plan data
 */

import type { Env } from "./index";
import { dbSelect } from "./supabase";
import { getEffectivePlan, type ProfileForPlan } from "./plans";

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });

const ADMIN_EMAIL = "shadow@shadowcypher.site";

function requireAdmin(user: { id: string; email: string }, cors: HeadersInit): Response | null {
  if (user.email !== ADMIN_EMAIL) {
    return json({ error: "forbidden" }, { status: 403 }, cors);
  }
  return null;
}

interface ProfileRow extends ProfileForPlan {
  user_id: string;
}
interface AgentRow {
  user_id: string;
  online: boolean;
}
interface MissionRow {
  created_at: string;
}

function sevenDaysAgo(): string {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString();
}

/** GET /v1/admin/overview */
export async function adminOverview(
  _req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
): Promise<Response> {
  const denied = requireAdmin(user, cors);
  if (denied) return denied;

  const [profiles, agents, missions] = await Promise.all([
    dbSelect<ProfileRow>(env, "profiles", {
      select: "user_id,plan,trial_ends_at,subscription_status,current_period_end",
      limit: 5000,
    }),
    dbSelect<AgentRow>(env, "agents", { select: "user_id,online", limit: 5000 }),
    dbSelect<MissionRow>(env, "missions", {
      select: "created_at",
      filters: { created_at: `gt.${sevenDaysAgo()}` },
      limit: 5000,
    }),
  ]);

  const planCounts: Record<string, number> = {};
  let trialCount = 0;
  for (const p of profiles) {
    const eff = getEffectivePlan(p);
    planCounts[eff] = (planCounts[eff] ?? 0) + 1;
    if (p.subscription_status === "trialing") trialCount++;
  }

  // Unique users with at least one agent
  const usersWithAgents = new Set(agents.map(a => a.user_id)).size;

  return json(
    {
      users: {
        total: profiles.length,
        free: planCounts["community"] ?? 0,
        operator: planCounts["operator"] ?? 0,
        trial: trialCount,
        new_7d: profiles.filter(p => {
          // profiles doesn't have created_at — use agents or skip
          return false;
        }).length,
      },
      agents: {
        total: agents.length,
        online: agents.filter(a => a.online).length,
        users_with_agents: usersWithAgents,
      },
      missions: {
        last_7d: missions.length,
      },
      as_of: new Date().toISOString(),
    },
    {},
    cors,
  );
}

interface SupabaseAuthUser {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at: string | null;
  user_metadata?: { handle?: string };
}

/** GET /v1/admin/users?page=1&per_page=25 */
export async function adminUsers(
  req: Request,
  env: Env,
  user: { id: string; email: string },
  cors: HeadersInit,
): Promise<Response> {
  const denied = requireAdmin(user, cors);
  if (denied) return denied;

  const url = new URL(req.url);
  const page = Math.max(1, parseInt(url.searchParams.get("page") ?? "1", 10));
  const perPage = Math.min(50, Math.max(1, parseInt(url.searchParams.get("per_page") ?? "25", 10)));

  // Fetch from Supabase auth admin API
  const authUrl = `${env.SUPABASE_URL}/auth/v1/admin/users?per_page=${perPage}&page=${page}`;
  const authResp = await fetch(authUrl, {
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  if (!authResp.ok) {
    return json({ error: "failed_to_list_users" }, { status: 502 }, cors);
  }
  const authBody = (await authResp.json()) as { users?: SupabaseAuthUser[]; total?: number };
  const authUsers = authBody.users ?? [];
  const total = authBody.total ?? authUsers.length;

  // Fetch plans for these users
  const ids = authUsers.map(u => u.id);
  let profileMap: Record<string, string> = {};
  if (ids.length > 0) {
    const profiles = await dbSelect<ProfileRow>(env, "profiles", {
      select: "user_id,plan,trial_ends_at,subscription_status,current_period_end",
      filters: { user_id: `in.(${ids.join(",")})` },
      limit: perPage,
    }).catch(() => [] as ProfileRow[]);
    for (const p of profiles) {
      profileMap[p.user_id] = getEffectivePlan(p);
    }
  }

  const users = authUsers.map(u => ({
    id: u.id,
    email: u.email,
    handle: u.user_metadata?.handle ?? u.email.split("@")[0],
    plan: profileMap[u.id] ?? "community",
    created_at: u.created_at,
    last_sign_in_at: u.last_sign_in_at,
  }));

  return json({ users, total, page, per_page: perPage }, {}, cors);
}
