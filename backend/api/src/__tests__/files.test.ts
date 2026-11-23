import { describe, it, expect } from "vitest";
import { downloadFile, uploadFile, listFiles, SEALED_TYPE } from "../files";
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

function bucket() {
  const store = new Map<string, { data: ArrayBuffer; httpMetadata: Record<string, string>; customMetadata: Record<string, string> }>();
  const env = {
    SHADOW_FILES: {
      put: async (key: string, data: ArrayBuffer, opts: { httpMetadata: Record<string, string>; customMetadata: Record<string, string> }) => {
        store.set(key, { data, ...opts });
      },
      list: async ({ prefix }: { prefix: string }) => ({
        truncated: false,
        objects: [...store.entries()].filter(([k]) => k.startsWith(prefix)).map(([key, o]) => ({
          key, size: o.data.byteLength, httpMetadata: o.httpMetadata, customMetadata: o.customMetadata,
        })),
      }),
    },
  } as unknown as Env;
  return { env, store };
}

function sealedUpload(plainType: string | null) {
  const form = new FormData();
  form.append("file", new File([new Uint8Array([0xc1, 0x2e, 0x03])], "notes.pdf", { type: SEALED_TYPE }));
  if (plainType) form.append("plain_type", plainType);
  return new Request("https://x/v1/files/upload", { method: "POST", body: form });
}

describe("sealed uploads", () => {
  it("stores ciphertext with the real type in metadata and lists it as sealed", async () => {
    const { env, store } = bucket();
    const res = await uploadFile(sealedUpload("application/pdf"), env, alice, {});
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ ok: true, name: "notes.pdf", type: "application/pdf", sealed: true });
    const [obj] = [...store.values()];
    expect(obj.httpMetadata.contentType).toBe(SEALED_TYPE);
    expect(obj.httpMetadata.contentDisposition).toMatch(/^attachment;/);
    expect(obj.customMetadata).toMatchObject({ sealed: "1", plain_type: "application/pdf" });

    const list = (await (await listFiles(new Request("https://x/v1/files"), env, alice, {})).json()) as { files: { type: string; sealed: boolean }[] };
    expect(list.files[0]).toMatchObject({ type: "application/pdf", sealed: true });
  });

  it("refuses a sealed upload whose real type is missing or not allowed", async () => {
    const { env } = bucket();
    expect((await uploadFile(sealedUpload(null), env, alice, {})).status).toBe(415);
    expect((await uploadFile(sealedUpload("application/x-msdownload"), env, alice, {})).status).toBe(415);
  });

  it("still lists plain uploads as not sealed", async () => {
    const { env } = bucket();
    const form = new FormData();
    form.append("file", new File(["hello"], "a.txt", { type: "text/plain" }));
    await uploadFile(new Request("https://x/v1/files/upload", { method: "POST", body: form }), env, alice, {});
    const list = (await (await listFiles(new Request("https://x/v1/files"), env, alice, {})).json()) as { files: { type: string; sealed: boolean }[] };
    expect(list.files[0]).toMatchObject({ type: "text/plain", sealed: false });
  });
});
