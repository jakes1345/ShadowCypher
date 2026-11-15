/// <reference types="node" />
/**
 * Scores local models on the question set, through the product's own prompt.
 *
 *   EVAL_MODELS=llama3.1:8b,phi4-mini npm run eval
 *
 * Each question is sent exactly as the hosted assistant would send it in
 * security mode: the same system prompt, the same network summary, the same
 * Ollama call. Temperature and seed are pinned so a run can be repeated.
 *
 *   EVAL_MODELS       comma-separated Ollama model names (required)
 *   EVAL_OLLAMA_URL   Ollama base URL (default http://127.0.0.1:11434)
 *   EVAL_OUT          folder for the result files (default: a folder in the system temp directory)
 *   EVAL_MAX_TOKENS   cap on answer length; defaults to what the product sends
 *   EVAL_ONLY         run only one category, or only ids starting with this text
 *
 * After a grading rule is corrected, the answers already collected can be marked
 * again without asking the models a second time:
 *
 *   EVAL_REGRADE=1 EVAL_OUT=<folder with the result files> npm run eval
 */
import { describe, it, expect } from "vitest";
import { mkdirSync, writeFileSync, appendFileSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildSystemPrompt, composeUserMessage, networkDataPart, queryOllama } from "../assistant";
import { grade, type Check } from "./grade";
import { QUESTIONS, type Category } from "./questions";
import { SCENARIOS } from "./scenarios";

const models = (process.env.EVAL_MODELS ?? "").split(",").map((m) => m.trim()).filter(Boolean);
const baseUrl = process.env.EVAL_OLLAMA_URL ?? "http://127.0.0.1:11434";
const outDir = process.env.EVAL_OUT ?? join(tmpdir(), "shadowcypher-eval");
const maxTokens = process.env.EVAL_MAX_TOKENS ? Number(process.env.EVAL_MAX_TOKENS) : undefined;
const only = process.env.EVAL_ONLY;
const regrade = Boolean(process.env.EVAL_REGRADE);

interface Result {
  id: string;
  category: Category;
  question: string;
  answer: string;
  seconds: number;
  score: number;
  pass: boolean;
  checks: Check[];
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
const slug = (model: string) => model.replace(/[^a-zA-Z0-9._-]+/g, "_");

function summarise(model: string, results: Result[]) {
  const categories = [...new Set(results.map((r) => r.category))].sort();
  const failedChecks: Record<string, number> = {};
  for (const r of results) for (const c of r.checks) if (!c.pass) {
    const name = c.name.startsWith("must_") && c.name !== "must_not" ? "missing_required_fact" : c.name;
    failedChecks[name] = (failedChecks[name] ?? 0) + 1;
  }
  const times = results.map((r) => r.seconds).sort((a, b) => a - b);
  return {
    model,
    questions: results.length,
    score: mean(results.map((r) => r.score)),
    passRate: mean(results.map((r) => (r.pass ? 1 : 0))),
    byCategory: Object.fromEntries(categories.map((c) => {
      const rs = results.filter((r) => r.category === c);
      return [c, { questions: rs.length, score: mean(rs.map((r) => r.score)), passRate: mean(rs.map((r) => (r.pass ? 1 : 0))) }];
    })),
    failedChecks,
    medianSeconds: times[Math.floor(times.length / 2)] ?? 0,
    totalMinutes: times.reduce((a, b) => a + b, 0) / 60,
  };
}

function report(summary: ReturnType<typeof summarise>, file: string) {
  console.log(`\n${summary.model}: score ${pct(summary.score)}, fully correct ${pct(summary.passRate)} of ${summary.questions}, median ${summary.medianSeconds.toFixed(1)}s per answer`);
  for (const [c, v] of Object.entries(summary.byCategory)) {
    console.log(`  ${c.padEnd(10)} score ${pct(v.score).padStart(6)}   fully correct ${pct(v.passRate).padStart(6)}   (${v.questions} questions)`);
  }
  console.log(`  failed checks: ${JSON.stringify(summary.failedChecks)}`);
  console.log(`  answers and checks: ${file}`);
}

describe.skipIf(!regrade)("mark saved answers again", () => {
  it("applies the current rules to every result file", () => {
    const byId = new Map(QUESTIONS.map((q) => [q.id, q]));
    const files = readdirSync(outDir).filter((f) => f.endsWith(".json"));
    expect(files.length).toBeGreaterThan(0);

    for (const name of files) {
      const file = join(outDir, name);
      const saved = JSON.parse(readFileSync(file, "utf8")) as { summary: { model: string }; results: Result[] };
      const results = saved.results.map((r) => {
        const q = byId.get(r.id);
        if (!q) throw new Error(`${name}: question ${r.id} is no longer in the set`);
        const s = SCENARIOS[q.scenario];
        const g = grade(r.answer, q, networkDataPart(s.devices, s.incidents, s.scans));
        return { ...r, category: q.category, question: q.question, score: g.score, pass: g.pass, checks: g.checks };
      });
      const summary = summarise(saved.summary.model, results);
      writeFileSync(file, JSON.stringify({ ...saved, regradedAt: new Date().toISOString(), summary, results }, null, 2));
      report(summary, file);
    }
  });
});

describe.skipIf(models.length === 0 || regrade)("assistant evaluation", () => {
  // Grouped by scenario so the model server can reuse the shared start of each prompt.
  const selected = QUESTIONS
    .filter((q) => !only || q.category === only || q.id.startsWith(only))
    .sort((a, b) => a.scenario.localeCompare(b.scenario));
  const system = buildSystemPrompt("security", false, new Date());
  mkdirSync(outDir, { recursive: true });

  it.each(models)("%s", async (model) => {
    const progress = join(outDir, `${slug(model)}.progress.log`);
    writeFileSync(progress, `${new Date().toISOString()} start ${model}: ${selected.length} questions\n`);
    const results: Result[] = [];

    for (const [i, q] of selected.entries()) {
      const s = SCENARIOS[q.scenario];
      const data = networkDataPart(s.devices, s.incidents, s.scans);
      const started = Date.now();
      const { answer } = await queryOllama(
        baseUrl,
        [{ role: "user", content: composeUserMessage([data], q.question) }],
        system,
        model,
        { temperature: 0, seed: 7, ...(maxTokens ? { num_predict: maxTokens } : {}) },
      );
      const seconds = (Date.now() - started) / 1000;
      const g = grade(answer, q, data);
      results.push({ id: q.id, category: q.category, question: q.question, answer, seconds, score: g.score, pass: g.pass, checks: g.checks });
      appendFileSync(progress, `${i + 1}/${selected.length} ${q.id} ${g.pass ? "pass" : "FAIL"} ${seconds.toFixed(1)}s\n`);
    }

    const summary = summarise(model, results);
    const file = join(outDir, `${slug(model)}.json`);
    writeFileSync(file, JSON.stringify({ ranAt: new Date().toISOString(), baseUrl, maxTokens: maxTokens ?? 600, summary, results }, null, 2));
    report(summary, file);

    expect(results).toHaveLength(selected.length);
  });
});
