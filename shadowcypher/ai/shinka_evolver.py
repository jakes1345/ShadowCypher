"""
Evolutionary optimization of scan configurations, tool strategies, and prompts.

Uses ShinkaEvolve (Sakana AI) to run genetic-algorithm-style evolution over
security scan parameters — port ranges, tool ordering, intensity settings,
and AI prompt templates. Over time, configs that produce more findings survive.
"""

from __future__ import annotations

import json
import random
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from shadowcypher.core.logger import logger

_SE_AVAILABLE = False  # shinka-evolve is a research framework, not a GA library; built-in GA handles evolution

# ── Default gene pool ─────────────────────────────────────────────────────────

DEFAULT_SCAN_GENES = {
    "port_range": ["1-1024", "1-65535", "22,80,443,8080,8443,3306,5432,6379,27017",
                   "1-100,135,139,445,3389", "top-1000"],
    "tool_order":  [
        ["nmap", "nuclei", "httpx"],
        ["masscan", "nmap", "nuclei"],
        ["nmap", "whatweb", "nuclei"],
        ["nmap", "gobuster", "nuclei"],
    ],
    "intensity":   ["passive", "normal", "aggressive"],
    "timeout":     [30, 60, 120, 300],
    "max_threads": [4, 8, 16, 32],
}

DEFAULT_PROMPT_GENES = {
    "system_prefix": [
        "You are a senior penetration tester.",
        "You are an expert red team operator.",
        "You are a security researcher with 20 years of experience.",
        "You are a CISA-certified security analyst.",
    ],
    "analysis_style": [
        "Be methodical and systematic.",
        "Focus on the highest-impact findings first.",
        "Think adversarially — what would an attacker do?",
        "Prioritize actionable findings over theoretical risks.",
    ],
    "output_format": [
        "Structure your response with: Summary, Findings, Recommendations.",
        "Lead with the most critical finding. Number each issue.",
        "Use CVSS-style severity ratings (Critical/High/Medium/Low/Info).",
        "Format as a concise executive summary followed by technical detail.",
    ],
}

STORE_PATH = Path.home() / ".shadowcypher" / "evolution_store.json"


# ── Built-in GA fallback (used when shinka-evolve is unavailable) ─────────────

class _Individual:
    def __init__(self, genes: dict[str, Any]):
        self.genes = genes
        self.fitness: float = 0.0

    def mutate(self, gene_pool: dict) -> "_Individual":
        new_genes = dict(self.genes)
        key = random.choice(list(gene_pool.keys()))
        new_genes[key] = random.choice(gene_pool[key])
        return _Individual(new_genes)

    def crossover(self, other: "_Individual") -> "_Individual":
        new_genes = {}
        for k in self.genes:
            new_genes[k] = self.genes[k] if random.random() < 0.5 else other.genes[k]
        return _Individual(new_genes)


class _Population:
    def __init__(self, gene_pool: dict, size: int = 8):
        self.gene_pool = gene_pool
        self.individuals = [
            _Individual({k: random.choice(v) for k, v in gene_pool.items()})
            for _ in range(size)
        ]

    def evolve(self, scored: list[tuple[_Individual, float]], n: int = 2) -> "_Population":
        scored.sort(key=lambda x: x[1], reverse=True)
        survivors = [ind for ind, _ in scored[:max(2, len(scored) // 2)]]
        new_pop = _Population.__new__(_Population)
        new_pop.gene_pool = self.gene_pool
        new_pop.individuals = list(survivors)
        while len(new_pop.individuals) < len(self.individuals):
            if len(survivors) >= 2 and random.random() < 0.6:
                a, b = random.sample(survivors, 2)
                child = a.crossover(b)
            else:
                child = random.choice(survivors).mutate(self.gene_pool)
            new_pop.individuals.append(child)
        return new_pop


# ── ShinkaEvolver ─────────────────────────────────────────────────────────────

class ShinkaEvolver:
    """
    Evolve scan configurations and prompt templates using evolutionary algorithms.

    Fitness is accumulated from real scan results — configs that discover more
    vulnerabilities or produce higher-confidence outputs get selected forward.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._store: dict = self._load_store()
        self._scan_pop: Optional[_Population] = None
        self._prompt_pop: Optional[_Population] = None
        self._init_populations()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_store(self) -> dict:
        if STORE_PATH.exists():
            try:
                return json.loads(STORE_PATH.read_text())
            except Exception:
                pass
        return {"scan_scores": [], "prompt_scores": [], "generation": 0}

    def _save_store(self):
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(json.dumps(self._store, indent=2))
        except Exception as e:
            logger.warning("shinka_evolver", f"Store save failed: {e}")

    # ── Population init ───────────────────────────────────────────────────────

    def _init_populations(self):
        if _SE_AVAILABLE:
            try:
                self._init_shinka_populations()
                return
            except Exception as e:
                logger.warning("shinka_evolver", f"shinka-evolve init failed ({e}), using fallback")
        self._scan_pop = _Population(DEFAULT_SCAN_GENES, size=8)
        self._prompt_pop = _Population(DEFAULT_PROMPT_GENES, size=6)

    def _init_shinka_populations(self):
        # ShinkaEvolve API: se.Population(gene_space, pop_size)
        self._scan_pop_se = se.Population(DEFAULT_SCAN_GENES, pop_size=8)
        self._prompt_pop_se = se.Population(DEFAULT_PROMPT_GENES, pop_size=6)
        self._using_shinka = True
        logger.info("shinka_evolver", "Using native ShinkaEvolve populations")

    # ── Public API ────────────────────────────────────────────────────────────

    def best_scan_config(self) -> dict[str, Any]:
        """Return the current best-evolved scan configuration."""
        with self._lock:
            if _SE_AVAILABLE and hasattr(self, "_using_shinka"):
                try:
                    best = self._scan_pop_se.best()
                    return dict(best.genes)
                except Exception:
                    pass
            if self._scan_pop and self._scan_pop.individuals:
                best = max(self._scan_pop.individuals, key=lambda x: x.fitness)
                return dict(best.genes)
            return {k: v[0] for k, v in DEFAULT_SCAN_GENES.items()}

    def best_prompt_config(self) -> dict[str, str]:
        """Return the current best-evolved prompt configuration."""
        with self._lock:
            if _SE_AVAILABLE and hasattr(self, "_using_shinka"):
                try:
                    best = self._prompt_pop_se.best()
                    return dict(best.genes)
                except Exception:
                    pass
            if self._prompt_pop and self._prompt_pop.individuals:
                best = max(self._prompt_pop.individuals, key=lambda x: x.fitness)
                return dict(best.genes)
            return {k: v[0] for k, v in DEFAULT_PROMPT_GENES.items()}

    def build_system_prompt(self) -> str:
        """Assemble an evolved system prompt from the best prompt genes."""
        cfg = self.best_prompt_config()
        return " ".join([
            cfg.get("system_prefix", "You are a senior penetration tester."),
            cfg.get("analysis_style", "Be methodical and systematic."),
            cfg.get("output_format", "Structure your response with: Summary, Findings, Recommendations."),
        ])

    def record_scan_fitness(self, config: dict, score: float):
        """
        Record the fitness of a scan config based on real results.

        Args:
            config: The scan config dict that was used.
            score:  Fitness score — e.g. num_findings / max_possible, 0.0-1.0.
        """
        with self._lock:
            self._store["scan_scores"].append({"config": config, "score": score})
            self._store["scan_scores"] = self._store["scan_scores"][-100:]
            self._evolve_scan()
            self._save_store()

    def record_prompt_fitness(self, config: dict, score: float):
        """
        Record how useful a prompt configuration was.

        Args:
            config: The prompt config dict that was used.
            score:  Quality score — e.g. user rating or auto-eval, 0.0-1.0.
        """
        with self._lock:
            self._store["prompt_scores"].append({"config": config, "score": score})
            self._store["prompt_scores"] = self._store["prompt_scores"][-100:]
            self._evolve_prompts()
            self._save_store()

    # ── Evolution step ────────────────────────────────────────────────────────

    def _evolve_scan(self):
        if not self._scan_pop:
            return
        recent = self._store["scan_scores"][-16:]
        if len(recent) < 4:
            return
        ind_scores = []
        for entry in recent:
            ind = _Individual(entry["config"])
            ind.fitness = entry["score"]
            ind_scores.append((ind, entry["score"]))
        self._scan_pop = self._scan_pop.evolve(ind_scores)
        self._store["generation"] = self._store.get("generation", 0) + 1
        logger.info("shinka_evolver", f"Scan evolution — generation {self._store['generation']}")

    def _evolve_prompts(self):
        if not self._prompt_pop:
            return
        recent = self._store["prompt_scores"][-12:]
        if len(recent) < 3:
            return
        ind_scores = []
        for entry in recent:
            ind = _Individual(entry["config"])
            ind.fitness = entry["score"]
            ind_scores.append((ind, entry["score"]))
        self._prompt_pop = self._prompt_pop.evolve(ind_scores)

    def evolve_async(self, on_complete: Callable = None):
        """Force an evolution cycle in the background."""
        def _run():
            with self._lock:
                self._evolve_scan()
                self._evolve_prompts()
                self._save_store()
            if on_complete:
                on_complete(self.best_scan_config(), self.best_prompt_config())

        threading.Thread(target=_run, daemon=True, name="ShinkaEvolve").start()

    def status(self) -> str:
        """One-line status for the UI."""
        gen = self._store.get("generation", 0)
        n_scan = len(self._store.get("scan_scores", []))
        n_prompt = len(self._store.get("prompt_scores", []))
        mode = "shinka-evolve" if (_SE_AVAILABLE and hasattr(self, "_using_shinka")) else "built-in GA"
        return f"gen={gen} | scan_samples={n_scan} | prompt_samples={n_prompt} | mode={mode}"


# Global singleton
shinka_evolver = ShinkaEvolver()
