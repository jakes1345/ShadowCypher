/**
 * Phase 4E — team / family accounts.
 *
 * Endpoints:
 *   POST   /v1/teams                          — create team (Operator-only owner)
 *   GET    /v1/teams                          — list teams I own or belong to
 *   POST   /v1/teams/invite       { team_id, email }   — invite by email
 *   GET    /v1/teams/invites                  — list pending invites for me
 *   POST   /v1/teams/accept       { team_id } — accept an invite addressed to my email
 *   DELETE /v1/teams/leave        { team_id } — leave a team I'm a member of
 *
 * Team plan inheritance: members of an Operator-owner team get effective_plan
 * upgraded to 'operator'. We do this by checking the user's owned/joined teams
 * inside getEffectivePlan callers — see `effectivePlanForUser()` below.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate, dbUpsert } from "./supabase";
import { getEffectivePlan, planRequired, type ProfileForPlan } from "./plans";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

interface ProfileRow extends ProfileForPlan { user_id: string; email: string | null; }

async function getProfile(env: Env, userId: string): Promise<ProfileRow | null> {
  const rows = await dbSelect<ProfileRow>(env, "profiles", {
    select: "user_id,email,plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return rows[0] ?? null;
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

export async function createTeam(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { name?: string };
  if (!body.name || body.name.length < 1 || body.name.length > 64) {
    return json({ error: "name_required_1_to_64_chars" }, { status: 400 }, cors);
  }

  // Only Operator owners can create teams
  const profile = await getProfile(env, user.id);
  const plan = getEffectivePlan(profile);
  if (plan !== "operator") {
    return planRequired("operator", plan, "Creating teams requires the Operator plan.", cors);
  }

  const team = await dbInsert<{ id: string; name: string; created_at: string }>(env, "teams", {
    name: body.name.trim(),
    owner_id: user.id,
  });
  // Owner is also a member with role=owner status=active
  await dbInsert(env, "team_members", {
    team_id: team.id,
    user_id: user.id,
    role: "owner",
    status: "active",
    invited_at: new Date().toISOString(),
    joined_at: new Date().toISOString(),
  });

  return json({ team_id: team.id, name: team.name, created_at: team.created_at }, {}, cors);
}

export async function listTeams(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  // Memberships I have
  const memberships = await dbSelect<{ team_id: string; role: string; status: string }>(
    env, "team_members",
    {
      select: "team_id,role,status",
      filters: { user_id: `eq.${user.id}`, status: `eq.active` },
      limit: 100,
    }
  );
  if (!memberships.length) return json({ teams: [] }, {}, cors);

  const teamIds = memberships.map((m) => m.team_id);
  // PostgREST `in` filter syntax
  const filter = `in.(${teamIds.map((id) => `"${id}"`).join(",")})`;
  const teams = await dbSelect<{ id: string; name: string; owner_id: string; created_at: string }>(
    env, "teams",
    {
      select: "id,name,owner_id,created_at",
      filters: { id: filter },
      order: "created_at.desc",
      limit: 100,
    }
  );

  const result = teams.map((t) => {
    const m = memberships.find((mm) => mm.team_id === t.id);
    return {
      id: t.id,
      name: t.name,
      role: m?.role || "member",
      is_owner: t.owner_id === user.id,
      created_at: t.created_at,
    };
  });
  return json({ teams: result }, {}, cors);
}

export async function inviteMember(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { team_id?: string; email?: string };
  if (!body.team_id || !body.email) return json({ error: "team_id_and_email_required" }, { status: 400 }, cors);
  const email = body.email.trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return json({ error: "invalid_email" }, { status: 400 }, cors);
  }

  // Verify caller owns the team
  const teams = await dbSelect<{ id: string; owner_id: string }>(env, "teams", {
    select: "id,owner_id",
    filters: { id: `eq.${body.team_id}`, owner_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!teams.length) return json({ error: "team_not_found_or_not_owner" }, { status: 403 }, cors);

  // Try to resolve to existing user_id by email (best-effort via profiles)
  const existing = await dbSelect<{ user_id: string }>(env, "profiles", {
    select: "user_id",
    filters: { email: `eq.${email}` },
    limit: 1,
  });

  await dbUpsert(
    env,
    "team_members",
    {
      team_id: body.team_id,
      user_id: existing[0]?.user_id ?? null,
      invited_email: email,
      role: "member",
      status: existing[0]?.user_id ? "pending" : "pending",
      invited_at: new Date().toISOString(),
    },
    "team_id,user_id,invited_email"
  );

  return json({ invited: true, email, resolved_user: !!existing[0] }, {}, cors);
}

export async function listInvites(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  // Find pending rows targeting either my user_id or my email
  const byUser = await dbSelect<{ team_id: string; invited_email: string | null; invited_at: string }>(
    env, "team_members",
    {
      select: "team_id,invited_email,invited_at",
      filters: { user_id: `eq.${user.id}`, status: `eq.pending` },
      limit: 50,
    }
  );
  const byEmail = await dbSelect<{ team_id: string; invited_email: string | null; invited_at: string }>(
    env, "team_members",
    {
      select: "team_id,invited_email,invited_at",
      filters: { invited_email: `eq.${user.email.toLowerCase()}`, status: `eq.pending` },
      limit: 50,
    }
  );
  const seen = new Set<string>();
  const all = [...byUser, ...byEmail].filter((m) => {
    if (seen.has(m.team_id)) return false;
    seen.add(m.team_id);
    return true;
  });
  if (!all.length) return json({ invites: [] }, {}, cors);

  const teamIds = all.map((m) => m.team_id);
  const filter = `in.(${teamIds.map((id) => `"${id}"`).join(",")})`;
  const teams = await dbSelect<{ id: string; name: string; owner_id: string }>(
    env, "teams",
    { select: "id,name,owner_id", filters: { id: filter }, limit: 100 }
  );

  const out = all.map((m) => {
    const t = teams.find((tt) => tt.id === m.team_id);
    return { team_id: m.team_id, team_name: t?.name || "(unknown)", invited_at: m.invited_at };
  });
  return json({ invites: out }, {}, cors);
}

export async function acceptInvite(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { team_id?: string };
  if (!body.team_id) return json({ error: "team_id_required" }, { status: 400 }, cors);

  // Find the matching pending row
  const rows = await dbSelect<{ team_id: string; user_id: string | null; invited_email: string | null; status: string }>(
    env, "team_members",
    {
      select: "team_id,user_id,invited_email,status",
      filters: { team_id: `eq.${body.team_id}`, status: `eq.pending` },
      limit: 5,
    }
  );
  const match = rows.find((r) =>
    r.user_id === user.id || r.invited_email === user.email.toLowerCase()
  );
  if (!match) return json({ error: "no_pending_invite" }, { status: 404 }, cors);

  await dbUpdate(
    env,
    "team_members",
    {
      team_id: `eq.${body.team_id}`,
      ...(match.user_id ? { user_id: `eq.${match.user_id}` } : { invited_email: `eq.${user.email.toLowerCase()}` }),
    },
    {
      user_id: user.id,
      status: "active",
      joined_at: new Date().toISOString(),
    }
  );
  return json({ joined: true, team_id: body.team_id }, {}, cors);
}

export async function leaveTeam(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { team_id?: string };
  if (!body.team_id) return json({ error: "team_id_required" }, { status: 400 }, cors);

  // Owners can't leave their own team — they have to delete it
  const team = await dbSelect<{ owner_id: string }>(env, "teams", {
    select: "owner_id",
    filters: { id: `eq.${body.team_id}` },
    limit: 1,
  });
  if (team[0]?.owner_id === user.id) {
    return json({ error: "owner_cannot_leave_own_team" }, { status: 400 }, cors);
  }

  await dbUpdate(
    env,
    "team_members",
    { team_id: `eq.${body.team_id}`, user_id: `eq.${user.id}` },
    { status: "left", joined_at: null }
  );
  return json({ left: true }, {}, cors);
}

// ─── Helper: effective plan with team inheritance ───────────────────────────

/**
 * Returns user's effective plan, considering team membership.
 * If the user belongs to an Operator-owner team, they inherit operator.
 * Used by callers that want to gate features (in addition to plain getEffectivePlan).
 */
export async function effectivePlanForUserWithTeams(
  env: Env,
  userId: string,
  baseProfile: ProfileForPlan | null
): Promise<"community" | "guardian_pro" | "operator"> {
  const base = getEffectivePlan(baseProfile);
  if (base === "operator") return base;

  // Find active team memberships
  const memberships = await dbSelect<{ team_id: string }>(env, "team_members", {
    select: "team_id",
    filters: { user_id: `eq.${userId}`, status: `eq.active` },
    limit: 50,
  });
  if (!memberships.length) return base;

  const teamIds = memberships.map((m) => m.team_id);
  const filter = `in.(${teamIds.map((id) => `"${id}"`).join(",")})`;
  const teams = await dbSelect<{ owner_id: string }>(env, "teams", {
    select: "owner_id",
    filters: { id: filter },
    limit: 50,
  });
  const ownerIds = [...new Set(teams.map((t) => t.owner_id))];
  if (!ownerIds.length) return base;

  // Pull owners' profiles
  const ownerFilter = `in.(${ownerIds.map((id) => `"${id}"`).join(",")})`;
  const owners = await dbSelect<ProfileForPlan>(env, "profiles", {
    select: "plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: ownerFilter },
    limit: 50,
  });
  const ownerPlans = owners.map((o) => getEffectivePlan(o));
  if (ownerPlans.includes("operator")) return "operator";
  if (ownerPlans.includes("guardian_pro") && base === "community") return "guardian_pro";
  return base;
}
