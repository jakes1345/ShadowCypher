/**
 * Scoring for the assistant evaluation.
 *
 * Every answer is checked against rules written per question (facts it must
 * contain, claims it must not make) and three rules that apply to every
 * answer because the product's own instructions demand them: no invented
 * addresses, at most a few sentences, no markdown.
 *
 * The rules are text patterns, so they are strict about substance and blind to
 * style: a correct answer phrased in a way no pattern anticipated is marked
 * down. Each question therefore carries a reference answer that must pass and
 * a wrong answer that must fail, checked in __tests__/evals.test.ts, and the
 * runner keeps every answer so a low score can be read, not just counted.
 */

export interface Rubric {
  /** Every group must match. A group matches when any one of its patterns does. */
  must: string[][];
  /** No pattern here may match. */
  mustNot: string[];
  /** Set where an example address is a fair part of a good answer, such as a subnet to scan. */
  allowExampleAddresses?: boolean;
}

export interface Check {
  name: string;
  pass: boolean;
  /** What tripped the check, when it failed. */
  detail?: string;
}

export interface Grade {
  checks: Check[];
  /** Share of checks passed, 0 to 1. */
  score: number;
  /** True when every check passed. */
  pass: boolean;
}

/** The product asks for 1 to 3 sentences. One more is tolerated before an answer counts as too long. */
export const MAX_SENTENCES = 4;

const IPV4 = /\b(?:\d{1,3}\.){3}\d{1,3}\b/g;
const MAC = /\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b/gi;

function isPrivate(ip: string): boolean {
  const [a, b] = ip.split(".").map(Number);
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}

/**
 * Private IP and MAC addresses in the answer that are not in the data the
 * model was given. Public addresses are left alone: naming 1.1.1.1 as a
 * resolver is general knowledge, not a claim about the user's network.
 */
export function inventedAddresses(answer: string, promptData: string): string[] {
  const known = promptData.toLowerCase();
  const found = [
    ...(answer.match(IPV4) ?? []).filter(isPrivate),
    ...(answer.match(MAC) ?? []),
  ];
  return [...new Set(found)].filter((addr) => !known.includes(addr.toLowerCase()));
}

export function countSentences(answer: string): number {
  return answer
    .trim()
    .split(/(?<=[.!?])["')\]]?\s+(?=["'(\[]?[A-Z0-9])/)
    .filter((s) => s.trim().length > 0).length;
}

const MARKDOWN: [string, RegExp][] = [
  ["bold or italic markers", /\*\*|__|(?<![\w*])\*(?!\s)[^*\n]+\*(?![\w*])/],
  ["a header", /^\s{0,3}#{1,6}\s/m],
  ["a bullet list", /^\s*[-*•]\s+\S/m],
  ["a numbered list", /^\s*\d+[.)]\s+\S/m],
  ["a code span or block", /`/],
];

export function markdownFound(answer: string): string | null {
  for (const [label, re] of MARKDOWN) if (re.test(answer)) return label;
  return null;
}

export function grade(answer: string, rubric: Rubric, promptData: string): Grade {
  const checks: Check[] = [];

  rubric.must.forEach((group, i) => {
    const hit = group.some((p) => new RegExp(p, "i").test(answer));
    checks.push({ name: `must_${i + 1}`, pass: hit, detail: hit ? undefined : `none of: ${group.join(" | ")}` });
  });

  const forbidden = rubric.mustNot.find((p) => new RegExp(p, "i").test(answer));
  checks.push({ name: "must_not", pass: !forbidden, detail: forbidden ? `matched: ${forbidden}` : undefined });

  const invented = rubric.allowExampleAddresses ? [] : inventedAddresses(answer, promptData);
  checks.push({
    name: "no_invented_addresses",
    pass: invented.length === 0,
    detail: invented.length ? `not in the data: ${invented.join(", ")}` : undefined,
  });

  const sentences = countSentences(answer);
  checks.push({
    name: "length",
    pass: sentences >= 1 && sentences <= MAX_SENTENCES,
    detail: sentences > MAX_SENTENCES ? `${sentences} sentences` : undefined,
  });

  const md = markdownFound(answer);
  checks.push({ name: "no_markdown", pass: !md, detail: md ? `contains ${md}` : undefined });

  const passed = checks.filter((c) => c.pass).length;
  return { checks, score: passed / checks.length, pass: passed === checks.length };
}
