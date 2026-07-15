/**
 * ShadowCypher Releases Worker
 * Serves release artifacts from R2 at releases.shadowcypher.site
 *
 * GET /                        — HTML index listing available versions
 * GET /manifest.json           — machine-readable release manifest
 * GET /latest/<file>           — download latest release file
 * GET /v<version>/<file>       — download specific version file
 * GET /v<version>/             — HTML listing for that version
 */

interface Env {
  SHADOW_FILES: R2Bucket;
}

const MIME: Record<string, string> = {
  iso:   "application/x-iso9660-image",
  apk:   "application/vnd.android.package-archive",
  gz:    "application/gzip",
  deb:   "application/vnd.debian.binary-package",
  rpm:   "application/x-rpm",
  asc:   "text/plain; charset=utf-8",
  txt:   "text/plain; charset=utf-8",
  json:  "application/json",
  html:  "text/html; charset=utf-8",
};

function mimeFor(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (filename.endsWith(".tar.gz")) return "application/gzip";
  return MIME[ext] ?? "application/octet-stream";
}

function html(title: string, body: string): Response {
  return new Response(
    `<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:monospace;background:#0a0e27;color:#e2e8f0;padding:40px 32px;max-width:860px;margin:0 auto}
  h1{color:#00f2ff;margin-bottom:8px;font-size:1.6rem}
  .sub{color:#8899aa;margin-bottom:32px;font-size:.9rem}
  table{width:100%;border-collapse:collapse;margin-top:16px}
  th{text-align:left;color:#8899aa;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;padding:6px 12px;border-bottom:1px solid #1e2a45}
  td{padding:10px 12px;border-bottom:1px solid #111929;font-size:.9rem}
  td:last-child{text-align:right;color:#8899aa;white-space:nowrap}
  a{color:#00f2ff;text-decoration:none}
  a:hover{text-decoration:underline}
  .badge{display:inline-block;background:#00f2ff22;color:#00f2ff;border-radius:3px;padding:2px 7px;font-size:.75rem;margin-left:8px}
</style>
</head><body>${body}</body></html>`,
    { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=60" } },
  );
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

async function serveIndex(env: Env): Promise<Response> {
  const manifest = await env.SHADOW_FILES.get("releases/manifest.json");
  let latestVersion = "—";
  if (manifest) {
    try {
      const m = await manifest.json<{ version: string }>();
      latestVersion = `v${m.version}`;
    } catch { /* ignore */ }
  }

  const listing = await env.SHADOW_FILES.list({ prefix: "releases/", delimiter: "/" });
  const versions = listing.delimitedPrefixes
    .map(p => p.replace("releases/", "").replace("/", ""))
    .filter(v => v !== "latest" && v !== "")
    .sort()
    .reverse();

  const rows = versions.map(v =>
    `<tr><td><a href="/${v}/">${v}</a>${v === latestVersion ? '<span class="badge">latest</span>' : ""}</td><td></td></tr>`
  ).join("") || `<tr><td colspan="2" style="color:#8899aa;padding:24px 12px">No releases published yet.</td></tr>`;

  return html("ShadowCypher Releases", `
    <h1>ShadowCypher Releases</h1>
    <p class="sub">Latest: <strong style="color:#00f2ff">${latestVersion}</strong> &nbsp;·&nbsp; <a href="/latest/">Download latest →</a> &nbsp;·&nbsp; <a href="/manifest.json">manifest.json</a></p>
    <table>
      <thead><tr><th>Version</th><th>Released</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `);
}

async function serveVersionIndex(env: Env, version: string): Promise<Response> {
  const prefix = `releases/${version}/`;
  const listing = await env.SHADOW_FILES.list({ prefix });

  if (listing.objects.length === 0) {
    return new Response("Not found", { status: 404 });
  }

  const rows = listing.objects.map(obj => {
    const name = obj.key.replace(prefix, "");
    const href = `/${version}/${name}`;
    return `<tr><td><a href="${href}">${name}</a></td><td>${fmtBytes(obj.size)}</td></tr>`;
  }).join("");

  return html(`ShadowCypher ${version}`, `
    <h1><a href="/" style="color:#8899aa;font-size:.8rem">← Releases</a><br>${version}</h1>
    <p class="sub" style="margin-top:8px">Files in this release</p>
    <table>
      <thead><tr><th>File</th><th>Size</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `);
}

async function serveFile(env: Env, r2Key: string, filename: string): Promise<Response> {
  const obj = await env.SHADOW_FILES.get(r2Key);
  if (!obj) return new Response("Not found", { status: 404 });

  const contentType = mimeFor(filename);
  const isText = contentType.startsWith("text/") || contentType === "application/json";

  const headers = new Headers({
    "Content-Type": contentType,
    "Content-Disposition": isText
      ? `inline; filename="${filename}"`
      : `attachment; filename="${filename}"`,
    "Cache-Control": "public, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
  });

  if (obj.size) headers.set("Content-Length", String(obj.size));
  if (obj.httpEtag) headers.set("ETag", obj.httpEtag);

  return new Response(obj.body, { headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+/g, "/");
    const segments = path.split("/").filter(Boolean);

    // GET /
    if (segments.length === 0) return serveIndex(env);

    // GET /manifest.json
    if (segments[0] === "manifest.json") {
      return serveFile(env, "releases/manifest.json", "manifest.json");
    }

    const version = segments[0]; // e.g. "latest" or "v1.0.0"
    const filename = segments[1];

    // GET /v1.0.0/ or /latest/  — directory listing
    if (!filename || filename === "") {
      return serveVersionIndex(env, version);
    }

    // GET /v1.0.0/<file> or /latest/<file>
    const r2Key = `releases/${version}/${filename}`;
    return serveFile(env, r2Key, filename);
  },
};
