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

import { isWorkspaceId, packByok, unpackByok, providerError, anthropicHeaders } from "../assistant";

describe("BYOK workspace ID", () => {
  it("validates workspace IDs", () => {
    expect(isWorkspaceId("wrkspc_01AbCdEfGhIjKl")).toBe(true);
    expect(isWorkspaceId("wrkspc_")).toBe(false);
    expect(isWorkspaceId("sk-ant-abc")).toBe(false);
    expect(isWorkspaceId(undefined)).toBe(false);
  });

  it("round-trips key and workspace, and reads old bare-key blobs", () => {
    const packed = packByok({ key: "sk-ant-xyz", workspaceId: "wrkspc_01AbCdEfGhIjKl" });
    expect(unpackByok(packed)).toEqual({ key: "sk-ant-xyz", workspaceId: "wrkspc_01AbCdEfGhIjKl" });
    expect(packByok({ key: "sk-ant-xyz" })).toBe("sk-ant-xyz");
    expect(unpackByok("sk-ant-legacy")).toEqual({ key: "sk-ant-legacy" });
  });

  it("only sends the workspace header when set", () => {
    expect(anthropicHeaders("k")["anthropic-workspace-id"]).toBeUndefined();
    expect(anthropicHeaders("k", "wrkspc_01AbCdEfGhIjKl")["anthropic-workspace-id"]).toBe("wrkspc_01AbCdEfGhIjKl");
  });
});

describe("providerError", () => {
  it("turns an Anthropic 400 into a readable 400", () => {
    const r = providerError('anthropic_400:{"type":"error","error":{"type":"invalid_request_error","message":"This API key is not scoped to a workspace"}}');
    expect(r.status).toBe(400);
    expect(r.body.error).toBe("provider_rejected");
    expect(r.body.reason).toBe("Anthropic rejected the request: This API key is not scoped to a workspace");
  });
  it("keeps rate limits as 429 and server errors as 502", () => {
    expect(providerError("anthropic_429:{}").status).toBe(429);
    expect(providerError("anthropic_529:overloaded").status).toBe(502);
    expect(providerError("ollama_404:model not found").body.reason).toBe("Ollama rejected the request: model not found");
    expect(providerError("socket hang up").status).toBe(502);
  });
});

describe("providerError with cut-off JSON", () => {
  it("still extracts Anthropic's message", () => {
    const r = providerError('anthropic_400:{"type":"error","error":{"type":"invalid_request_error","message":"This API key is not scoped to a workspace."},"request_id":"req_01');
    expect(r.body.reason).toBe("Anthropic rejected the request: This API key is not scoped to a workspace.");
  });
});

import { extractToolErrors } from "../assistant";

describe("extractToolErrors", () => {
  it("reports web tool error codes and ignores successful results", () => {
    expect(extractToolErrors([
      { type: "web_search_tool_result", content: [{ type: "web_search_result", url: "https://a", title: "A" }] },
      { type: "web_search_tool_result", content: { type: "web_search_tool_result_error", error_code: "max_uses_exceeded" } },
      { type: "web_fetch_tool_result", content: { type: "web_fetch_tool_error", error_code: "url_not_accessible" } },
      { type: "text", text: "hi" },
    ])).toEqual(["web_search: max_uses_exceeded", "web_fetch: url_not_accessible"]);
  });
});

import { afterEach, vi } from "vitest";
import { chooseOllamaModel, listOllamaModels, resolveOllamaModel, OLLAMA_MODEL_PREFERENCE } from "../assistant";

describe("choosing a model on a user's Ollama server", () => {
  afterEach(() => vi.unstubAllGlobals());

  /** An Ollama server with these models installed; records the paths asked for. */
  function ollamaWith(models: { name: string; family?: string }[], status = 200) {
    const paths: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      paths.push(new URL(url).pathname);
      return new Response(
        JSON.stringify(status === 200 ? { models: models.map((m) => ({ name: m.name, details: { family: m.family ?? "llama" } })) } : { error: "nope" }),
        { status },
      );
    });
    return paths;
  }

  it("takes the first preferred model that is installed", () => {
    const preferred = ["llama3.1:8b", "phi4-mini"];
    expect(chooseOllamaModel(["mistral:7b", "phi4-mini:latest", "llama3.1:8b"], preferred)).toBe("llama3.1:8b");
    expect(chooseOllamaModel(["mistral:7b", "phi4-mini:latest"], preferred)).toBe("phi4-mini:latest");
  });

  it("matches a bare name to the latest tag only, and ignores case", () => {
    expect(chooseOllamaModel(["Phi4-Mini:latest"], ["phi4-mini"])).toBe("Phi4-Mini:latest");
    // A differently tagged build is not the preferred model, so the first installed one is used.
    expect(chooseOllamaModel(["gemma3:4b", "llama3.1:70b"], ["llama3.1:8b"])).toBe("gemma3:4b");
    expect(chooseOllamaModel(["hf.co/org/model:latest"], ["hf.co/org/model"])).toBe("hf.co/org/model:latest");
  });

  it("falls back to whatever is installed, or nothing", () => {
    expect(chooseOllamaModel(["qwen2.5:7b", "gemma3:4b"], ["llama3.1:8b"])).toBe("qwen2.5:7b");
    expect(chooseOllamaModel([], ["llama3.1:8b"])).toBeUndefined();
  });

  it("lists chat models and leaves embedding models out", async () => {
    const paths = ollamaWith([
      { name: "nomic-embed-text:latest", family: "nomic-bert" },
      { name: "all-minilm:latest", family: "bert" },
      { name: "llama3.1:8b" },
    ]);
    expect(await listOllamaModels("https://ollama.example.com/")).toEqual(["llama3.1:8b"]);
    expect(paths).toEqual(["/api/tags"]);
  });

  it("prefers the operator's model, then the best-scoring one, then what is there", async () => {
    ollamaWith([{ name: "phi4-mini:latest" }, { name: "llama3.1:8b" }, { name: "gemma3:4b" }]);
    expect(await resolveOllamaModel("https://o.example.com")).toBe("llama3.1:8b");
    expect(await resolveOllamaModel("https://o.example.com", "gemma3:4b")).toBe("gemma3:4b");
    expect(await resolveOllamaModel("https://o.example.com", "not-installed")).toBe("llama3.1:8b");

    ollamaWith([{ name: "gemma3:4b" }, { name: "phi4-mini:latest" }]);
    expect(await resolveOllamaModel("https://o.example.com")).toBe("phi4-mini:latest");

    ollamaWith([{ name: "gemma3:4b" }]);
    expect(await resolveOllamaModel("https://o.example.com")).toBe("gemma3:4b");
  });

  it("asks by name when the server will not list its models", async () => {
    ollamaWith([], 404);
    expect(await resolveOllamaModel("https://o.example.com")).toBe(OLLAMA_MODEL_PREFERENCE[0]);
    expect(await resolveOllamaModel("https://o.example.com", "mistral:7b")).toBe("mistral:7b");
  });

  it("says so when the server has no chat model at all", async () => {
    ollamaWith([{ name: "nomic-embed-text:latest", family: "nomic-bert" }]);
    const err = await resolveOllamaModel("https://o.example.com").catch((e: Error) => e);
    expect(err).toBeInstanceOf(Error);
    const shown = providerError((err as Error).message);
    expect(shown.status).toBe(400);
    expect(shown.body.reason).toContain("no chat model is installed");
    expect(shown.body.reason).toContain("ollama pull");
  });
});

describe("providerError with Ollama's own error shape", () => {
  it("shows the text Ollama sent, not raw JSON", () => {
    const e = providerError(`ollama_404:{"error":"model 'llama3.1:8b' not found"}`);
    expect(e.status).toBe(400);
    expect(e.body.reason).toBe("Ollama rejected the request: model 'llama3.1:8b' not found");
  });
});
