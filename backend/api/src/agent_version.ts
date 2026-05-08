/**
 * GET /v1/agent/version — unauthenticated, public.
 *
 * Returns the current published Guardian agent version, download URL,
 * and SHA256 checksum. Version + SHA256 come from wrangler vars so they
 * can be updated without code changes.
 */

import type { Env } from "./index";

export function getAgentVersion(env: Env, cors: HeadersInit): Response {
  return new Response(
    JSON.stringify({
      version: env.AGENT_VERSION || "0.3.0",
      download_url: "https://shadowcypher.site/agent/shadowcypher_agent.py",
      sha256: env.AGENT_SHA256 || "",
    }),
    { headers: { "Content-Type": "application/json", ...cors } }
  );
}
