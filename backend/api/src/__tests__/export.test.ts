import { describe, it, expect, vi, afterEach } from "vitest";
import { fakeBackend } from "./helpers/fake_backend";
import { buildExport } from "../account";

const ALICE = "11111111-1111-4111-8111-111111111111";
const BOB = "22222222-2222-4222-8222-222222222222";
const alice = { id: ALICE, email: "alice@shadowcypher.site" };

const ALL_TABLES = [
  "profiles", "user_profiles", "notification_prefs", "user_keys", "agents", "devices", "scans", "incidents",
  "cve_alerts_sent", "missions", "mail_messages", "chat_messages", "chat_reactions", "chat_presence",
  "dm_read_receipts", "chat_rooms", "calendar_events", "teams", "team_members", "referral_redemptions",
  "audit_log", "webhooks", "device_auth_codes",
];

function seed(overrides: Record<string, Record<string, unknown>[]> = {}) {
  const tables: Record<string, Record<string, unknown>[]> = Object.fromEntries(ALL_TABLES.map((t) => [t, []]));
  Object.assign(tables, {
    profiles: [{ user_id: ALICE, plan: "community" }, { user_id: BOB, plan: "operator" }],
    user_keys: [{ user_id: ALICE, fingerprint: "AAAA", public_key: "pub", encrypted_private_key: "locked" }],
    mail_messages: [
      { id: "1", user_id: ALICE, subject: "hello", body_text: "for alice" },
      { id: "2", user_id: BOB, subject: "secret", body_text: "for bob" },
    ],
    chat_messages: [{ id: "c1", user_id: ALICE, content: "hi" }, { id: "c2", user_id: BOB, content: "yo" }],
    calendar_events: [{ id: "e1", user_id: ALICE, title: "dentist" }],
    missions: [{ id: "m1", user_id: ALICE, script_content: "scan" }],
    teams: [{ id: "t1", owner_id: ALICE, name: "mine" }, { id: "t2", owner_id: BOB, name: "theirs" }],
    referral_redemptions: [
      { id: "r1", referrer_id: ALICE, referee_id: BOB },
      { id: "r2", referrer_id: BOB, referee_id: ALICE },
      { id: "r3", referrer_id: BOB, referee_id: "33333333-3333-4333-8333-333333333333" },
    ],
    webhooks: [{ id: "w1", user_id: ALICE, url: "https://hook.example", signing_secret: "whsec_do_not_export" }],
    device_auth_codes: [{ device_code: "dc_secret", user_id: ALICE, client_label: "desktop", status: "consumed" }],
    ...overrides,
  });
  return fakeBackend({
    tables,
    objects: {
      [`${ALICE}/9f.pdf`]: { original_name: "taxes.pdf", uploaded_at: "2026-10-01T00:00:00Z" },
      [`${ALICE}/docs/d1.html`]: { title: "Notes", updated_at: "2026-10-02T00:00:00Z" },
      [`${ALICE}/sheets/s1.json`]: { title: "Budget" },
      [`${BOB}/other.txt`]: { original_name: "bob.txt" },
    },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("buildExport", () => {
  it("includes the content the old export left out", async () => {
    const be = seed();
    vi.stubGlobal("fetch", be.fetch);
    const b = await buildExport(be.env, alice) as Record<string, any>;

    expect(b.mail).toEqual([{ id: "1", user_id: ALICE, subject: "hello", body_text: "for alice" }]);
    expect(b.chat_messages).toEqual([{ id: "c1", user_id: ALICE, content: "hi" }]);
    expect(b.calendar_events).toHaveLength(1);
    expect(b.missions).toHaveLength(1);
    expect(b.identity_keys).toMatchObject({ fingerprint: "AAAA", encrypted_private_key: "locked" });
    expect(b.teams_owned).toEqual([{ id: "t1", owner_id: ALICE, name: "mine" }]);
    expect(b.incomplete).toEqual([]);
  });

  it("lists files, docs and sheets with the route that returns each one", async () => {
    const be = seed();
    vi.stubGlobal("fetch", be.fetch);
    const b = await buildExport(be.env, alice) as Record<string, any>;

    expect(b.files).toEqual([{
      key: `${ALICE}/9f.pdf`, name: "taxes.pdf", size: `${ALICE}/9f.pdf`.length,
      updated_at: "2026-10-01T00:00:00Z", download: `/v1/files/${ALICE}/9f.pdf`,
    }]);
    expect(b.docs[0]).toMatchObject({ name: "Notes", download: "/v1/docs/d1" });
    expect(b.sheets[0]).toMatchObject({ name: "Budget", download: "/v1/sheets/s1" });
    expect(b.counts).toMatchObject({ files: 1, docs: 1, sheets: 1, mail: 1 });
  });

  it("never includes another user's rows or files", async () => {
    const be = seed();
    vi.stubGlobal("fetch", be.fetch);
    const text = JSON.stringify(await buildExport(be.env, alice));
    expect(text).not.toContain("for bob");
    expect(text).not.toContain("bob.txt");
    expect(text).not.toContain('"theirs"');
  });

  it("includes referrals in both directions and nobody else's", async () => {
    const be = seed();
    vi.stubGlobal("fetch", be.fetch);
    const b = await buildExport(be.env, alice) as Record<string, any>;
    expect(b.referrals.map((r: { id: string }) => r.id)).toEqual(["r1", "r2"]);
  });

  it("leaves out secrets the user never chose", async () => {
    const be = seed();
    vi.stubGlobal("fetch", be.fetch);
    const text = JSON.stringify(await buildExport(be.env, alice));
    expect(text).not.toContain("whsec_do_not_export");
    expect(text).not.toContain("dc_secret");
    expect(text).toContain("https://hook.example");
  });

  it("returns every row of a large collection, not just the first page", async () => {
    const scans = Array.from({ length: 2345 }, (_, i) => ({ id: String(i).padStart(6, "0"), user_id: ALICE }));
    const be = seed({ scans });
    vi.stubGlobal("fetch", be.fetch);
    const b = await buildExport(be.env, alice) as Record<string, any>;
    expect(b.scans).toHaveLength(2345);
    expect(new Set(b.scans.map((s: { id: string }) => s.id)).size).toBe(2345);
    expect(b.incomplete).toEqual([]);
  });

  it("says which parts are missing instead of passing off a partial copy", async () => {
    const be = seed();
    delete be.tables.calendar_events;
    be.failWith = (label) => (label === "GET mail_messages" ? 500 : undefined);
    vi.stubGlobal("fetch", be.fetch);
    const b = await buildExport(be.env, alice) as Record<string, any>;
    expect(b.incomplete).toEqual(["calendar_events", "mail"]);
    expect(b.chat_messages).toHaveLength(1);
  });
});
