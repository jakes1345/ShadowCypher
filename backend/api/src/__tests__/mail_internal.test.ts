import { describe, it, expect } from "vitest";
import { bareAddress, isInternalAddress } from "../mail";

describe("bareAddress", () => {
  it("strips display names and lowercases", () => {
    expect(bareAddress("Alice <Alice@ShadowCypher.site>")).toBe("alice@shadowcypher.site");
    expect(bareAddress("  bob@example.com ")).toBe("bob@example.com");
  });
});

describe("isInternalAddress", () => {
  it("accepts handles on shadowcypher.site", () => {
    expect(isInternalAddress("ghost_01@shadowcypher.site")).toBe(true);
    expect(isInternalAddress("Ghost <ghost@shadowcypher.site>")).toBe(true);
  });

  it("rejects other domains and look-alikes", () => {
    expect(isInternalAddress("ghost@gmail.com")).toBe(false);
    expect(isInternalAddress("ghost@shadowcypher.site.evil.com")).toBe(false);
    expect(isInternalAddress("ghost@mail.shadowcypher.site")).toBe(false);
    expect(isInternalAddress("a@shadowcypher.site")).toBe(false);
  });
});
