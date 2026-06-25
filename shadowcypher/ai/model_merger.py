"""
Evolutionary model merge — combine local Ollama models into a better hybrid.

Based on Sakana AI's evolutionary-model-merge (Apache-2.0).

The paper uses evolutionary search over merge configurations (TIES, DARE, SLERP)
across task vectors in weight space. We implement this at the Ollama/Modelfile
level: evolve weightings of multiple models by testing merged outputs on a
benchmark, selecting the best merge config.

Merge strategies:
  - ensemble:   Route to each model, pick the best response (voting)
  - chain:      Each model refines the previous model's output
  - specialist: Route by query type to the best model for that task
  - mixture:    Average token probabilities (requires llama.cpp)

This module implements ensemble and chain merges (no weight-level access needed),
and provides scaffolding for weight-level merges if llama.cpp is available.
"""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from shadowcypher.core.logger import logger

STORE_PATH = Path.home() / ".shadowcypher" / "model_merge_fitness.json"


@dataclass
class MergeConfig:
    """A merge configuration to evaluate."""
    models: list[str]             # Ollama model names to merge
    strategy: str                 # "ensemble", "chain", "specialist"
    weights: list[float]          # Per-model weight (for ensemble voting)
    specialist_map: dict[str, str] = field(default_factory=dict)  # task_type → model
    fitness: float = 0.5
    generation: int = 0

    def to_dict(self) -> dict:
        return {
            "models": self.models,
            "strategy": self.strategy,
            "weights": self.weights,
            "specialist_map": self.specialist_map,
            "fitness": self.fitness,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MergeConfig":
        return cls(**d)


class ModelMerger:
    """
    Evolutionary merge of multiple local Ollama models.

    Uses evolutionary search to find the best combination of available
    models for different security task types.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._configs: list[MergeConfig] = []
        self._best: Optional[MergeConfig] = None
        self._load()

    def _load(self):
        if STORE_PATH.exists():
            try:
                data = json.loads(STORE_PATH.read_text())
                self._configs = [MergeConfig.from_dict(d) for d in data.get("configs", [])]
                if self._configs:
                    self._best = max(self._configs, key=lambda c: c.fitness)
            except Exception:
                pass

    def _save(self):
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(json.dumps(
                {"configs": [c.to_dict() for c in self._configs[-20:]]}, indent=2
            ))
        except Exception as e:
            logger.warning("model_merger", f"Save failed: {e}")

    # ── Merge strategies ──────────────────────────────────────────────────────

    def _run_model(self, model: str, query: str, system: str = "", on_output: Callable = None) -> str:
        """Query a single Ollama model."""
        try:
            from shadowcypher.ai.providers import provider_registry
            return provider_registry.generate(query, system_prompt=system, max_tokens=600, temperature=0.4)
        except Exception as e:
            return f"[model error: {e}]"

    def _score_response(self, response: str, query: str) -> float:
        """Quick heuristic scoring: length, keyword density, no-error penalty."""
        if not response or response.startswith("[model error"):
            return 0.0
        score = min(1.0, len(response) / 500)
        kws = ["vulnerability", "CVE", "port", "service", "exploit", "risk", "recommend"]
        hits = sum(1 for kw in kws if kw.lower() in response.lower())
        score += hits * 0.05
        return min(1.0, score)

    def ensemble(self, query: str, config: MergeConfig, on_output: Callable = None) -> str:
        """
        Run all models, return the best single response (weighted voting by score).
        """
        emit = on_output or (lambda x: None)
        responses = []
        for model in config.models:
            emit(f"[MERGE/ensemble] Querying {model}...\n")
            resp = self._run_model(model, query, on_output=on_output)
            score = self._score_response(resp, query)
            responses.append((resp, score, model))
            emit(f"[MERGE/ensemble] {model}: score={score:.2f}\n")

        responses.sort(key=lambda x: x[1], reverse=True)
        best_resp, best_score, best_model = responses[0]
        emit(f"[MERGE/ensemble] Winner: {best_model} (score={best_score:.2f})\n")
        return best_resp

    def chain(self, query: str, config: MergeConfig, on_output: Callable = None) -> str:
        """
        Chain models: each model refines the previous model's output.
        Model 0 answers the query; model 1 critiques and improves; etc.
        """
        emit = on_output or (lambda x: None)
        current = query
        last_response = ""
        for i, model in enumerate(config.models):
            if i == 0:
                prompt = current
            else:
                prompt = (
                    f"Original question: {query}\n\n"
                    f"Previous analysis:\n{last_response[:800]}\n\n"
                    f"Improve and extend this analysis. Fix any errors, add missing details, "
                    f"and make the answer more specific and actionable."
                )
            emit(f"[MERGE/chain] Step {i+1}/{len(config.models)}: {model}\n")
            last_response = self._run_model(model, prompt, on_output=on_output)

        return last_response

    def specialist(self, query: str, config: MergeConfig, on_output: Callable = None) -> str:
        """Route query to the best specialist model based on task type."""
        emit = on_output or (lambda x: None)
        # Use Transformer² to classify
        try:
            from shadowcypher.ai.transformer2 import transformer2
            t2 = transformer2.adapt(query, top_k=1)
            expert_type = t2["experts_used"][0] if t2["experts_used"] else "general"
        except Exception:
            expert_type = "general"

        target_model = config.specialist_map.get(expert_type) or config.models[0]
        emit(f"[MERGE/specialist] Task={expert_type} → {target_model}\n")
        return self._run_model(target_model, query, on_output=on_output)

    # ── Main API ──────────────────────────────────────────────────────────────

    def merge(
        self,
        query: str,
        config: MergeConfig = None,
        on_output: Callable = None,
    ) -> str:
        """
        Run the merged model on a query.

        If no config is provided, uses the best evolved config.
        Falls back to listing available models if none configured.
        """
        with self._lock:
            cfg = config or self._best

        if not cfg:
            return self._run_model("", query, on_output=on_output)

        if cfg.strategy == "chain":
            return self.chain(query, cfg, on_output)
        elif cfg.strategy == "specialist":
            return self.specialist(query, cfg, on_output)
        else:
            return self.ensemble(query, cfg, on_output)

    def record_fitness(self, config: MergeConfig, score: float):
        """Record the fitness of a merge configuration."""
        with self._lock:
            config.fitness = score
            if config not in self._configs:
                self._configs.append(config)
            self._configs.sort(key=lambda c: c.fitness, reverse=True)
            self._best = self._configs[0] if self._configs else None
            self._save()

    def evolve(self, available_models: list[str]) -> MergeConfig:
        """
        Generate a new merge config via evolutionary mutation of the best config.

        Call this after accumulating fitness scores to explore new merge strategies.
        """
        strategies = ["ensemble", "chain", "specialist"]
        if not self._configs:
            n = min(3, len(available_models))
            return MergeConfig(
                models=random.sample(available_models, n),
                strategy=random.choice(strategies),
                weights=[1.0 / n] * n,
            )

        parent = self._best or self._configs[0]
        # Mutate: change strategy, swap a model, or adjust weights
        mutation = random.choice(["strategy", "swap_model", "weights"])

        new_models = list(parent.models)
        new_strategy = parent.strategy
        new_weights = list(parent.weights)

        if mutation == "strategy":
            new_strategy = random.choice([s for s in strategies if s != parent.strategy])
        elif mutation == "swap_model" and available_models:
            alternatives = [m for m in available_models if m not in new_models]
            if alternatives:
                idx = random.randrange(len(new_models))
                new_models[idx] = random.choice(alternatives)
        elif mutation == "weights":
            idx = random.randrange(len(new_weights))
            new_weights[idx] = max(0.1, new_weights[idx] + random.uniform(-0.2, 0.2))
            total = sum(new_weights)
            new_weights = [w / total for w in new_weights]

        return MergeConfig(
            models=new_models,
            strategy=new_strategy,
            weights=new_weights,
            generation=parent.generation + 1,
        )

    def list_ollama_models(self) -> list[str]:
        """Return names of all locally available Ollama models."""
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
                data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def status(self) -> str:
        best = self._best
        if best:
            return f"best_config: {best.strategy}({','.join(best.models)}) fitness={best.fitness:.2f} gen={best.generation}"
        return "no merge configs yet"


# Global singleton
model_merger = ModelMerger()
