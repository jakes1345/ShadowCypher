import { describe, it, expect, vi, afterEach } from "vitest";
import { fakeBackend } from "./helpers/fake_backend";
import { replyMail, sendOutbound, storeInboundMail } from "../mail";
import { getKdfParams } from "../identity";

const ADMIN = "00000000-0000-4000-8000-000000000001";
const ALICE = "11111111-1111-4111-8111-111111111111";
const SQUATTER = "99999999-9999-4999-8999-999999999999";

function backend(extraEmails: Record<string, string> = {}) {
  return fakeBackend({
    authEmails: { [ADMIN]: "shadow@shadowcypher.site", [ALICE]: "alice@shadowcypher.site", ...extraEmails },
    tables: { mail_messages: [] },
  });
}

function inbound(to: string, from = "reporter@example.com"): ForwardableEmailMessage {
  return {
    to, from,
    headers: new Headers({ subject: "Found a bug", "message-id": "<1@example.com>", date: "Sat, 14 Nov 2026 10:00:00 +0000" }),
  } as unknown as ForwardableEmailMessage;
}

const RAW = "Subject: Found a bug\r\nContent-Type: text/plain\r\n\r\nDetails inside.\r\n";
const post = (body: unknown) => new Request("https://api/v1/mail/send", { method: "POST", body: JSON.stringify(body) });

afterEach(() => vi.unstubAllGlobals());

describe("inbound mail to role addresses", () => {
  it.each(["security", "privacy", "legal", "billing", "hello", "abuse"])(
    "delivers %s@ to the operator's inbox and keeps the address it was sent to",
    async (role) => {
      const be = backend();
      vi.stubGlobal("fetch", be.fetch);
      await storeInboundMail(be.env, inbound(`${role}@shadowcypher.site`), RAW);
      expect(be.tables.mail_messages).toHaveLength(1);
      expect(be.tables.mail_messages[0]).toMatchObject({
        user_id: ADMIN, to_addr: `${role}@shadowcypher.site`, from_addr: "reporter@example.com", direction: "inbound",
      });
    },
  );

  it("does not hand role mail to an account that holds the role name", async () => {
    const be = backend({ [SQUATTER]: "security@shadowcypher.site" });
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("security@shadowcypher.site"), RAW);
    expect(be.tables.mail_messages.map((m) => m.user_id)).toEqual([ADMIN]);
  });

  it("still delivers ordinary mail to its owner", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("alice@shadowcypher.site"), RAW);
    expect(be.tables.mail_messages.map((m) => m.user_id)).toEqual([ALICE]);
  });

  it("drops mail for a handle nobody owns", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    await storeInboundMail(be.env, inbound("nobody_here@shadowcypher.site"), RAW);
    expect(be.tables.mail_messages).toEqual([]);
  });
});

describe("mail between users", () => {
  it("routes a user's message to security@ into the operator's inbox", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    const res = await sendOutbound(
      post({ to: "security@shadowcypher.site", subject: "report", text: "hi" }),
      be.env, { id: ALICE, email: "alice@shadowcypher.site" }, {},
    );
    expect(res.status).toBe(200);
    const inboxCopy = be.tables.mail_messages.find((m) => m.direction === "inbound");
    expect(inboxCopy).toMatchObject({ user_id: ADMIN, to_addr: "security@shadowcypher.site" });
  });
});

describe("sending from a role name", () => {
  const squatter = { id: SQUATTER, email: "billing@shadowcypher.site" };

  it("refuses an account that holds a role name", async () => {
    const be = backend({ [SQUATTER]: "billing@shadowcypher.site" });
    vi.stubGlobal("fetch", be.fetch);
    const res = await sendOutbound(post({ to: "victim@example.com", subject: "Invoice", text: "pay here" }), be.env, squatter, {});
    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ error: "reserved_sender" });
    expect(be.tables.mail_messages).toEqual([]);
  });

  it("refuses replies from it too", async () => {
    const be = backend({ [SQUATTER]: "billing@shadowcypher.site" });
    be.tables.mail_messages.push({ id: "m1", user_id: SQUATTER, message_id: "<a@b>", from_addr: "victim@example.com", subject: "Q" });
    vi.stubGlobal("fetch", be.fetch);
    const res = await replyMail(post({ text: "send your card" }), be.env, squatter, {}, "m1");
    expect(res.status).toBe(403);
  });

  it("lets the operator send", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    const res = await sendOutbound(
      post({ to: "alice@shadowcypher.site", subject: "Welcome", text: "hi" }),
      be.env, { id: ADMIN, email: "shadow@shadowcypher.site" }, {},
    );
    expect(res.status).toBe(200);
  });
});

describe("sign-up check", () => {
  const get = (handle: string) => new Request(`https://api/v1/auth/kdf?handle=${handle}`);

  it("flags a reserved handle so the form can say so before sign-up", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    expect(await (await getKdfParams(get("security"), be.env, {})).json()).toEqual({ v: 0, reserved: true });
  });

  it("answers exactly as before for any other handle", async () => {
    const be = backend();
    vi.stubGlobal("fetch", be.fetch);
    expect(await (await getKdfParams(get("alice"), be.env, {})).json()).toEqual({ v: 0 });
    expect(await (await getKdfParams(get("free_name"), be.env, {})).json()).toEqual({ v: 0 });
  });
});
