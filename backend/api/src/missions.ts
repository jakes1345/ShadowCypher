/**
 * ShadowScript remote mission execution.
 *
 * Phone sends a ShadowScript to the API; the desktop Guardian agent polls,
 * executes it locally, and posts results back. Phone polls for completion.
 *
 * Flow: POST /v1/agents/{agent_id}/missions  →  agent polls  →  agent posts result
 *       GET  /v1/missions/{mission_id}        →  phone checks status
 *
 * Plan gate: operator only (missions execute arbitrary code on the desktop).
 * Rate limit: 10 missions/min per user (enforced in index.ts).
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate } from "./supabase";
import { getEffectivePlan, planRequired, type ProfileForPlan } from "./plans";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

function randomId(prefix: string): string {
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  return `${prefix}_${Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')}`;
}

async function getProfile(env: Env, userId: string): Promise<ProfileForPlan | null> {
  const rows = await dbSelect<ProfileForPlan>(env, "profiles", {
    select: "plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return rows[0] ?? null;
}

interface AgentRow { id: string; user_id: string; }
interface MissionRow {
  id: string;
  agent_id: string;
  user_id: string;
  status: string;
  script_content: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result_output: string | null;
  exit_code: number | null;
}

/** POST /v1/agents/:agent_id/missions — phone submits a ShadowScript mission */
export async function createMission(
  req: Request,
  env: Env,
  user: AuthedUser,
  cors: HeadersInit,
  agentId: string,
): Promise<Response> {
  const profile = await getProfile(env, user.id);
  if (!profile) return json({ error: "profile_not_found" }, { status: 404 }, cors);
  const plan = getEffectivePlan(profile);
  if (plan !== "operator") {
    return planRequired(["operator"], plan, "Remote mission execution requires Operator plan.", cors);
  }

  // Verify user owns this agent
  const agents = await dbSelect<AgentRow>(env, "agents", {
    select: "id,user_id",
    filters: { id: `eq.${agentId}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!agents.length) return json({ error: "agent_not_found" }, { status: 404 }, cors);

  const body = (await req.json().catch(() => ({}))) as { script?: string; label?: string };
  const script = (body.script || "").trim();
  if (!script) return json({ error: "script_required" }, { status: 400 }, cors);
  if (script.length > 8000) return json({ error: "script_too_long" }, { status: 400 }, cors);

  const missionId = randomId("msn");
  await dbInsert(env, "missions", {
    id: missionId,
    agent_id: agentId,
    user_id: user.id,
    status: "pending",
    script_content: script,
    label: body.label || null,
    created_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
    result_output: null,
    exit_code: null,
  });

  return json({ mission_id: missionId, status: "pending" }, { status: 201 }, cors);
}

/** GET /v1/agents/:agent_id/missions/pending — desktop agent polls for work */
export async function getPendingMissions(
  req: Request,
  env: Env,
  user: AuthedUser,
  cors: HeadersInit,
  agentId: string,
): Promise<Response> {
  // Verify agent belongs to user
  const agents = await dbSelect<AgentRow>(env, "agents", {
    select: "id",
    filters: { id: `eq.${agentId}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!agents.length) return json({ error: "agent_not_found" }, { status: 404 }, cors);

  const missions = await dbSelect<Pick<MissionRow, "id" | "script_content" | "created_at">>(env, "missions", {
    select: "id,script_content,created_at",
    filters: { agent_id: `eq.${agentId}`, status: `eq.pending` },
    order: "created_at.asc",
    limit: 5,
  });

  // Mark them running — include status filter as optimistic lock so a concurrent
  // poll that already grabbed a mission (and set it to 'running') won't match.
  for (const m of missions) {
    await dbUpdate(env, "missions", { id: `eq.${m.id}`, status: `eq.pending` }, {
      status: "running",
      started_at: new Date().toISOString(),
    });
  }
  // Re-fetch only the missions we actually grabbed (status=running, started in last 5s)
  const started = await dbSelect<Pick<MissionRow, "id" | "script_content" | "created_at">>(env, "missions", {
    select: "id,script_content,created_at",
    filters: { agent_id: `eq.${agentId}`, status: `eq.running`, started_at: `gt.${new Date(Date.now() - 5000).toISOString()}` },
  });
  return json({ missions: started }, {}, cors);
}

/** POST /v1/missions/:mission_id/result — desktop agent posts execution output */
export async function reportMissionResult(
  req: Request,
  env: Env,
  user: AuthedUser,
  cors: HeadersInit,
  missionId: string,
): Promise<Response> {
  // Verify mission belongs to user
  const existing = await dbSelect<Pick<MissionRow, "id" | "user_id">>(env, "missions", {
    select: "id,user_id",
    filters: { id: `eq.${missionId}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!existing.length) return json({ error: "mission_not_found" }, { status: 404 }, cors);

  const body = (await req.json().catch(() => ({}))) as { output?: string; exit_code?: number; error?: string };
  const status = body.error ? "failed" : "completed";

  await dbUpdate(env, "missions", { id: `eq.${missionId}` }, {
    status,
    completed_at: new Date().toISOString(),
    result_output: body.output || body.error || "",
    exit_code: body.exit_code ?? (body.error ? 1 : 0),
  });

  return json({ ok: true, status }, {}, cors);
}

/** GET /v1/missions/:mission_id — phone polls for result */
export async function getMission(
  req: Request,
  env: Env,
  user: AuthedUser,
  cors: HeadersInit,
  missionId: string,
): Promise<Response> {
  const missions = await dbSelect<MissionRow>(env, "missions", {
    select: "id,agent_id,status,created_at,started_at,completed_at,result_output,exit_code",
    filters: { id: `eq.${missionId}`, user_id: `eq.${user.id}` },
    limit: 1,
  });
  if (!missions.length) return json({ error: "mission_not_found" }, { status: 404 }, cors);
  return json(missions[0], {}, cors);
}

/** GET /v1/missions — list user's recent missions */
export async function listMissions(
  req: Request,
  env: Env,
  user: AuthedUser,
  cors: HeadersInit,
): Promise<Response> {
  const url = new URL(req.url);
  const agentId = url.searchParams.get("agent_id");
  const filters: Record<string, string> = { user_id: `eq.${user.id}` };
  if (agentId) filters.agent_id = `eq.${agentId}`;

  const missions = await dbSelect<MissionRow>(env, "missions", {
    select: "id,agent_id,status,created_at,started_at,completed_at,exit_code",
    filters,
    order: "created_at.desc",
    limit: 50,
  });
  return json({ missions }, {}, cors);
}
