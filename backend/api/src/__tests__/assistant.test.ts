import { describe, it, expect } from "vitest";
import {
  parseMode, buildSystemPrompt, wantsNetworkData, wantsWebSearch,
  communityBlocked, maxQuestionLength, formatWebResults,
} from "../assistant";

describe("assistant modes", () => {
  it("defaults to security mode", () => {
    expect(parseMode(undefined)).toBe("security");
    expect(parseMode("anything")).toBe("security");
    expect(parseMode("general")).toBe("general");
  });

  it("general prompt carries the date and voice style only when asked", () => {
    const now = new Date("2026-11-04T12:00:00Z");
    const text = buildSystemPrompt("general", false, now);
    expect(text).toContain("2026-11-04");
    expect(text).not.toContain("read aloud");
    expect(buildSystemPrompt("general", true, now)).toContain("read aloud");
    expect(buildSystemPrompt("security", true, now)).toContain("security advisor");
  });

  it("only sends network data for security questions in general mode", () => {
    expect(wantsNetworkData("security", "what is the capital of France")).toBe(true);
    expect(wantsNetworkData("general", "what is the capital of France")).toBe(false);
    expect(wantsNetworkData("general", "any new devices on my network?")).toBe(true);
    expect(wantsNetworkData("general", "is my firewall on")).toBe(true);
  });

  it("searches the web for time-sensitive general questions or when asked", () => {
    expect(wantsWebSearch("general", "who won the game last night, latest score", undefined)).toBe(true);
    expect(wantsWebSearch("general", "what's the weather tomorrow", undefined)).toBe(true);
    expect(wantsWebSearch("general", "explain photosynthesis", undefined)).toBe(false);
    expect(wantsWebSearch("general", "explain photosynthesis", true)).toBe(true);
    expect(wantsWebSearch("general", "latest news", false)).toBe(false);
    expect(wantsWebSearch("security", "latest news", true)).toBe(false);
  });

  it("allows longer questions in general mode", () => {
    expect(maxQuestionLength("security")).toBe(800);
    expect(maxQuestionLength("general")).toBe(4000);
  });
});

describe("community plan gate", () => {
  it("blocks the platform provider on community", () => {
    expect(communityBlocked("community", "platform", false, false)).toBe(true);
  });
  it("allows a configured own key or Ollama on community", () => {
    expect(communityBlocked("community", "byok", true, false)).toBe(false);
    expect(communityBlocked("community", "ollama", false, true)).toBe(false);
  });
  it("blocks a provider that is selected but not configured", () => {
    expect(communityBlocked("community", "byok", false, false)).toBe(true);
    expect(communityBlocked("community", "ollama", false, false)).toBe(true);
  });
  it("never blocks paid plans", () => {
    expect(communityBlocked("guardian_pro", "platform", false, false)).toBe(false);
    expect(communityBlocked("operator", "platform", false, false)).toBe(false);
  });
});

describe("formatWebResults", () => {
  it("numbers results and truncates long snippets", () => {
    const out = formatWebResults([
      { title: "A", url: "https://a.example", snippet: "x".repeat(900) },
      { title: "B", url: "https://b.example", snippet: "" },
    ]);
    expect(out).toContain("[1] A (https://a.example)");
    expect(out).toContain("[2] B (https://b.example)");
    expect(out.split("\n")[1].length).toBe(500);
  });
});

import { extractAnswer, extractSources } from "../assistant";

describe("Claude general-mode response parsing", () => {
  const blocks = [
    { type: "thinking", text: "" },
    { type: "server_tool_use" },
    { type: "web_search_tool_result", content: [
      { type: "web_search_result", url: "https://a.example", title: "A" },
      { type: "web_search_result", url: "https://b.example", title: "B" },
    ] },
    { type: "text", text: "The answer is " },
    { type: "text", text: "42.", citations: [{ type: "web_search_result_location", url: "https://b.example", title: "B" }] },
  ];

  it("joins split text blocks and skips tool and thinking blocks", () => {
    expect(extractAnswer(blocks)).toBe("The answer is 42.");
  });

  it("prefers cited pages for sources", () => {
    expect(extractSources(blocks).map((s) => s.url)).toEqual(["https://b.example"]);
  });

  it("falls back to search results when nothing is cited", () => {
    const uncited = blocks.slice(0, 4);
    expect(extractSources(uncited).map((s) => s.url)).toEqual(["https://a.example", "https://b.example"]);
  });

  it("handles a search error object without crashing", () => {
    expect(extractSources([{ type: "web_search_tool_result", content: { error_code: "max_uses_exceeded" } }])).toEqual([]);
  });
});
