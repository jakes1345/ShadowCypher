/**
 * Guardian endpoints — agent check-ins, scans, devices, incidents.
 *
 * All endpoints require Bearer key auth (resolved to user_id via api_key in user_metadata).
 * Writes use the service_role key (RLS-bypassing) so the Worker can write on behalf of agents.
 * Reads honor user ownership via explicit user_id filters.
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpdate, dbUpsert } from "./supabase";
import {
  getEffectivePlan,
  getLimits,
  planRequired,
  type ProfileForPlan,
} from "./plans";
import { dispatchIncidentNotification } from "./notifications";

interface AuthedUser {
  id: string;
  email: string;
}

async function getProfile(env: Env, userId: string): Promise<ProfileForPlan | null> {
  const rows = await dbSelect<ProfileForPlan>(env, "profiles", {
    select: "plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return rows[0] ?? null;
}

interface RegisterBody {
  hostname: string;
  os?: string;
  agent_version?: string;
}

interface ScanBody {
  agent_id?: string;
  scan_type: "network" | "port" | "router" | "arp" | "audit";
  target?: string;
  duration_ms?: number;
  devices?: Array<{
    mac: string;
    ip?: string;
    hostname?: string;
    vendor?: string;
    device_type?: string;
    open_ports?: number[];
  }>;
  result?: Record<string, unknown>;
}

interface IncidentBody {
  agent_id?: string;
  device_id?: string;
  severity: "info" | "warning" | "critical";
  category: string;
  title: string;
  detail?: string;
  data?: Record<string, unknown>;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

// ─── Agents ─────────────────────────────────────────────────────────────────

export async function registerAgent(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const body = (await req.json().catch(() => ({}))) as RegisterBody;
  if (!body.hostname) return json({ error: "hostname_required" }, { status: 400 }, cors);

  // Plan gate: enforce maxAgents (existing same hostname is upsert, not new — exempt)
  const profile = await getProfile(env, user.id);
  const plan = getEffectivePlan(profile);
  const limits = getLimits(plan);

  const existingByHost = await dbSelect<{ id: string }>(env, "agents", {
    select: "id",
    filters: { user_id: `eq.${user.id}`, hostname: `eq.${body.hostname}` },
    limit: 1,
  });
  if (existingByHost.length === 0) {
    const allAgents = await dbSelect<{ id: string }>(env, "agents", {
      select: "id",
      filters: { user_id: `eq.${user.id}` },
      limit: limits.maxAgents + 1,
    });
    if (allAgents.length >= limits.maxAgents) {
      return planRequired(
        ["guardian_pro", "operator"],
        plan,
        `Plan ${plan} is limited to ${limits.maxAgents} agent(s). Upgrade to register more.`,
        cors
      );
    }
  }

  const agent = await dbUpsert<{ id: string }>(
    env,
    "agents",
    {
      user_id: user.id,
      hostname: body.hostname,
      os: body.os ?? null,
      agent_version: body.agent_version ?? null,
      last_seen_at: new Date().toISOString(),
    },
    "user_id,hostname"
  );
  return json({ agent_id: agent.id }, {}, cors);
}

export async function heartbeatAgent(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const url = new URL(req.url);
  const agentId = url.searchParams.get("agent_id");
  if (!agentId) return json({ error: "agent_id_required" }, { status: 400 }, cors);

  await dbUpdate(env, "agents", { id: `eq.${agentId}`, user_id: `eq.${user.id}` }, {
    last_seen_at: new Date().toISOString(),
  });
  return json({ ok: true }, {}, cors);
}

// ─── Scans + devices ────────────────────────────────────────────────────────

export async function uploadScan(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const body = (await req.json().catch(() => ({}))) as ScanBody;
  if (!body.scan_type) return json({ error: "scan_type_required" }, { status: 400 }, cors);

  const scan = await dbInsert<{ id: string; started_at: string }>(env, "scans", {
    user_id: user.id,
    agent_id: body.agent_id ?? null,
    scan_type: body.scan_type,
    target: body.target ?? null,
    duration_ms: body.duration_ms ?? null,
    device_count: body.devices?.length ?? null,
    result: body.result ?? {},
  });

  // Upsert each discovered device + flag new-device incidents
  const newDeviceIncidents: Array<{ mac: string; ip?: string; hostname?: string }> = [];
  if (body.devices?.length) {
    for (const d of body.devices) {
      if (!d.mac) continue;
      const existing = await dbSelect<{ id: string }>(env, "devices", {
        select: "id",
        filters: { user_id: `eq.${user.id}`, mac: `eq.${d.mac}` },
        limit: 1,
      });
      const isNew = existing.length === 0;
      await dbUpsert(
        env,
        "devices",
        {
          user_id: user.id,
          agent_id: body.agent_id ?? null,
          mac: d.mac,
          ip: d.ip ?? null,
          hostname: d.hostname ?? null,
          vendor: d.vendor ?? null,
          device_type: d.device_type ?? null,
          open_ports: d.open_ports ?? [],
          last_seen_at: new Date().toISOString(),
        },
        "user_id,mac"
      );
      if (isNew) newDeviceIncidents.push({ mac: d.mac, ip: d.ip, hostname: d.hostname });
    }
  }

  // Auto-create incidents for new devices
  for (const nd of newDeviceIncidents) {
    await dbInsert(env, "incidents", {
      user_id: user.id,
      agent_id: body.agent_id ?? null,
      severity: "info",
      category: "new_device",
      title: `New device on network: ${nd.hostname ?? nd.ip ?? nd.mac}`,
      detail: `MAC ${nd.mac}${nd.ip ? ` · IP ${nd.ip}` : ""}`,
      data: nd,
    });
  }

  return json(
    { scan_id: scan.id, started_at: scan.started_at, new_device_incidents: newDeviceIncidents.length },
    {},
    cors
  );
}

export async function listDevices(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const devices = await dbSelect(env, "devices", {
    select: "id,mac,ip,hostname,vendor,device_type,open_ports,trusted,last_seen_at,first_seen_at",
    filters: { user_id: `eq.${user.id}` },
    order: "last_seen_at.desc",
    limit: 200,
  });
  return json({ devices }, {}, cors);
}

export async function recentScans(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  // Plan gate: free tier sees only last 7 days; Pro = 90 days; Operator = unlimited
  const profile = await getProfile(env, user.id);
  const plan = getEffectivePlan(profile);
  const limits = getLimits(plan);
  const cutoff = new Date(Date.now() - limits.scanHistoryDays * 86400000).toISOString();

  const scans = await dbSelect(env, "scans", {
    select: "id,scan_type,target,duration_ms,device_count,started_at",
    filters: { user_id: `eq.${user.id}`, started_at: `gte.${cutoff}` },
    order: "started_at.desc",
    limit: 25,
  });
  return json({ scans, plan, history_days: limits.scanHistoryDays }, {}, cors);
}

// ─── Incidents ──────────────────────────────────────────────────────────────

export async function createIncident(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const body = (await req.json().catch(() => ({}))) as IncidentBody;
  if (!body.severity || !body.category || !body.title) {
    return json({ error: "severity_category_title_required" }, { status: 400 }, cors);
  }
  const inc = await dbInsert<{ id: string; created_at: string }>(env, "incidents", {
    user_id: user.id,
    agent_id: body.agent_id ?? null,
    device_id: body.device_id ?? null,
    severity: body.severity,
    category: body.category,
    title: body.title,
    detail: body.detail ?? null,
    data: body.data ?? {},
  });

  // Fire-and-forget notification dispatch (non-blocking; log failures only)
  try {
    await dispatchIncidentNotification(env, {
      id: inc.id,
      severity: body.severity,
      category: body.category,
      title: body.title,
      detail: body.detail ?? null,
      user_id: user.id,
    }, user.email);
  } catch (e) {
    console.warn("[notify] dispatch failed", e instanceof Error ? e.message : e);
  }

  return json({ incident_id: inc.id, created_at: inc.created_at }, {}, cors);
}

export async function listIncidents(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const url = new URL(req.url);
  const onlyOpen = url.searchParams.get("open") === "1";
  const filters: Record<string, string> = { user_id: `eq.${user.id}` };
  if (onlyOpen) filters.acknowledged = "eq.false";

  const incidents = await dbSelect(env, "incidents", {
    select: "id,severity,category,title,detail,data,acknowledged,acknowledged_at,created_at,device_id",
    filters,
    order: "created_at.desc",
    limit: 100,
  });
  return json({ incidents }, {}, cors);
}

export async function ackIncident(req: Request, env: Env, user: AuthedUser, cors: HeadersInit) {
  const url = new URL(req.url);
  const incidentId = url.searchParams.get("incident_id");
  if (!incidentId) return json({ error: "incident_id_required" }, { status: 400 }, cors);

  const updated = await dbUpdate(
    env,
    "incidents",
    { id: `eq.${incidentId}`, user_id: `eq.${user.id}` },
    { acknowledged: true, acknowledged_at: new Date().toISOString() }
  );
  if (!updated.length) return json({ error: "not_found" }, { status: 404 }, cors);
  return json({ ok: true }, {}, cors);
}
