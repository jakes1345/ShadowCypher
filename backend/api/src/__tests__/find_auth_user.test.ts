import { describe, it, expect, vi, afterEach } from "vitest";
import { findAuthUserByEmail } from "../supabase";
import type { Env } from "../index";

const env = { SUPABASE_URL: "https://db.example", SUPABASE_SERVICE_ROLE_KEY: "svc" } as unknown as Env;

function page(emails: string[]) {
  return new Response(JSON.stringify({ users: emails.map((email, i) => ({ id: `id-${email}-${i}`, email })) }));
}

afterEach(() => vi.unstubAllGlobals());

describe("findAuthUserByEmail", () => {
  it("returns the exact match, not the first row", async () => {
    // Substring filter: "al@" also matches "val@", which sorts first.
    const fetchMock = vi.fn().mockResolvedValue(page(["val@shadowcypher.site", "al@shadowcypher.site"]));
    vi.stubGlobal("fetch", fetchMock);
    const u = await findAuthUserByEmail(env, "AL@shadowcypher.site");
    expect(u?.email).toBe("al@shadowcypher.site");
    const url = new URL(fetchMock.mock.calls[0][0] as string);
    expect(url.searchParams.get("filter")).toBe("al@shadowcypher.site");
    expect(url.searchParams.has("email")).toBe(false);
  });

  it("returns null when the server ignores the filter and no row matches", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page(["someone@shadowcypher.site"])));
    expect(await findAuthUserByEmail(env, "nobody@shadowcypher.site")).toBeNull();
  });

  it("pages until it finds the match", async () => {
    const first = Array.from({ length: 50 }, (_, i) => `x${i}al@shadowcypher.site`);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(page(first))
      .mockResolvedValueOnce(page(["al@shadowcypher.site"]));
    vi.stubGlobal("fetch", fetchMock);
    expect((await findAuthUserByEmail(env, "al@shadowcypher.site"))?.email).toBe("al@shadowcypher.site");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("returns null on an API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("down", { status: 503 })));
    expect(await findAuthUserByEmail(env, "al@shadowcypher.site")).toBeNull();
  });
});
