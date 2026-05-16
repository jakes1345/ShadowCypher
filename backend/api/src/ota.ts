/**
 * OTA update manifest for Shadow Android app.
 * GET  /v1/shadow/ota        — fetch current version manifest (no auth)
 * POST /v1/shadow/ota        — update manifest (admin key required)
 *
 * Manifest stored in KV binding SHADOW_OTA (key: "manifest").
 */

export interface OtaManifest {
  version: string;       // semver, e.g. "1.2"
  apk_url: string;       // GitHub Releases CDN URL
  apk_sha256: string;    // hex SHA-256 of the signed APK
  chunks_url: string;    // URL to chunks.json for KB search
  classifier_url: string; // URL to classifier.json for intent model
  released_at: string;   // ISO 8601
}

export interface OtaEnv {
  SHADOW_OTA: KVNamespace;
  SHADOW_ADMIN_KEY: string;
}

export async function getOtaManifest(env: OtaEnv): Promise<Response> {
  const raw = await env.SHADOW_OTA.get("manifest");
  if (!raw) {
    return new Response(
      JSON.stringify({ error: "no manifest published yet" }),
      { status: 404, headers: { "Content-Type": "application/json" } },
    );
  }
  return new Response(raw, {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=300",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export async function updateOtaManifest(
  req: Request,
  env: OtaEnv,
): Promise<Response> {
  // Admin-only: validate bearer key
  const auth = req.headers.get("Authorization") ?? "";
  const key = auth.replace(/^Bearer\s+/i, "").trim();
  if (!key || key !== env.SHADOW_ADMIN_KEY) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  let body: Partial<OtaManifest>;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid json" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { version, apk_url, apk_sha256, chunks_url, classifier_url } = body;
  if (!version || !apk_url || !apk_sha256 || !chunks_url || !classifier_url) {
    return new Response(
      JSON.stringify({
        error: "missing fields",
        required: ["version", "apk_url", "apk_sha256", "chunks_url", "classifier_url"],
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );
  }

  // Basic URL validation — must be GitHub or shadowcypher.site
  const allowedHosts = ["github.com", "raw.githubusercontent.com", "shadowcypher.site"];
  for (const url of [apk_url, chunks_url, classifier_url]) {
    try {
      const host = new URL(url).hostname;
      if (!allowedHosts.some((h) => host === h || host.endsWith(`.${h}`))) {
        return new Response(
          JSON.stringify({ error: `url host not allowed: ${host}` }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        );
      }
    } catch {
      return new Response(JSON.stringify({ error: `invalid url: ${url}` }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  // Validate SHA-256 format (64 hex chars)
  if (!/^[0-9a-f]{64}$/i.test(apk_sha256)) {
    return new Response(JSON.stringify({ error: "apk_sha256 must be 64 hex chars" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
  }

  const manifest: OtaManifest = {
    version,
    apk_url,
    apk_sha256,
    chunks_url,
    classifier_url,
    released_at: new Date().toISOString(),
  };

  await env.SHADOW_OTA.put("manifest", JSON.stringify(manifest));

  return new Response(JSON.stringify({ ok: true, manifest }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
