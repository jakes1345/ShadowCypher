import { describe, it, expect, vi, afterEach } from "vitest";
import { dbDelete, dbSelectAll } from "../supabase";
import { fakeBackend } from "./helpers/fake_backend";

afterEach(() => vi.unstubAllGlobals());

describe("dbDelete", () => {
  it("refuses to run without a filter", async () => {
    const be = fakeBackend({ tables: { scans: [{ id: "1" }] } });
    vi.stubGlobal("fetch", be.fetch);
    await expect(dbDelete(be.env, "scans", {})).rejects.toThrow("db_delete_unfiltered:scans");
    expect(be.calls).toEqual([]);
    expect(be.tables.scans).toHaveLength(1);
  });

  it("returns how many rows went", async () => {
    const be = fakeBackend({ tables: { scans: [{ id: "1", user_id: "a" }, { id: "2", user_id: "a" }, { id: "3", user_id: "b" }] } });
    vi.stubGlobal("fetch", be.fetch);
    expect(await dbDelete(be.env, "scans", { user_id: "eq.a" })).toBe(2);
    expect(be.tables.scans).toEqual([{ id: "3", user_id: "b" }]);
  });

  it("treats a missing table as nothing to delete", async () => {
    const be = fakeBackend();
    vi.stubGlobal("fetch", be.fetch);
    expect(await dbDelete(be.env, "missions", { user_id: "eq.a" })).toBe(0);
  });

  it("throws on any other failure", async () => {
    const be = fakeBackend({ tables: { scans: [] } });
    be.failWith = () => 500;
    vi.stubGlobal("fetch", be.fetch);
    await expect(dbDelete(be.env, "scans", { user_id: "eq.a" })).rejects.toThrow("db_delete_failed:scans:500");
  });
});

describe("dbSelectAll", () => {
  const rows = Array.from({ length: 2005 }, (_, i) => ({ id: String(i).padStart(5, "0") }));

  it("reads past the per-request row cap", async () => {
    const be = fakeBackend({ tables: { scans: rows } });
    vi.stubGlobal("fetch", be.fetch);
    const out = await dbSelectAll<{ id: string }>(be.env, "scans", { order: "id.asc" });
    expect(out.truncated).toBe(false);
    expect(out.rows.map((r) => r.id)).toEqual(rows.map((r) => r.id));
    expect(be.calls).toHaveLength(3);
  });

  it("reports truncation at the cap", async () => {
    const be = fakeBackend({ tables: { scans: rows } });
    vi.stubGlobal("fetch", be.fetch);
    const out = await dbSelectAll(be.env, "scans", { order: "id.asc", maxRows: 2000 });
    expect(out.rows).toHaveLength(2000);
    expect(out.truncated).toBe(true);
  });
});
