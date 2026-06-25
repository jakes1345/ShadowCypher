"""
Tree-search reasoning engine — AB-MCTS over LLM reasoning paths.

For complex security queries, instead of one linear AI call, we run AB-MCTS
to explore multiple reasoning branches and pick the best one. Each node in the
tree is a reasoning step; the LLM scores how promising each branch looks.

Usage:
    from shadowcypher.ai.tree_reasoner import tree_reasoner
    result = tree_reasoner.reason("pentest 192.168.1.100", budget=12, on_output=print)
"""

from __future__ import annotations

import re
import threading
from typing import Callable, Optional

from shadowcypher.core.logger import logger

try:
    import treequest as tq
    _TQ_AVAILABLE = True
except ImportError:
    _TQ_AVAILABLE = False
    logger.warning("tree_reasoner", "treequest not installed — tree search disabled")

# ── Reasoning actions ─────────────────────────────────────────────────────────
# Each action is a reasoning lens the AI applies at each tree step.

ACTIONS = {
    "enumerate":  "Enumerate the attack surface. What services, endpoints, or entry points are present or implied?",
    "analyze":    "Analyze the current findings. What patterns, misconfigs, or vulnerabilities stand out?",
    "exploit":    "Reason about exploitation. What technique would be most effective and why?",
    "lateral":    "Think about post-exploitation. What lateral movement or privilege escalation is possible?",
    "report":     "Synthesize all findings into a structured assessment. Threat level, key findings, recommended actions.",
}

SCORE_PROMPT = """Rate how useful and accurate this security reasoning is for answering the original question.
Consider: specificity, actionability, technical correctness, and relevance.
Respond with ONLY a decimal number between 0.0 and 1.0. No other text.

Original question: {query}

Reasoning so far:
{state}

Score (0.0-1.0):"""

STEP_PROMPT = """You are a senior security analyst. Continue this security assessment with a focus on: {action_desc}

Original question: {query}

Reasoning so far:
{state}

Continue the analysis (2-4 sentences, specific and technical):"""


class TreeReasoner:
    """
    AB-MCTS over LLM reasoning paths. Each node is a reasoning step;
    the tree explores different analytical directions and picks the best path.
    """

    def __init__(self):
        self._lock = threading.Lock()

    def _call_llm(self, prompt: str, max_tokens: int = 300) -> str:
        """Single LLM call via the active provider."""
        try:
            from shadowcypher.ai.providers import provider_registry
            return provider_registry.generate(
                prompt,
                system_prompt="You are a senior security analyst. Be concise, technical, and specific.",
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as e:
            logger.warning("tree_reasoner", f"LLM call failed: {e}")
            return ""

    def _score(self, state: str, query: str) -> float:
        """Ask the LLM to rate the quality of a reasoning path (0.0–1.0)."""
        prompt = SCORE_PROMPT.format(query=query, state=state[-1500:])
        raw = self._call_llm(prompt, max_tokens=10).strip()
        m = re.search(r"([01]?\.\d+|\d+)", raw)
        if m:
            val = float(m.group(1))
            return min(1.0, max(0.0, val))
        return 0.5  # neutral if LLM gives garbage

    def _make_generate(self, query: str, action_name: str, on_output: Callable = None):
        """Return a generate(parent_state) → (state, score) function for one action."""
        action_desc = ACTIONS[action_name]

        def generate(parent_state: Optional[str]) -> tuple[str, float]:
            state = parent_state or f"Target/query: {query}"
            prompt = STEP_PROMPT.format(
                action_desc=action_desc,
                query=query,
                state=state[-2000:],
            )
            step = self._call_llm(prompt, max_tokens=350)
            if not step:
                return state, 0.0
            new_state = f"{state}\n\n[{action_name.upper()}]\n{step.strip()}"
            score = self._score(new_state, query)
            if on_output:
                on_output(f"[TREE/{action_name}] score={score:.2f} — {step[:120].strip()}...\n")
            return new_state, score

        return generate

    def reason(
        self,
        query: str,
        budget: int = 16,
        on_output: Callable = None,
        actions: list[str] = None,
    ) -> str:
        """
        Run AB-MCTS over reasoning paths for a security query.

        Args:
            query:     The security question or task.
            budget:    Number of tree expansions (more = better but slower).
            on_output: Streaming callback for progress lines.
            actions:   Which reasoning actions to use (default: all 5).

        Returns:
            The best reasoning path found.
        """
        if not _TQ_AVAILABLE:
            logger.warning("tree_reasoner", "treequest not available, falling back to direct LLM")
            return self._fallback(query, on_output)

        active_actions = actions or list(ACTIONS.keys())

        if on_output:
            on_output(f"[TREE] AB-MCTS search — budget={budget}, actions={active_actions}\n")

        algo = tq.ABMCTSA()
        search_tree = algo.init_tree()

        generate_fns = {
            action: self._make_generate(query, action, on_output)
            for action in active_actions
        }

        for i in range(budget):
            search_tree = algo.step(search_tree, generate_fns)
            if on_output and i % 4 == 3:
                try:
                    best_state, best_score = tq.top_k(search_tree, algo, k=1)[0]
                    on_output(f"[TREE] step {i+1}/{budget} — best score so far: {best_score:.2f}\n")
                except Exception:
                    pass

        try:
            best_state, best_score = tq.top_k(search_tree, algo, k=1)[0]
            if on_output:
                on_output(f"\n[TREE] Search complete. Best path score: {best_score:.2f}\n")
                on_output("─" * 60 + "\n")
            return best_state
        except Exception as e:
            logger.error("tree_reasoner", f"top_k failed: {e}")
            return self._fallback(query, on_output)

    def _fallback(self, query: str, on_output: Callable = None) -> str:
        """Direct LLM call when treequest is unavailable."""
        if on_output:
            on_output("[TREE] treequest unavailable — direct LLM call\n")
        return self._call_llm(
            f"You are a senior security analyst. Answer thoroughly:\n\n{query}",
            max_tokens=800,
        )

    def reason_async(
        self,
        query: str,
        on_output: Callable = None,
        on_complete: Callable = None,
        budget: int = 16,
        actions: list[str] = None,
    ):
        """Non-blocking tree search. Calls on_complete(result) when done."""
        def _worker():
            result = self.reason(query, budget=budget, on_output=on_output, actions=actions)
            if on_complete:
                on_complete(result)

        t = threading.Thread(target=_worker, daemon=True, name="TreeReasoner")
        t.start()
        return t


# Global singleton
tree_reasoner = TreeReasoner()
