/// <reference types="node" />
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  ADMIN_EMAIL, RESERVED_HANDLES, handleOf, inboxFor, isBlockedSender, isReservedHandle,
} from "../reserved";

describe("reserved handles", () => {
  it("covers every address the site publishes", () => {
    for (const h of ["security", "privacy", "legal", "billing", "hello", "shadow"]) {
      expect(isReservedHandle(h)).toBe(true);
    }
  });

  it("ignores case and surrounding space", () => {
    expect(isReservedHandle("  Security ")).toBe(true);
    expect(isReservedHandle("alice")).toBe(false);
  });

  it("only contains names sign-up could otherwise accept", () => {
    for (const h of RESERVED_HANDLES) expect(h).toMatch(/^[a-z0-9_]{2,32}$/);
  });

  it("matches the list the database enforces", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const sql = readFileSync(resolve(here, "../../migrations/0024_reserved_handles.sql"), "utf8");
    const block = sql.match(/reserved constant text\[\] := array\[(.*?)\];/s);
    expect(block).not.toBeNull();
    const inSql = [...block![1].matchAll(/'([^']+)'/g)].map((m) => m[1]).sort();
    expect(inSql).toEqual([...RESERVED_HANDLES].sort());
  });
});

describe("mail routing for role addresses", () => {
  it("sends role mail to the operator's inbox", () => {
    expect(inboxFor("security")).toBe(ADMIN_EMAIL);
    expect(inboxFor("Privacy")).toBe(ADMIN_EMAIL);
  });

  it("leaves ordinary handles alone", () => {
    expect(inboxFor("alice")).toBe("alice@shadowcypher.site");
  });

  it("reads the handle only from this domain", () => {
    expect(handleOf("Alice@ShadowCypher.site")).toBe("alice");
    expect(handleOf("security@example.com")).toBeNull();
  });

  it("blocks sending from a role name unless it is the operator", () => {
    expect(isBlockedSender("security@shadowcypher.site")).toBe(true);
    expect(isBlockedSender(ADMIN_EMAIL)).toBe(false);
    expect(isBlockedSender("alice@shadowcypher.site")).toBe(false);
    expect(isBlockedSender("security@example.com")).toBe(false);
  });
});
