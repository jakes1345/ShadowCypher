import { describe, it, expect, vi, afterEach, beforeAll } from "vitest";
import * as openpgp from "openpgp";
import { fakeBackend } from "./helpers/fake_backend";
import { sendOutbound, storeInboundMail, getMail } from "../mail";
import { sealBody, previewFor } from "../mail_crypto";

const ALICE = "11111111-1111-4111-8111-111111111111";
const BOB = "22222222-2222-4222-8222-222222222222";

let alicePriv: openpgp.PrivateKey;
let alicePub: string;

beforeAll(async () => {
  const { privateKey, publicKey } = await openpgp.generateKey({
    type: "ecc",
    curve: "curve25519Legacy",
    userIDs: [{ name: "alice", email: "alice@shadowcypher.site" }],
    format: "armored",
  });
  alicePriv = await openpgp.readPrivateKey({ armoredKey: privateKey });
  alicePub = publicKey;
});

afterEach(() => vi.unstubAllGlobals());

async function open(armored: string, key: openpgp.PrivateKey) {
  const message = await openpgp.readMessage({ armoredMessage: armored });
  const { data } = await openpgp.decrypt({ message, decryptionKeys: key });
  return JSON.parse(data as string);
}

function backend(withKey: boolean) {
  return fakeBackend({
    authEmails: { [ALICE]: "alice@shadowcypher.site", [BOB]: "bob@shadowcypher.site" },
    tables: {
      mail_messages: [],
      user_keys: withKey ? [{ user_id: ALICE, handle: "alice", fingerprint: "x", public_key: alicePub, encrypted_private_key: "x" }] : [],
    },
  });
}

const inbound = (to: string) => ({
  to, from: "someone@example.com",
  headers: new Headers({ subject: "Hello", "message-id": "<9@example.com>", date: "Sat, 14 Nov 2026 10:00:00 +0000" }),
}) as unknown as ForwardableEmailMessage;
const RAW = "Subject: Hello\r\nContent-Type: text/plain\r\n\r\nThe launch code is 0000.\r\n";

describe("sealBody", () => {
  it("round-trips text and html through the owner's key", async () => {
    const armored = await sealBody(alicePub, "plain body", "<p>html body</p>");
    expect(armored).toContain("BEGIN PGP MESSAGE");
    expect(armored).not.toContain("plain body");
    expect(await open(armored, alicePriv)).toEqual({ v: 1, text: "plain body", html: "<p>html body</p>" });
  });
});

describe("previewFor", () => {
  it("gives no body preview for sealed mail", () => {
    expect(previewFor({ body_text: null, body_html: null, body_pgp: "-----BEGIN PGP MESSAGE-----" }, "secret")).toBe("");
    expect(previewFor({ body_text: "hi", body_html: null, body_pgp: null }, "  hi   there ")).toBe("hi there");
  });
});

describe("mail at rest", () => {
  it("seals inbound mail for an account with an identity key", async () => {
    const be = backend(true);
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("alice@shadowcypher.site"), RAW);
    const row = be.tables.mail_messages[0];
    expect(row.body_text).toBeNull();
    expect(row.body_html).toBeNull();
    expect(JSON.stringify(row)).not.toContain("launch code");
    expect((await open(row.body_pgp as string, alicePriv)).text).toContain("The launch code is 0000.");
  });

  it("keeps plaintext for an account without a key", async () => {
    const be = backend(false);
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("alice@shadowcypher.site"), RAW);
    const row = be.tables.mail_messages[0];
    expect(row.body_pgp).toBeNull();
    expect(row.body_text).toContain("The launch code is 0000.");
  });

  it("seals internal delivery for the recipient and leaves the sender's copy in the clear when the sender has no key", async () => {
    const be = backend(true);
    vi.stubGlobal("fetch", be.fetch);
    const req = new Request("https://api/v1/mail/send", {
      method: "POST",
      body: JSON.stringify({ to: "alice@shadowcypher.site", subject: "Hi", text: "meet at noon" }),
    });
    const res = await sendOutbound(req, be.env, { id: BOB, email: "bob@shadowcypher.site" }, {});
    expect(res.status).toBe(200);
    const toAlice = be.tables.mail_messages.find((m) => m.user_id === ALICE)!;
    const bobCopy = be.tables.mail_messages.find((m) => m.user_id === BOB)!;
    expect(toAlice.body_text).toBeNull();
    expect((await open(toAlice.body_pgp as string, alicePriv)).text).toBe("meet at noon");
    expect(bobCopy.body_text).toBe("meet at noon");
  });

  it("returns body_pgp from GET /v1/mail/:id so the browser can open it", async () => {
    const be = backend(true);
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("alice@shadowcypher.site"), RAW);
    be.tables.mail_messages[0].id = "m1"; // Postgres assigns ids; the fake does not.
    const res = await getMail(new Request("https://api/v1/mail/m1"), be.env, { id: ALICE, email: "alice@shadowcypher.site" }, {}, "m1");
    const body = (await res.json()) as { body_pgp?: string };
    expect(body.body_pgp).toContain("BEGIN PGP MESSAGE");
  });
});
