import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import * as openpgp from "openpgp";
import type { Env } from "../index";

const db = vi.hoisted(() => ({
  rows: [] as Record<string, unknown>[],
  inserted: [] as Record<string, unknown>[],
  updated: [] as Record<string, unknown>[],
  lookup: vi.fn(),
}));

vi.mock("../supabase", () => ({
  dbSelect: vi.fn(async (_env: unknown, _table: string, opts: { filters?: Record<string, string> }) => {
    const [[col, cond]] = Object.entries(opts.filters ?? {});
    const want = cond.replace(/^eq\./, "");
    return db.rows.filter((r) => r[col] === want);
  }),
  dbInsert: vi.fn(async (_env: unknown, _t: string, row: Record<string, unknown>) => {
    db.inserted.push(row);
    db.rows.push(row);
    return row;
  }),
  dbUpdate: vi.fn(async (_env: unknown, _t: string, _f: unknown, patch: Record<string, unknown>) => {
    db.updated.push(patch);
    return patch;
  }),
  lookupAuthUserByEmail: db.lookup,
}));
vi.mock("../audit", () => ({ audit: vi.fn(async () => undefined), clientHints: () => ({}) }));

import { getKdfParams, lookupIdentity, getMyIdentity, saveMyIdentity } from "../identity";

const env = {} as Env;
const cors = {};
const alice = { id: "u-alice", email: "alice@shadowcypher.site", handle: "alice" };

type Bundle = { public_key: string; encrypted_private_key: string; recovery_private_key: string; fingerprint: string };

async function makeBundle(handle: string): Promise<Bundle> {
  const { privateKey } = await openpgp.generateKey({
    type: "ecc",
    userIDs: [{ name: handle, email: `${handle}@shadowcypher.site` }],
    format: "object",
  });
  return {
    public_key: privateKey.toPublic().armor(),
    encrypted_private_key: (await openpgp.encryptKey({ privateKey, passphrase: "kek" })).armor(),
    recovery_private_key: (await openpgp.encryptKey({ privateKey, passphrase: "phrase" })).armor(),
    fingerprint: privateKey.getFingerprint(),
  };
}

function post(body: unknown): Request {
  return new Request("https://api.shadowcypher.site/v1/identity/me", { method: "POST", body: JSON.stringify(body) });
}
const get = (path: string) => new Request(`https://api.shadowcypher.site${path}`);
const read = async (r: Response) => ({ status: r.status, body: (await r.json()) as Record<string, unknown> });

let aliceKeys: Bundle;
let otherKeys: Bundle;
let bobKeys: Bundle;

beforeAll(async () => {
  [aliceKeys, otherKeys, bobKeys] = await Promise.all([makeBundle("alice"), makeBundle("alice"), makeBundle("bob")]);
});

beforeEach(() => {
  db.rows.length = 0;
  db.inserted.length = 0;
  db.updated.length = 0;
  db.lookup.mockReset();
});

describe("GET /v1/auth/kdf", () => {
  const kdf = { v: 1, alg: "argon2id", m: 65536, t: 3, p: 1, salt: "AAAAAAAAAAAAAAAAAAAAAA==" };

  it("returns the stored parameters for an upgraded account", async () => {
    db.lookup.mockResolvedValue({ id: "u", email: "alice@shadowcypher.site", user_metadata: { kdf: { ...kdf, extra: "x" } } });
    expect(await read(await getKdfParams(get("/v1/auth/kdf?handle=Alice"), env, cors))).toEqual({ status: 200, body: kdf });
    expect(db.lookup).toHaveBeenCalledWith(env, "alice@shadowcypher.site");
  });

  it("answers v0 for legacy and unknown accounts alike", async () => {
    db.lookup.mockResolvedValueOnce({ id: "u", user_metadata: {} }).mockResolvedValueOnce(null);
    expect((await read(await getKdfParams(get("/v1/auth/kdf?handle=old"), env, cors))).body).toEqual({ v: 0 });
    expect((await read(await getKdfParams(get("/v1/auth/kdf?handle=nobody"), env, cors))).body).toEqual({ v: 0 });
  });

  it("does not pass through weakened parameters", async () => {
    db.lookup.mockResolvedValue({ id: "u", user_metadata: { kdf: { ...kdf, m: 1024 } } });
    expect((await read(await getKdfParams(get("/v1/auth/kdf?handle=alice"), env, cors))).body).toEqual({ v: 0 });
  });

  it("fails closed when the user lookup is down", async () => {
    db.lookup.mockRejectedValue(new Error("auth_lookup_failed:503"));
    expect((await getKdfParams(get("/v1/auth/kdf?handle=alice"), env, cors)).status).toBe(503);
  });

  it("rejects malformed handles without a lookup", async () => {
    expect((await getKdfParams(get("/v1/auth/kdf?handle=a%40b"), env, cors)).status).toBe(400);
    expect(db.lookup).not.toHaveBeenCalled();
  });
});

describe("POST /v1/identity/me", () => {
  it("stores a new, locked bundle", async () => {
    const { status, body } = await read(await saveMyIdentity(post(aliceKeys), env, alice, cors));
    expect(status).toBe(200);
    expect(body).toMatchObject({ fingerprint: aliceKeys.fingerprint, created: true });
    expect(db.inserted[0]).toMatchObject({ user_id: "u-alice", handle: "alice", fingerprint: aliceKeys.fingerprint });
  });

  it("refuses a private key that is not encrypted", async () => {
    const { privateKey } = await openpgp.generateKey({
      type: "ecc", userIDs: [{ email: "alice@shadowcypher.site" }], format: "object",
    });
    const bundle = { public_key: privateKey.toPublic().armor(), encrypted_private_key: privateKey.armor() };
    expect(await read(await saveMyIdentity(post(bundle), env, alice, cors)))
      .toEqual({ status: 400, body: { error: "private_key_not_encrypted" } });
    expect(db.inserted).toHaveLength(0);
  });

  it("refuses a key issued for another handle", async () => {
    expect((await read(await saveMyIdentity(post(bobKeys), env, alice, cors))).body.error).toBe("user_id_mismatch");
  });

  it("refuses private and public halves from different keys", async () => {
    const mixed = { ...aliceKeys, encrypted_private_key: otherKeys.encrypted_private_key };
    expect((await read(await saveMyIdentity(post(mixed), env, alice, cors))).body.error).toBe("fingerprint_mismatch");
  });

  it("refuses a private key uploaded as the public key", async () => {
    const swapped = { ...aliceKeys, public_key: aliceKeys.encrypted_private_key };
    expect((await read(await saveMyIdentity(post(swapped), env, alice, cors))).body.error).toBe("public_key_is_private");
  });

  it("re-locks the same key in place (password change)", async () => {
    db.rows.push({ user_id: "u-alice", handle: "alice", fingerprint: aliceKeys.fingerprint });
    const { status, body } = await read(await saveMyIdentity(post(aliceKeys), env, alice, cors));
    expect(status).toBe(200);
    expect(body.created).toBe(false);
    expect(db.updated[0]).toHaveProperty("encrypted_private_key", aliceKeys.encrypted_private_key);
    expect(db.updated[0]).not.toHaveProperty("public_key");
  });

  it("will not swap in a different key without replace:true", async () => {
    db.rows.push({ user_id: "u-alice", handle: "alice", fingerprint: aliceKeys.fingerprint });
    expect(await read(await saveMyIdentity(post(otherKeys), env, alice, cors)))
      .toEqual({ status: 409, body: { error: "identity_exists", fingerprint: aliceKeys.fingerprint } });
    expect(db.updated).toHaveLength(0);

    const replaced = await read(await saveMyIdentity(post({ ...otherKeys, replace: true }), env, alice, cors));
    expect(replaced.body).toMatchObject({ replaced: true, fingerprint: otherKeys.fingerprint });
    expect(db.updated[0]).toHaveProperty("public_key", otherKeys.public_key);
  });

  it("requires the account to have a handle", async () => {
    expect((await saveMyIdentity(post(aliceKeys), env, { id: "x", email: "x@y" }, cors)).status).toBe(400);
  });
});

describe("reading keys", () => {
  it("returns only the public half to other people", async () => {
    db.rows.push({ user_id: "u-alice", handle: "alice", ...aliceKeys });
    const { body } = await read(await lookupIdentity(get("/v1/identity/lookup?handle=alice"), env, cors));
    expect(body).toEqual({ handle: "alice", fingerprint: aliceKeys.fingerprint, public_key: aliceKeys.public_key });
  });

  it("returns the owner's locked bundle, or 404", async () => {
    expect((await getMyIdentity(get("/v1/identity/me"), env, alice, cors)).status).toBe(404);
    db.rows.push({ user_id: "u-alice", handle: "alice", ...aliceKeys });
    expect((await getMyIdentity(get("/v1/identity/me"), env, alice, cors)).status).toBe(200);
  });
});
