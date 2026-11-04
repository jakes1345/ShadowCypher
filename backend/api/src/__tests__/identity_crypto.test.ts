/// <reference types="node" />
// Exercises www/js/identity.js with the exact vendored libraries the web app loads,
// so the client crypto contract is covered by the backend test run.
import { describe, it, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInThisContext } from "node:vm";

const require = createRequire(import.meta.url);
const WWW = resolve(dirname(fileURLToPath(import.meta.url)), "../../../../www");

type Identity = {
  KDF_V1: { v: number; m: number; t: number; p: number };
  newKdfParams(): { v: number; alg: string; m: number; t: number; p: number; salt: string };
  validateKdf(kdf: unknown): Uint8Array;
  deriveSecrets(pw: string, kdf: unknown): Promise<{ loginSecret: string; kek: string }>;
  newRecoveryPhrase(): string;
  normalizePhrase(p: string): string;
  createIdentity(handle: string): Promise<{ privateKey: any; publicKey: string; fingerprint: string }>;
  lockPrivateKey(key: any, secret: string): Promise<string>;
  unlockPrivateKey(armored: string, secret: string): Promise<any>;
  buildBundle(key: any, kek: string, phrase?: string): Promise<Record<string, string | undefined>>;
};

let ScIdentity: Identity;
let openpgp: any;
// Cheap params for speed; production uses 64 MiB.
const testKdf = (salt: string) => ({ v: 1, alg: "argon2id", m: 19456, t: 1, p: 1, salt });

beforeAll(() => {
  const g = globalThis as Record<string, unknown>;
  // The openpgp browser build declares `var openpgp`, as a <script> tag would.
  g.openpgp = runInThisContext(`${readFileSync(`${WWW}/vendor/openpgp-6.3.2.min.js`, "utf8")}\n;openpgp`);
  openpgp = g.openpgp;
  g.hashwasm = require(`${WWW}/vendor/hash-wasm-argon2-4.12.0.umd.min.js`);
  runInThisContext(readFileSync(`${WWW}/js/identity.js`, "utf8"));
  ScIdentity = g.ScIdentity as Identity;
});

describe("password split", () => {
  it("is deterministic and yields two distinct secrets", async () => {
    const kdf = testKdf(ScIdentity.newKdfParams().salt);
    const a = await ScIdentity.deriveSecrets("correct horse battery", kdf);
    const b = await ScIdentity.deriveSecrets("correct horse battery", kdf);
    expect(a).toEqual(b);
    expect(a.loginSecret).not.toBe(a.kek);
    expect(a.loginSecret).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(a.loginSecret.length).toBeLessThanOrEqual(72);
  });

  it("changes with the password and with the salt", async () => {
    const salt = ScIdentity.newKdfParams().salt;
    const base = await ScIdentity.deriveSecrets("password-one!", testKdf(salt));
    const otherPw = await ScIdentity.deriveSecrets("password-two!", testKdf(salt));
    const otherSalt = await ScIdentity.deriveSecrets("password-one!", testKdf(ScIdentity.newKdfParams().salt));
    expect(otherPw.loginSecret).not.toBe(base.loginSecret);
    expect(otherSalt.loginSecret).not.toBe(base.loginSecret);
  });

  it("uses 64 MiB Argon2id by default", () => {
    const p = ScIdentity.newKdfParams();
    expect(p).toMatchObject({ v: 1, alg: "argon2id", m: 65536, t: 3, p: 1 });
    expect(ScIdentity.validateKdf(p)).toHaveLength(16);
  });

  it("rejects weak or abusive parameters from the server", () => {
    const salt = ScIdentity.newKdfParams().salt;
    expect(() => ScIdentity.validateKdf({ ...testKdf(salt), m: 1024 })).toThrow();
    expect(() => ScIdentity.validateKdf({ ...testKdf(salt), m: 4_000_000 })).toThrow();
    expect(() => ScIdentity.validateKdf({ ...testKdf(salt), t: 0 })).toThrow();
    expect(() => ScIdentity.validateKdf({ ...testKdf(salt), alg: "pbkdf2" })).toThrow();
    expect(() => ScIdentity.validateKdf({ ...testKdf(salt), v: 2 })).toThrow();
    expect(() => ScIdentity.validateKdf({ ...testKdf("AAAA"), })).toThrow();
    expect(() => ScIdentity.validateKdf(null)).toThrow();
  });
});

describe("recovery phrase", () => {
  it("is 160 bits in 8 groups and normalizes loosely typed input", () => {
    const phrase = ScIdentity.newRecoveryPhrase();
    expect(phrase).toMatch(/^([A-HJ-NP-Z2-9]{4}-){7}[A-HJ-NP-Z2-9]{4}$/);
    const sloppy = phrase.toLowerCase().replace(/-/g, " ");
    expect(ScIdentity.normalizePhrase(sloppy)).toBe(phrase.replace(/-/g, ""));
    expect(ScIdentity.newRecoveryPhrase()).not.toBe(phrase);
  });

  it("rejects malformed phrases", () => {
    expect(() => ScIdentity.normalizePhrase("ABCD-EFGH")).toThrow();
    expect(() => ScIdentity.normalizePhrase("0".repeat(32))).toThrow();
  });
});

describe("identity keys", () => {
  it("creates a key for the handle and both locked copies unlock with the right secret only", async () => {
    const { privateKey, publicKey, fingerprint } = await ScIdentity.createIdentity("alice");
    const pub = await openpgp.readKey({ armoredKey: publicKey });
    expect(pub.isPrivate()).toBe(false);
    expect(pub.getFingerprint()).toBe(fingerprint);
    expect(pub.getUserIDs()).toEqual(["alice <alice@shadowcypher.site>"]);

    const { kek } = await ScIdentity.deriveSecrets("hunter2hunter2", testKdf(ScIdentity.newKdfParams().salt));
    const phrase = ScIdentity.newRecoveryPhrase();
    const bundle = await ScIdentity.buildBundle(privateKey, kek, phrase);

    // Uploaded copies are locked.
    for (const field of ["encrypted_private_key", "recovery_private_key"] as const) {
      const k = await openpgp.readPrivateKey({ armoredKey: bundle[field] });
      expect(k.isDecrypted()).toBe(false);
      expect(k.getFingerprint()).toBe(fingerprint);
    }
    // Locking a copy must not lock the in-memory key the app keeps using.
    expect(privateKey.isDecrypted()).toBe(true);

    const viaPassword = await ScIdentity.unlockPrivateKey(bundle.encrypted_private_key!, kek);
    const viaPhrase = await ScIdentity.unlockPrivateKey(bundle.recovery_private_key!, ScIdentity.normalizePhrase(phrase));
    expect(viaPassword.getFingerprint()).toBe(fingerprint);
    expect(viaPhrase.getFingerprint()).toBe(fingerprint);

    await expect(ScIdentity.unlockPrivateKey(bundle.encrypted_private_key!, "wrong")).rejects.toThrow();
    await expect(ScIdentity.unlockPrivateKey(bundle.recovery_private_key!, kek)).rejects.toThrow();
  });

  it("decrypts mail encrypted to the public key after a password change via the recovery phrase", async () => {
    const { privateKey, publicKey } = await ScIdentity.createIdentity("bob");
    const phrase = ScIdentity.newRecoveryPhrase();
    const oldKek = (await ScIdentity.deriveSecrets("old-password!!", testKdf(ScIdentity.newKdfParams().salt))).kek;
    const bundle = await ScIdentity.buildBundle(privateKey, oldKek, phrase);

    const message = await openpgp.encrypt({
      message: await openpgp.createMessage({ text: "hello bob" }),
      encryptionKeys: await openpgp.readKey({ armoredKey: publicKey }),
    });

    // Password forgotten: recover with the phrase, re-lock under the new password.
    const recovered = await ScIdentity.unlockPrivateKey(bundle.recovery_private_key!, ScIdentity.normalizePhrase(phrase));
    const newKek = (await ScIdentity.deriveSecrets("new-password!!", testKdf(ScIdentity.newKdfParams().salt))).kek;
    const relocked = await ScIdentity.lockPrivateKey(recovered, newKek);
    const unlocked = await ScIdentity.unlockPrivateKey(relocked, newKek);

    const { data } = await openpgp.decrypt({
      message: await openpgp.readMessage({ armoredMessage: message }),
      decryptionKeys: unlocked,
    });
    expect(data).toBe("hello bob");
  });
});
