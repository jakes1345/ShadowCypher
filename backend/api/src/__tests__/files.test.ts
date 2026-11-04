import { describe, it, expect } from "vitest";
import { downloadFile } from "../files";
import type { Env } from "../index";

function envWith(objects: Record<string, string>): Env {
  return {
    SHADOW_FILES: {
      get: async (k: string) =>
        k in objects ? { body: objects[k], size: objects[k].length, httpMetadata: { contentType: "text/plain" } } : null,
    },
  } as unknown as Env;
}

const req = new Request("https://x/v1/files/k");
const alice = { id: "alice-id", email: "a@x" };

describe("downloadFile ownership", () => {
  const env = envWith({ "alice-id/a.txt": "hi", "bob-id/b.txt": "secret" });

  it("serves the owner's file", async () => {
    const res = await downloadFile(req, env, alice, {}, "alice-id/a.txt");
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("hi");
  });

  it("refuses another user's file", async () => {
    const res = await downloadFile(req, env, alice, {}, "bob-id/b.txt");
    expect(res.status).toBe(403);
  });

  it("refuses path traversal out of the owner's prefix", async () => {
    const res = await downloadFile(req, env, alice, {}, "alice-id/../bob-id/b.txt");
    expect(res.status).toBe(403);
  });
});
