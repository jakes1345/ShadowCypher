import { describe, it, expect } from "vitest";
import {
  decodeMimeWords,
  decodeQuotedPrintable,
  parseHeaders,
  parseMimeParts,
  extractBodies,
} from "../mime";

// ── decodeMimeWords ───────────────────────────────────────────────────────────

describe("decodeMimeWords", () => {
  it("passes plain ASCII through unchanged", () => {
    expect(decodeMimeWords("Hello World")).toBe("Hello World");
  });

  it("decodes base64-encoded UTF-8 subject", () => {
    // =?UTF-8?B?SGVsbG8gV29ybGQ=?= → "Hello World"
    expect(decodeMimeWords("=?UTF-8?B?SGVsbG8gV29ybGQ=?=")).toBe("Hello World");
  });

  it("decodes Q-encoded word (uppercase encoding designator)", () => {
    // =?ISO-8859-1?Q?Keld_J=F8rn_Simonsen?= → "Keld Jørn Simonsen"
    const result = decodeMimeWords("=?ISO-8859-1?Q?Keld_J=F8rn_Simonsen?=");
    expect(result).toContain("Keld J");
    expect(result).toContain("rn Simonsen");
  });

  it("decodes Q-encoded underscore as space", () => {
    // =?UTF-8?Q?hello_world?= → "hello world"
    expect(decodeMimeWords("=?UTF-8?Q?hello_world?=")).toBe("hello world");
  });

  it("handles multiple encoded-words in one string", () => {
    const result = decodeMimeWords("=?UTF-8?B?SGVsbG8=?= =?UTF-8?B?V29ybGQ=?=");
    expect(result).toBe("Hello World");
  });

  it("leaves malformed encoded-words as-is without throwing", () => {
    expect(() => decodeMimeWords("=?UTF-8?Z?broken?=")).not.toThrow();
  });
});

// ── decodeQuotedPrintable ─────────────────────────────────────────────────────

describe("decodeQuotedPrintable", () => {
  it("decodes simple hex sequences", () => {
    expect(decodeQuotedPrintable("Hello=20World")).toBe("Hello World");
  });

  it("strips soft line breaks (=\\n)", () => {
    expect(decodeQuotedPrintable("Hello=\nWorld")).toBe("HelloWorld");
  });

  it("strips soft line breaks (=\\r\\n)", () => {
    expect(decodeQuotedPrintable("Hello=\r\nWorld")).toBe("HelloWorld");
  });

  it("decodes é (=E9)", () => {
    expect(decodeQuotedPrintable("caf=E9")).toBe("caf\xe9");
  });

  it("passes plain text through unchanged", () => {
    expect(decodeQuotedPrintable("plain text")).toBe("plain text");
  });
});

// ── parseHeaders ──────────────────────────────────────────────────────────────

describe("parseHeaders", () => {
  it("parses a single header", () => {
    const h = parseHeaders("Content-Type: text/plain");
    expect(h.get("content-type")).toBe("text/plain");
  });

  it("lowercases header names", () => {
    const h = parseHeaders("Subject: Test Email");
    expect(h.get("subject")).toBe("Test Email");
  });

  it("parses multiple headers", () => {
    const raw = "From: alice@example.com\r\nTo: bob@example.com\r\nSubject: Hi";
    const h = parseHeaders(raw);
    expect(h.get("from")).toBe("alice@example.com");
    expect(h.get("to")).toBe("bob@example.com");
    expect(h.get("subject")).toBe("Hi");
  });

  it("handles headers with colon in value", () => {
    const h = parseHeaders("X-Header: value:with:colons");
    expect(h.get("x-header")).toBe("value:with:colons");
  });

  it("normalises CRLF and LF header separators", () => {
    const crlf = parseHeaders("A: 1\r\nB: 2");
    const lf = parseHeaders("A: 1\nB: 2");
    expect(crlf.get("a")).toBe(lf.get("a"));
    expect(crlf.get("b")).toBe(lf.get("b"));
  });
});

// ── parseMimeParts ────────────────────────────────────────────────────────────

describe("parseMimeParts", () => {
  it("returns a single part for a non-multipart message", () => {
    const raw = "Content-Type: text/plain\n\nHello, world!";
    const parts = parseMimeParts(raw);
    expect(parts).toHaveLength(1);
    expect(parts[0].body).toBe("Hello, world!");
  });

  it("splits a multipart/alternative into two parts", () => {
    const raw = [
      'Content-Type: multipart/alternative; boundary="boundary42"',
      "",
      "--boundary42",
      "Content-Type: text/plain",
      "",
      "Plain body",
      "--boundary42",
      "Content-Type: text/html",
      "",
      "<p>HTML body</p>",
      "--boundary42--",
    ].join("\n");

    const parts = parseMimeParts(raw);
    expect(parts).toHaveLength(2);
    const types = parts.map((p) => p.headers.get("content-type"));
    expect(types).toContain("text/plain");
    expect(types).toContain("text/html");
  });
});

// ── extractBodies ─────────────────────────────────────────────────────────────

describe("extractBodies", () => {
  it("extracts plain text from a simple message", () => {
    const raw = "Content-Type: text/plain\n\nHello!";
    const { text, html } = extractBodies(raw);
    expect(text).toBe("Hello!");
    expect(html).toBeNull();
  });

  it("extracts HTML from a simple HTML message", () => {
    const raw = "Content-Type: text/html\n\n<p>Hi</p>";
    const { text, html } = extractBodies(raw);
    expect(html).toBe("<p>Hi</p>");
    expect(text).toBeNull();
  });

  it("extracts both parts from multipart/alternative", () => {
    const raw = [
      'Content-Type: multipart/alternative; boundary="b"',
      "",
      "--b",
      "Content-Type: text/plain",
      "",
      "Plain",
      "--b",
      "Content-Type: text/html",
      "",
      "<p>HTML</p>",
      "--b--",
    ].join("\n");

    const { text, html } = extractBodies(raw);
    expect(text).toBe("Plain");
    expect(html).toBe("<p>HTML</p>");
  });

  it("decodes quoted-printable body", () => {
    const raw = [
      "Content-Type: text/plain",
      "Content-Transfer-Encoding: quoted-printable",
      "",
      "Hello=20World",
    ].join("\n");
    const { text } = extractBodies(raw);
    expect(text).toBe("Hello World");
  });

  it("decodes base64 body", () => {
    // "Hello" in base64
    const raw = [
      "Content-Type: text/plain",
      "Content-Transfer-Encoding: base64",
      "",
      "SGVsbG8=",
    ].join("\n");
    const { text } = extractBodies(raw);
    expect(text).toBe("Hello");
  });
});
