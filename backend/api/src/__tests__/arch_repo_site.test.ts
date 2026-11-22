// @vitest-environment node
/**
 * pacman is told to fetch the [shadowos] repository from
 * https://shadowcypher.site/arch/shadowos/x86_64, but no file under www/ lives
 * there. One line in www/_redirects sends those requests to the GitHub release
 * that the publish-arch workflow uploads to. Removing that line, or moving it
 * below the catch-all, takes the repository offline without changing any page,
 * so these tests fail first.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../../..");
const text = (path: string) => readFileSync(join(ROOT, path), "utf8");
/** Byte for byte, as a string: latin1 maps every byte to one character. */
const bytes = (path: string) => readFileSync(join(ROOT, path), "latin1");

/** Lines of www/_redirects as [from, to, status], without comments. */
const rules = text("www/_redirects")
  .split("\n")
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith("#"))
  .map((l) => l.split(/\s+/));

describe("the [shadowos] pacman repository on shadowcypher.site", () => {
  it("serves the address the mirrorlist and install.sh give pacman", () => {
    const server = /^Server\s*=\s*(\S+)$/m.exec(text("packaging/arch/shadowos-mirrorlist/shadowos-mirrorlist"))?.[1];
    expect(server).toBe("https://shadowcypher.site/arch/$repo/$arch");
    expect(text("www/arch/install.sh")).toContain('REPO_URL="https://shadowcypher.site/arch"');
    // $repo is shadowos and $arch is x86_64: the path the redirect has to cover.
    expect(rules.map((r) => r[0])).toContain("/arch/shadowos/x86_64/*");
  });

  it("redirects to the release the workflow publishes to", () => {
    const tag = /^\s*RELEASE_TAG:\s*(\S+)$/m.exec(text(".github/workflows/publish-arch.yml"))?.[1];
    expect(tag).toBeTruthy();
    const rule = rules.find((r) => r[0] === "/arch/shadowos/x86_64/*");
    expect(rule?.[1]).toMatch(new RegExp(`^https://github\\.com/[^/]+/[^/]+/releases/download/${tag}/:splat$`));
    expect(rule?.[2]).toBe("302");
  });

  it("puts the redirect before the catch-all", () => {
    const from = rules.map((r) => r[0]);
    expect(from.indexOf("/arch/shadowos/x86_64/*")).toBeLessThan(from.indexOf("/*"));
  });

  it("hands out the key that shadowos-keyring ships", () => {
    expect(bytes("www/arch/shadowos.gpg") === bytes("packaging/arch/shadowos-keyring/shadowos.gpg")).toBe(true);
  });
});
