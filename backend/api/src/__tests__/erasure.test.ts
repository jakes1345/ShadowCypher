import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { fakeBackend, type FakeBackend } from "./helpers/fake_backend";

const neonDeleteUser = vi.fn(async (_env: unknown, _id: string) => {});
vi.mock("../neon", () => ({ neonDeleteUser: (env: unknown, id: string) => neonDeleteUser(env, id) }));

import { deleteUserFiles, eraseUser, ErasureError } from "../erasure";

const ALICE = "11111111-1111-4111-8111-111111111111";
const BOB = "22222222-2222-4222-8222-222222222222";

function seeded(): FakeBackend {
  return fakeBackend({
    authUsers: [ALICE, BOB],
    stripeCustomers: ["cus_alice", "cus_bob"],
    tables: {
      profiles: [
        { user_id: ALICE, stripe_customer_id: "cus_alice" },
        { user_id: BOB, stripe_customer_id: "cus_bob" },
      ],
      chat_messages: [
        { id: "m1", user_id: ALICE, content: "hi" },
        { id: "m2", user_id: BOB, content: "yo" },
        { id: "m3", user_id: ALICE, content: "bye" },
      ],
      chat_reactions: [{ message_id: "m2", user_id: ALICE, emoji: "x" }, { message_id: "m1", user_id: BOB, emoji: "y" }],
      chat_presence: [{ user_id: ALICE, room_id: "r1" }, { user_id: BOB, room_id: "r1" }],
      dm_read_receipts: [{ user_id: ALICE, room_id: "r1" }],
      missions: [{ id: "x1", user_id: ALICE, script_content: "scan" }, { id: "x2", user_id: BOB, script_content: "scan" }],
      chat_rooms: [{ id: "r1", created_by: ALICE }, { id: "r2", created_by: BOB }],
    },
    objects: {
      [`${ALICE}/a.txt`]: {},
      [`${ALICE}/docs/d1.html`]: {},
      [`${ALICE}/sheets/s1.json`]: {},
      [`${BOB}/b.txt`]: {},
    },
  });
}

let be: FakeBackend;
beforeEach(() => {
  be = seeded();
  neonDeleteUser.mockReset();
  neonDeleteUser.mockImplementation(async () => { be.calls.push("neon delete"); });
  vi.stubGlobal("fetch", be.fetch);
});
afterEach(() => vi.unstubAllGlobals());

describe("eraseUser", () => {
  it("removes everything stored for the user and nothing of anyone else's", async () => {
    const report = await eraseUser(be.env, ALICE);

    expect(report).toEqual({
      billing: "cancelled",
      files: 3,
      rows: { chat_reactions: 1, chat_messages: 2, chat_presence: 1, dm_read_receipts: 1, missions: 1 },
    });

    expect(be.stripeCustomers.has("cus_alice")).toBe(false);
    expect([...be.objects.keys()]).toEqual([`${BOB}/b.txt`]);
    expect(be.tables.chat_messages).toEqual([{ id: "m2", user_id: BOB, content: "yo" }]);
    expect(be.tables.chat_reactions.map((r) => r.user_id)).toEqual([BOB]);
    expect(be.tables.chat_presence.map((r) => r.user_id)).toEqual([BOB]);
    expect(be.tables.dm_read_receipts).toEqual([]);
    expect(be.tables.missions.map((r) => r.user_id)).toEqual([BOB]);
    expect(be.authUsers.has(ALICE)).toBe(false);

    // Bob is untouched
    expect(be.stripeCustomers.has("cus_bob")).toBe(true);
    expect(be.authUsers.has(BOB)).toBe(true);
    expect(neonDeleteUser).toHaveBeenCalledTimes(1);
    expect(neonDeleteUser.mock.calls[0][1]).toBe(ALICE);
  });

  it("keeps rooms the user created but drops their id from them", async () => {
    await eraseUser(be.env, ALICE);
    expect(be.tables.chat_rooms).toEqual([{ id: "r1", created_by: null }, { id: "r2", created_by: BOB }]);
  });

  it("stops billing first and deletes the sign-in last, after the mirror", async () => {
    await eraseUser(be.env, ALICE);
    const order = be.calls.filter((c) => c.startsWith("stripe") || c === "neon delete" || c.startsWith("auth"));
    expect(order).toEqual(["stripe DELETE cus_alice", "neon delete", `auth DELETE ${ALICE}`]);
    expect(be.calls.indexOf("stripe DELETE cus_alice")).toBeLessThan(be.calls.findIndex((c) => c.startsWith("r2")));
  });

  it("makes no Stripe call for a user who never had a customer", async () => {
    be.tables.profiles[0].stripe_customer_id = null;
    const report = await eraseUser(be.env, ALICE);
    expect(report.billing).toBe("none");
    expect(be.calls.some((c) => c.startsWith("stripe"))).toBe(false);
    expect(be.authUsers.has(ALICE)).toBe(false);
  });

  it("deletes nothing when billing cannot be cancelled", async () => {
    be.failWith = (label) => (label.startsWith("stripe") ? 500 : undefined);
    const err = await eraseUser(be.env, ALICE).catch((e) => e);
    expect(err).toBeInstanceOf(ErasureError);
    expect((err as ErasureError).step).toBe("billing");
    expect(be.objects.size).toBe(4);
    expect(be.tables.chat_messages).toHaveLength(3);
    expect(neonDeleteUser).not.toHaveBeenCalled();
    expect(be.authUsers.has(ALICE)).toBe(true);
  });

  it("keeps the sign-in when the mirror cannot be cleared, so the key cannot outlive the account", async () => {
    neonDeleteUser.mockRejectedValueOnce(new Error("neon down"));
    const err = await eraseUser(be.env, ALICE).catch((e) => e);
    expect((err as ErasureError).step).toBe("mirror");
    expect(be.authUsers.has(ALICE)).toBe(true);
    expect(be.calls.some((c) => c.startsWith("auth"))).toBe(false);
  });

  it("finishes on a retry after a failure part-way", async () => {
    neonDeleteUser.mockRejectedValueOnce(new Error("neon down"));
    await eraseUser(be.env, ALICE).catch(() => null);
    // second attempt: Stripe customer and files are already gone
    const report = await eraseUser(be.env, ALICE);
    expect(report).toEqual({
      billing: "cancelled",
      files: 0,
      rows: { chat_reactions: 0, chat_messages: 0, chat_presence: 0, dm_read_receipts: 0, missions: 0 },
    });
    expect(be.authUsers.has(ALICE)).toBe(false);
  });

  it("works on a database without the optional chat and mission tables", async () => {
    for (const t of ["chat_messages", "chat_reactions", "chat_presence", "dm_read_receipts", "missions", "chat_rooms"]) {
      delete be.tables[t];
    }
    const report = await eraseUser(be.env, ALICE);
    expect(report.rows.chat_messages).toBe(0);
    expect(be.authUsers.has(ALICE)).toBe(false);
  });

  it("refuses an id that is not a UUID before touching anything", async () => {
    const err = await eraseUser(be.env, "").catch((e) => e);
    expect((err as ErasureError).step).toBe("validate");
    expect(be.calls).toEqual([]);
  });
});

describe("deleteUserFiles", () => {
  it("pages through more objects than one listing returns", async () => {
    const objects: Record<string, Record<string, string>> = { [`${BOB}/keep.txt`]: {} };
    for (let i = 0; i < 2300; i++) objects[`${ALICE}/f${String(i).padStart(4, "0")}`] = {};
    be = fakeBackend({ objects });
    expect(await deleteUserFiles(be.env, ALICE)).toBe(2300);
    expect([...be.objects.keys()]).toEqual([`${BOB}/keep.txt`]);
    expect(be.calls.filter((c) => c.startsWith("r2 delete"))).toEqual(["r2 delete 1000", "r2 delete 1000", "r2 delete 300"]);
  });

  it("never lists outside the user's own prefix", async () => {
    await expect(deleteUserFiles(be.env, "")).rejects.toThrow("invalid_user_id");
    await expect(deleteUserFiles(be.env, "../")).rejects.toThrow("invalid_user_id");
    expect(be.objects.size).toBe(4);
  });
});
