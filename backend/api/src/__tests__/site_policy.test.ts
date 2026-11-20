// @vitest-environment node
/**
 * The live site sends a second security policy that lists where scripts may load
 * from (www/_headers, the https://shadowcypher.site/* block). It exists to refuse
 * the bot-check script Cloudflare adds, which sets a cookie. Because it is a list,
 * a page that loads a script from somewhere new would break on the live site only.
 * These tests fail first.
 */
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const WWW = resolve(dirname(fileURLToPath(import.meta.url)), "../../../../www");
const LIVE = "https://shadowcypher.site";

/** The script-src sources of the live-domain policy. */
function liveScriptSources(): string[] {
  const lines = readFileSync(join(WWW, "_headers"), "utf8").split("\n");
  const start = lines.findIndex((l) => l.trim() === `${LIVE}/*`);
  if (start < 0) throw new Error("no live-domain block in www/_headers");
  for (let i = start + 1; i < lines.length && /^\s/.test(lines[i]); i++) {
    const m = /^\s+Content-Security-Policy:\s*(.+)$/.exec(lines[i]);
    if (!m) continue;
    const directive = m[1].split(";").map((d) => d.trim()).find((d) => d.startsWith("script-src "));
    if (directive) return directive.split(/\s+/).slice(1);
  }
  throw new Error("the live-domain block has no script-src");
}

/** How a browser matches a same-site path: a source ending in "/" is a prefix, anything else must match exactly. */
function allowed(path: string, sources: string[]): boolean {
  return sources
    .filter((s) => s.startsWith(`${LIVE}/`))
    .map((s) => s.slice(LIVE.length))
    .some((s) => (s.endsWith("/") ? path.startsWith(s) : path === s));
}

function htmlFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) return htmlFiles(full);
    return name.endsWith(".html") ? [full] : [];
  });
}

/** Every script a page loads from this site, and every service worker it registers. */
function scriptsLoadedBySite(): { page: string; path: string }[] {
  const found: { page: string; path: string }[] = [];
  for (const file of htmlFiles(WWW)) {
    const html = readFileSync(file, "utf8");
    const page = file.slice(WWW.length);
    for (const m of html.matchAll(/<script\b[^>]*\ssrc\s*=\s*["']([^"']+)["']/gi)) found.push({ page, path: m[1] });
    for (const m of html.matchAll(/serviceWorker\s*\.\s*register\(\s*["']([^"']+)["']/g)) found.push({ page, path: m[1] });
  }
  return found;
}

describe("the live site's script policy", () => {
  const sources = liveScriptSources();
  const scripts = scriptsLoadedBySite();

  it("finds the scripts the site loads", () => {
    expect(scripts.length).toBeGreaterThan(5);
    expect(scripts.map((s) => s.path)).toContain("/sw.js");
  });

  it("loads every script from this site, by a path from the root", () => {
    for (const s of scripts) expect(s.path, `${s.page} loads ${s.path}`).toMatch(/^\/[^/]/);
  });

  it("allows every script the site loads", () => {
    const refused = scripts.filter((s) => !allowed(s.path.split(/[?#]/)[0], sources));
    expect(refused, "add the folder to the https://shadowcypher.site/* block in www/_headers").toEqual([]);
  });

  it("refuses Cloudflare's bot-check script and keeps its email helper", () => {
    expect(allowed("/cdn-cgi/challenge-platform/scripts/jsd/main.js", sources)).toBe(false);
    expect(allowed("/cdn-cgi/challenge-platform/h/b/scripts/jsd/f8df4d4a0cd6/main.js", sources)).toBe(false);
    expect(allowed("/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js", sources)).toBe(true);
  });

  it("does not open the door wider than the first policy", () => {
    // 'self' or a bare host would let the bot check back in.
    expect(sources).not.toContain("'self'");
    expect(sources).not.toContain(LIVE);
    expect(sources).not.toContain(`${LIVE}/`);
    expect(sources.filter((s) => s.startsWith("http") && !s.startsWith(`${LIVE}/`))).toEqual([]);
    // The web app has inline scripts and loads WebAssembly, so both of these must stay.
    expect(sources).toContain("'unsafe-inline'");
    expect(sources).toContain("'wasm-unsafe-eval'");
  });
});
