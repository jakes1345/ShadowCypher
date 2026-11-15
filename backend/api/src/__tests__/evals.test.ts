import { describe, it, expect } from "vitest";
import { buildSystemPrompt, composeUserMessage, networkDataPart } from "../assistant";
import { countSentences, grade, inventedAddresses, markdownFound, MAX_SENTENCES } from "../evals/grade";
import { QUESTIONS } from "../evals/questions";
import { SCENARIOS } from "../evals/scenarios";

const dataFor = (id: keyof typeof SCENARIOS) => {
  const s = SCENARIOS[id];
  return networkDataPart(s.devices, s.incidents, s.scans);
};

describe("evaluation set", () => {
  it("has between 50 and 100 questions with unique ids", () => {
    expect(QUESTIONS.length).toBeGreaterThanOrEqual(50);
    expect(QUESTIONS.length).toBeLessThanOrEqual(100);
    expect(new Set(QUESTIONS.map((q) => q.id)).size).toBe(QUESTIONS.length);
  });

  it("covers every category and uses every scenario", () => {
    const perCategory: Record<string, number> = {};
    for (const q of QUESTIONS) perCategory[q.category] = (perCategory[q.category] ?? 0) + 1;
    for (const c of ["grounding", "advice", "knowledge", "honesty", "safety"]) {
      expect(perCategory[c] ?? 0, c).toBeGreaterThanOrEqual(5);
    }
    expect(new Set(QUESTIONS.map((q) => q.scenario))).toEqual(new Set(Object.keys(SCENARIOS)));
  });

  it("only uses patterns that compile, and every question has at least one rule", () => {
    for (const q of QUESTIONS) {
      expect(q.must.length, q.id).toBeGreaterThan(0);
      for (const p of [...q.must.flat(), ...q.mustNot]) expect(() => new RegExp(p, "i"), `${q.id}: ${p}`).not.toThrow();
    }
  });

  it("asks through the same prompt the product sends", () => {
    const s = SCENARIOS.new_device;
    const message = composeUserMessage([networkDataPart(s.devices, s.incidents, s.scans)], "What just joined my network?");
    expect(message).toContain("My network data:");
    expect(message).toContain("  - 192.168.1.87 | type=unknown | ports=[]");
    expect(message).toContain("[INFO] new_device: New device on network: 192.168.1.87");
    expect(message.endsWith("My question: What just joined my network?")).toBe(true);
    expect(buildSystemPrompt("security", false, new Date())).toContain("Never invent device names, IPs, or incidents");
  });

  // The rules are only worth anything if they can tell a good answer from a bad one.
  describe.each(QUESTIONS)("$id", (q) => {
    it("passes its reference answer on every check", () => {
      const g = grade(q.reference, q, dataFor(q.scenario));
      expect(g.checks.filter((c) => !c.pass), q.reference).toEqual([]);
    });

    it("fails its wrong answer on substance, not on format", () => {
      const g = grade(q.wrong, q, dataFor(q.scenario));
      const substance = g.checks.filter((c) => c.name.startsWith("must") || c.name === "no_invented_addresses");
      expect(substance.some((c) => !c.pass), q.wrong).toBe(true);
    });

    it("keeps its reference inside the length the product asks for", () => {
      expect(countSentences(q.reference)).toBeLessThanOrEqual(3);
    });
  });
});

describe("invented addresses", () => {
  const data = "  - 192.168.1.87 | type=unknown\n  - desk-pc | type=pc";

  it("flags a private address that is not in the data", () => {
    expect(inventedAddresses("The laptop is at 192.168.1.20.", data)).toEqual(["192.168.1.20"]);
    expect(inventedAddresses("Check 10.0.0.5 and 172.16.4.4.", data)).toEqual(["10.0.0.5", "172.16.4.4"]);
  });

  it("accepts an address that is in the data", () => {
    expect(inventedAddresses("The device at 192.168.1.87 is new.", data)).toEqual([]);
  });

  it("leaves public addresses alone", () => {
    expect(inventedAddresses("Use 1.1.1.1 or 9.9.9.9 as your resolver.", data)).toEqual([]);
    expect(inventedAddresses("172.32.0.1 is not a private address.", data)).toEqual([]);
  });

  it("flags an invented MAC address", () => {
    expect(inventedAddresses("Its MAC is AA:BB:CC:11:22:33.", data)).toEqual(["AA:BB:CC:11:22:33"]);
  });
});

describe("format checks", () => {
  it("counts sentences without being fooled by addresses, versions or ports", () => {
    expect(countSentences("One sentence only.")).toBe(1);
    expect(countSentences("The device at 192.168.1.87 is new. Block it on the router.")).toBe(2);
    expect(countSentences("Ports 23, 53 and 80 are open. Close 23 first! Is that clear?")).toBe(3);
    expect(countSentences("Update to version 2.17.1 of Log4j.")).toBe(1);
  });

  it("fails an answer that runs past the limit", () => {
    const long = Array.from({ length: MAX_SENTENCES + 1 }, (_, i) => `Sentence number ${i + 1} is here.`).join(" ");
    const g = grade(long, { must: [["sentence"]], mustNot: [] }, "");
    expect(g.checks.find((c) => c.name === "length")?.pass).toBe(false);
  });

  it("detects markdown and leaves plain speech alone", () => {
    expect(markdownFound("Turn off **telnet** now.")).toBe("bold or italic markers");
    expect(markdownFound("Do this:\n- turn off telnet\n- update firmware")).toBe("a bullet list");
    expect(markdownFound("Steps:\n1. Log in\n2. Disable WPS")).toBe("a numbered list");
    expect(markdownFound("## Summary\nAll fine.")).toBe("a header");
    expect(markdownFound("Run `nmap` on it.")).toBe("a code span or block");
    expect(markdownFound("Turn off telnet, then use the HTTPS admin page - it is safer.")).toBeNull();
    expect(markdownFound("A 5 * 3 grid has 15 cells.")).toBeNull();
  });
});
