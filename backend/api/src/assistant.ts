/**
 * Phase 4C + 4F — AI security assistant with cost protection.
 *
 * Three providers (chosen per-user via profiles.ai_provider):
 *   1. "platform"  — uses platform's Anthropic key (default), counted against monthly plan quota
 *   2. "byok"      — uses user's own Anthropic key, stored encrypted; no quota
 *   3. "ollama"    — calls a user-provided Ollama-compatible endpoint; no quota
 *
 * Monthly quotas (queries/month):
 *   community     — 0  (assistant disabled, returns 402)
 *   guardian_pro  — 50
 *   operator      — 500
 *
 * BYOK keys are encrypted at rest using AES-GCM with the Worker's BYOK_ENCRYPTION_SECRET.
 *
 * Endpoints:
 *   POST /v1/assistant/query                  — submit a question
 *   GET  /v1/assistant/usage                  — current month's usage + plan cap
 *   POST /v1/assistant/byok                   — set/clear BYOK Anthropic key
 *   POST /v1/assistant/ollama                 — set/clear Ollama URL
 *
 * Secrets:
 *   ANTHROPIC_API_KEY            — platform key (used when ai_provider='platform')
 *   ANTHROPIC_MODEL              — defaults to claude-haiku-4-5-20251001
 *   BYOK_ENCRYPTION_SECRET       — 32-byte (or longer) random; used to AES-GCM encrypt user keys
 */

import type { Env } from "./index";
import { dbSelect, dbUpdate } from "./supabase";
import { getEffectivePlan, planRequired, type ProfileForPlan } from "./plans";

interface AuthedUser { id: string; email: string; }

const QUOTA_BY_PLAN: Record<string, number> = {
  community: 25,
  guardian_pro: 500,
  operator: 5000,
};

const SYSTEM_PROMPT = `You are Shadow, the ShadowCypher voice assistant — a calm, precise security advisor. Reply in 1-3 sentences optimized for speech. No markdown, no bullet points, no headers. If the user's network data is provided, reference it directly. Never invent device names, IPs, or incidents. If a question is outside your data, say so plainly and suggest one next step.`;

interface ProfileFull extends ProfileForPlan {
  user_id: string;
  ai_query_count: number;
  ai_query_period_start: string;
  ai_provider: "platform" | "byok" | "ollama";
  ai_byok_key_encrypted: string | null;
  ai_byok_key_last4: string | null;
  ai_ollama_url: string | null;
}

interface DeviceRow { mac: string; ip: string | null; hostname: string | null; vendor: string | null; device_type: string | null; open_ports: number[] | null; last_seen_at: string; trusted: boolean; }
interface IncidentRow { severity: string; category: string; title: string; created_at: string; acknowledged: boolean; }
interface ScanRow { scan_type: string; device_count: number | null; started_at: string; }

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers || {}) },
  });

// ─── BYOK encryption (AES-GCM) ─────────────────────────────────────────────

async function deriveKey(secret: string): Promise<CryptoKey> {
  const buf = new TextEncoder().encode(secret);
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return crypto.subtle.importKey("raw", hash, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

async function encrypt(secret: string, plaintext: string): Promise<string> {
  const key = await deriveKey(secret);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(
    await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(plaintext))
  );
  const combined = new Uint8Array(iv.length + ct.length);
  combined.set(iv, 0);
  combined.set(ct, iv.length);
  return btoa(String.fromCharCode(...combined));
}

async function decrypt(secret: string, ciphertext: string): Promise<string> {
  const key = await deriveKey(secret);
  const combined = Uint8Array.from(atob(ciphertext), (c) => c.charCodeAt(0));
  const iv = combined.slice(0, 12);
  const ct = combined.slice(12);
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return new TextDecoder().decode(pt);
}

// ─── Profile + quota helpers ───────────────────────────────────────────────

async function getProfile(env: Env, userId: string): Promise<ProfileFull | null> {
  const rows = await dbSelect<ProfileFull>(env, "profiles", {
    select: "user_id,plan,trial_ends_at,subscription_status,current_period_end,ai_query_count,ai_query_period_start,ai_provider,ai_byok_key_encrypted,ai_byok_key_last4,ai_ollama_url",
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  return rows[0] ?? null;
}

/** Returns the current month's usage + quota, rolling over the period if >30 days passed. */
async function rolloverIfNeeded(env: Env, profile: ProfileFull): Promise<{ count: number; reset: boolean }> {
  const periodStart = new Date(profile.ai_query_period_start).getTime();
  const ageMs = Date.now() - periodStart;
  if (ageMs > 30 * 86400000) {
    await dbUpdate(env, "profiles", { user_id: `eq.${profile.user_id}` }, {
      ai_query_count: 0,
      ai_query_period_start: new Date().toISOString(),
    });
    return { count: 0, reset: true };
  }
  return { count: profile.ai_query_count, reset: false };
}

async function incrementUsage(env: Env, userId: string, by = 1): Promise<void> {
  // Use PostgREST RPC for atomic increment to avoid read-modify-write race
  // Falls back to read-modify-write if RPC not available
  try {
    const resp = await fetch(
      `${env.SUPABASE_URL}/rest/v1/rpc/increment_ai_query_count`,
      {
        method: 'POST',
        headers: {
          apikey: env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ p_user_id: userId, p_by: by }),
      }
    );
    if (resp.ok) return; // RPC handled it atomically
  } catch { /* fall through */ }
  // Fallback: read-modify-write (race window acceptable for metering)
  const rows = await dbSelect<{ ai_query_count: number }>(env, 'profiles', {
    select: 'ai_query_count',
    filters: { user_id: `eq.${userId}` },
    limit: 1,
  });
  const next = (rows[0]?.ai_query_count ?? 0) + by;
  await dbUpdate(env, 'profiles', { user_id: `eq.${userId}` }, { ai_query_count: next });
}

// ─── Endpoints ──────────────────────────────────────────────────────────────

export async function getUsage(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const profile = await getProfile(env, user.id);
  if (!profile) return json({ error: "profile_not_found" }, { status: 404 }, cors);
  const plan = getEffectivePlan(profile);
  const { count } = await rolloverIfNeeded(env, profile);
  const cap = QUOTA_BY_PLAN[plan] ?? 0;
  return json({
    plan,
    provider: profile.ai_provider,
    count,
    cap,
    remaining: Math.max(0, cap - count),
    period_start: profile.ai_query_period_start,
    byok_configured: !!profile.ai_byok_key_encrypted,
    byok_last4: profile.ai_byok_key_last4,
    ollama_url: profile.ai_ollama_url,
  }, {}, cors);
}

export async function setByok(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { api_key?: string | null; clear?: boolean };
  if (body.clear || body.api_key === null || body.api_key === "") {
    await dbUpdate(env, "profiles", { user_id: `eq.${user.id}` }, {
      ai_provider: "platform",
      ai_byok_key_encrypted: null,
      ai_byok_key_last4: null,
    });
    return json({ cleared: true }, {}, cors);
  }
  if (!body.api_key || !body.api_key.startsWith("sk-ant-")) {
    return json({ error: "invalid_anthropic_key_format" }, { status: 400 }, cors);
  }
  if (!env.BYOK_ENCRYPTION_SECRET) {
    return json({ error: "byok_not_supported_on_this_deployment" }, { status: 503 }, cors);
  }
  const encrypted = await encrypt(env.BYOK_ENCRYPTION_SECRET, body.api_key);
  const last4 = body.api_key.slice(-4);
  await dbUpdate(env, "profiles", { user_id: `eq.${user.id}` }, {
    ai_provider: "byok",
    ai_byok_key_encrypted: encrypted,
    ai_byok_key_last4: last4,
  });
  return json({ saved: true, last4 }, {}, cors);
}

export async function setOllama(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as { url?: string | null; clear?: boolean };
  if (body.clear || body.url === null || body.url === "") {
    await dbUpdate(env, "profiles", { user_id: `eq.${user.id}` }, {
      ai_provider: "platform",
      ai_ollama_url: null,
    });
    return json({ cleared: true }, {}, cors);
  }
  if (!body.url || !/^https?:\/\//i.test(body.url)) {
    return json({ error: "url_must_start_with_http_or_https" }, { status: 400 }, cors);
  }
  // Only allow public URLs (block obvious private ranges to prevent SSRF surprises against the Worker)
  // Allow localhost / 127.x for explicit user opt-in (they're calling from their own browser context anyway? no — Worker calls. So this is a real concern.)
  // For safety: only allow https + non-private hostnames. User's local Ollama needs a public tunnel (cloudflared / ngrok).
  try {
    const u = new URL(body.url);
    const blocked = /^(localhost|127\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.|192\.168\.|169\.254\.)/i;
    if (blocked.test(u.hostname)) {
      return json({
        error: "private_host_not_allowed",
        hint: "Expose Ollama via cloudflared/ngrok and use the public URL — the Worker can't reach your LAN.",
      }, { status: 400 }, cors);
    }
  } catch {
    return json({ error: "invalid_url" }, { status: 400 }, cors);
  }
  await dbUpdate(env, "profiles", { user_id: `eq.${user.id}` }, {
    ai_provider: "ollama",
    ai_ollama_url: body.url,
  });
  return json({ saved: true, url: body.url }, {}, cors);
}

interface HistoryMessage { role: "user" | "assistant"; content: string; }

export async function handleQuery(req: Request, env: Env, user: AuthedUser, cors: HeadersInit): Promise<Response> {
  const body = (await req.json().catch(() => ({}))) as {
    question?: string;
    tier?: string;
    history?: HistoryMessage[];   // last N turns from the client
    system?: string;              // client-built system prompt (guardian context injected)
  };
  const question = (body.question || "").trim();
  if (!question) return json({ error: "question_required" }, { status: 400 }, cors);
  if (question.length > 800) return json({ error: "question_too_long" }, { status: 400 }, cors);
  const requestedTier = (body.tier || "fast").toLowerCase(); // "fast" = haiku, "deep" = sonnet

  const profile = await getProfile(env, user.id);
  if (!profile) return json({ error: "profile_not_found" }, { status: 404 }, cors);
  const plan = getEffectivePlan(profile);

  // Plan gate
  if (plan === "community") {
    return planRequired(["guardian_pro", "operator"], plan, "AI assistant requires Guardian Pro or Operator.", cors);
  }

  // Quota check (only for platform-provided AI; BYOK and Ollama are user-funded)
  if (profile.ai_provider === "platform") {
    const { count } = await rolloverIfNeeded(env, profile);
    const cap = QUOTA_BY_PLAN[plan] ?? 0;
    if (count >= cap) {
      return json({
        error: "quota_exceeded",
        plan,
        count,
        cap,
        period_resets_at: new Date(new Date(profile.ai_query_period_start).getTime() + 30 * 86400000).toISOString(),
        hint: "Switch to BYOK (your own Anthropic key) or Ollama (self-hosted) for unmetered access.",
      }, { status: 429 }, cors);
    }
  }

  // Build data-grounded prompt
  const [devices, incidents, scans] = await Promise.all([
    dbSelect<DeviceRow>(env, "devices", { select: "mac,ip,hostname,vendor,device_type,open_ports,last_seen_at,trusted", filters: { user_id: `eq.${user.id}` }, order: "last_seen_at.desc", limit: 30 }),
    dbSelect<IncidentRow>(env, "incidents", { select: "severity,category,title,created_at,acknowledged", filters: { user_id: `eq.${user.id}` }, order: "created_at.desc", limit: 20 }),
    dbSelect<ScanRow>(env, "scans", { select: "scan_type,device_count,started_at", filters: { user_id: `eq.${user.id}` }, order: "started_at.desc", limit: 10 }),
  ]);

  // Build the final user message (always append current question with data context)
  const dataCtx = formatSummary(devices, incidents, scans);
  const userMessage = `My network data:\n\n${dataCtx}\n\nMy question: ${question}`;

  // Build multi-turn messages array (prepend validated history, then current user turn)
  const rawHistory: HistoryMessage[] = Array.isArray(body.history) ? body.history : [];
  const validatedHistory: HistoryMessage[] = rawHistory
    .filter((m) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.length > 0)
    .slice(-8);  // max 8 messages (4 turns)

  // The messages array sent to the LLM: prior turns + current question
  const messages: HistoryMessage[] = [
    ...validatedHistory,
    { role: "user", content: userMessage },
  ];

  // Merge client system prompt (has guardian live context) with backend SYSTEM_PROMPT
  const clientSystem = (typeof body.system === "string" && body.system.length > 0) ? body.system : "";
  const effectiveSystemPrompt = clientSystem
    ? `${SYSTEM_PROMPT}\n\n${clientSystem}`
    : SYSTEM_PROMPT;

  // Dispatch to chosen provider
  try {
    let answer: string;
    let modelLabel: string;

    if (profile.ai_provider === "ollama" && profile.ai_ollama_url) {
      const ollamaModel = env.OLLAMA_DEFAULT_MODEL || 'llama3.1:8b';
      ({ answer, modelLabel } = await queryOllama(profile.ai_ollama_url, messages, effectiveSystemPrompt, ollamaModel));
    } else if (profile.ai_provider === "byok" && profile.ai_byok_key_encrypted) {
      if (!env.BYOK_ENCRYPTION_SECRET) {
        return json({ error: "byok_decryption_unavailable" }, { status: 503 }, cors);
      }
      const userKey = await decrypt(env.BYOK_ENCRYPTION_SECRET, profile.ai_byok_key_encrypted);
      ({ answer, modelLabel } = await queryAnthropic(userKey, env.ANTHROPIC_MODEL || "claude-haiku-4-5-20251001", messages, effectiveSystemPrompt));
    } else {
      // Platform provider
      if (!env.ANTHROPIC_API_KEY) {
        return json({ error: "platform_ai_not_configured", hint: "Configure your own Anthropic key (BYOK) or Ollama URL in the dashboard." }, { status: 503 }, cors);
      }
      // Sonnet tier: operator plan only, costs 2 quota units
      let model = env.ANTHROPIC_MODEL || "claude-haiku-4-5-20251001";
      let quotaCost = 1;
      if (requestedTier === "deep" && plan === "operator") {
        model = "claude-sonnet-4-6-20251001";
        quotaCost = 2;
      }
      ({ answer, modelLabel } = await queryAnthropic(env.ANTHROPIC_API_KEY, model, messages, effectiveSystemPrompt));
      // Only platform provider counts against quota
      await incrementUsage(env, user.id, quotaCost);
    }

    return json({
      answer,
      model: modelLabel,
      provider: profile.ai_provider,
      data_summary: { devices: devices.length, incidents: incidents.length, scans: scans.length },
    }, {}, cors);
  } catch (e) {
    console.error("[assistant] failed", e);
    return json({ error: "ai_error", message: e instanceof Error ? e.message : "unknown" }, { status: 502 }, cors);
  }
}

async function queryAnthropic(
  apiKey: string,
  model: string,
  messages: HistoryMessage[],
  systemPrompt: string,
): Promise<{ answer: string; modelLabel: string }> {
  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "x-api-key": apiKey, "anthropic-version": "2023-06-01", "content-type": "application/json" },
    body: JSON.stringify({
      model,
      max_tokens: 600,
      system: systemPrompt,
      messages,
    }),
  });
  if (!resp.ok) throw new Error(`anthropic_${resp.status}:${await resp.text()}`);
  const data = (await resp.json()) as { content?: Array<{ type: string; text?: string }>; model?: string };
  const text = (data.content || []).filter((c) => c.type === "text").map((c) => c.text || "").join("\n").trim();
  return { answer: text || "(no answer)", modelLabel: data.model || model };
}

async function queryOllama(
  baseUrl: string,
  messages: HistoryMessage[],
  systemPrompt: string,
  model = 'llama3.1:8b',
): Promise<{ answer: string; modelLabel: string }> {
  const url = baseUrl.replace(/\/$/, "") + "/api/chat";
  const resp = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model,
      stream: false,
      messages: [
        { role: "system", content: systemPrompt },
        ...messages,
      ],
      options: { num_predict: 600 },
    }),
  });
  if (!resp.ok) throw new Error(`ollama_${resp.status}:${await resp.text()}`);
  const data = (await resp.json()) as { message?: { content?: string }; model?: string };
  return { answer: data.message?.content?.trim() || "(no answer)", modelLabel: data.model || "ollama" };
}

function formatSummary(devices: DeviceRow[], incidents: IncidentRow[], scans: ScanRow[]): string {
  const lines: string[] = [];
  lines.push(`DEVICES (${devices.length}):`);
  if (!devices.length) lines.push("  (none — agent not installed)");
  for (const d of devices.slice(0, 20)) {
    const ports = (d.open_ports || []).slice(0, 8).join(",");
    const trust = d.trusted ? " [trusted]" : "";
    lines.push(`  - ${d.hostname || d.ip || d.mac} | type=${d.device_type || "unknown"} | ports=[${ports}] | seen=${d.last_seen_at}${trust}`);
  }
  lines.push("");
  lines.push(`INCIDENTS (${incidents.length}):`);
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
