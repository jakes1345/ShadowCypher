/**
 * Phase 4C — AI security assistant.
 *
 * Endpoint: POST /v1/assistant/query  { question: string }
 *   Authenticated. Pro/Operator/Trial only (community gets 402).
 *   Pulls the user's recent devices/scans/incidents, formats a prompt,
 *   calls Anthropic Claude, returns a plain-English answer.
 *
 * Why server-side: keeps the Anthropic key out of the browser, lets us
 * inject the user's data without exposing the data model to the client.
 *
 * Secrets:
 *   ANTHROPIC_API_KEY    — sk-ant-… from console.anthropic.com
 *   ANTHROPIC_MODEL      — defaults to claude-haiku-4-5-20251001
 */

import type { Env } from "./index";
import { dbSelect } from "./supabase";
import { getEffectivePlan, planRequired, type ProfileForPlan } from "./plans";

interface AuthedUser { id: string; email: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

const SYSTEM_PROMPT = `You are the ShadowCypher security assistant — a calm, terse, technically precise advisor that helps the user understand their network, devices, and security posture. You answer based ONLY on the user's data summary provided in the user message. If the data doesn't answer the question, say so. Never invent device names, IPs, or events. Keep responses under 200 words unless the user asks for more depth. Use plain language; avoid hype words like "tactical", "ghost", "sovereign". Format short answers as 2-4 short paragraphs or a brief bulleted list. End with one concrete next step the user can take.`;

interface DeviceRow { mac: string; ip: string | null; hostname: string | null; vendor: string | null; device_type: string | null; open_ports: number[] | null; last_seen_at: string; trusted: boolean; }
interface IncidentRow { severity: string; category: string; title: string; created_at: string; acknowledged: boolean; }
interface ScanRow { scan_type: string; device_count: number | null; started_at: string; }

export async function handleQuery(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { question?: string };
  const question = (body.question || "").trim();
  if (!question) return json({ error: "question_required" }, { status: 400 }, cors);
  if (question.length > 800) return json({ error: "question_too_long" }, { status: 400 }, cors);

  // Plan gate
  const profileRows = await dbSelect<ProfileForPlan>(env, "profiles", {
    select: "plan,trial_ends_at,subscription_status,current_period_end",
    filters: { user_id: `eq.${user.id}` },
    limit: 1,
  });
  const plan = getEffectivePlan(profileRows[0]);
  if (plan === "community") {
    return planRequired(["guardian_pro", "operator"], plan, "AI assistant requires Guardian Pro or Operator.", cors);
  }

  if (!env.ANTHROPIC_API_KEY) {
    return json({
      error: "assistant_not_configured",
      message: "AI assistant is not yet configured on this deployment. The site owner needs to set ANTHROPIC_API_KEY as a Worker secret.",
    }, { status: 503 }, cors);
  }

  // Pull the user's data summary
  const [devices, incidents, scans] = await Promise.all([
    dbSelect<DeviceRow>(env, "devices", {
      select: "mac,ip,hostname,vendor,device_type,open_ports,last_seen_at,trusted",
      filters: { user_id: `eq.${user.id}` },
      order: "last_seen_at.desc",
      limit: 30,
    }),
    dbSelect<IncidentRow>(env, "incidents", {
      select: "severity,category,title,created_at,acknowledged",
      filters: { user_id: `eq.${user.id}` },
      order: "created_at.desc",
      limit: 20,
    }),
    dbSelect<ScanRow>(env, "scans", {
      select: "scan_type,device_count,started_at",
      filters: { user_id: `eq.${user.id}` },
      order: "started_at.desc",
      limit: 10,
    }),
  ]);

  const summary = formatSummary(devices, incidents, scans);
  const userMessage = `My data:\n\n${summary}\n\nMy question: ${question}`;

  const model = env.ANTHROPIC_MODEL || "claude-haiku-4-5-20251001";
  try {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model,
        max_tokens: 600,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userMessage }],
      }),
    });
    if (!resp.ok) {
      const err = await resp.text();
      console.error("[assistant] anthropic error", resp.status, err);
      return json({ error: "ai_error", status: resp.status }, { status: 502 }, cors);
    }
    const data = (await resp.json()) as { content?: Array<{ type: string; text?: string }>; model?: string; usage?: unknown };
    const text = (data.content || []).filter((c) => c.type === "text").map((c) => c.text || "").join("\n").trim();
    return json({
      answer: text || "(no answer returned)",
      model: data.model || model,
      data_summary: { devices: devices.length, incidents: incidents.length, scans: scans.length },
    }, {}, cors);
  } catch (e) {
    console.error("[assistant] fetch failed", e);
    return json({ error: "ai_unreachable" }, { status: 502 }, cors);
  }
}

function formatSummary(devices: DeviceRow[], incidents: IncidentRow[], scans: ScanRow[]): string {
  const lines: string[] = [];
  lines.push(`DEVICES (${devices.length} total, last seen first):`);
  if (!devices.length) lines.push("  (no devices yet — agent not installed or no scans run)");
  for (const d of devices.slice(0, 20)) {
    const ports = (d.open_ports || []).slice(0, 8).join(",");
    const trust = d.trusted ? " [trusted]" : "";
    lines.push(`  - ${d.hostname || d.ip || d.mac} | type=${d.device_type || "unknown"} | ports=[${ports}] | last_seen=${d.last_seen_at}${trust}`);
  }
  lines.push("");
  lines.push(`INCIDENTS (${incidents.length} total, last 20):`);
  if (!incidents.length) lines.push("  (none)");
  for (const i of incidents) {
    const ack = i.acknowledged ? " [acked]" : "";
    lines.push(`  - [${i.severity.toUpperCase()}] ${i.category}: ${i.title} @ ${i.created_at}${ack}`);
  }
  lines.push("");
  lines.push(`RECENT SCANS (${scans.length}):`);
  for (const s of scans) lines.push(`  - ${s.scan_type} · ${s.device_count ?? 0} devices · ${s.started_at}`);
  return lines.join("\n");
}
