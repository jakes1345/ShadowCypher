"""
ShadowCypher Attack Chain Planner — Sakana AI TreeQuest integration.

Uses Monte Carlo Tree Search (via treequest) to explore multi-step
security assessment paths. Instead of blindly running every tool,
the planner asks the local AI to predict the utility of each next
action, searches the space of possible action sequences, and returns
the highest-value path to execute.

This is the "AI Scientist" pattern applied to security:
  Speculate → Evaluate → Execute best path → Analyze

Safety: the planner only suggests actions against explicitly provided
targets. It never autonomously initiates scans — it returns an ordered
action plan that the operator executes (or approves for auto-execution).

Usage:
    from shadowcypher.ai.tree_planner import tree_planner
    plan = tree_planner.plan(target="192.168.1.1", context="web app, port 80 open")
    # → [("nmap_service", 0.92), ("nuclei_scan", 0.87), ("cve_lookup", 0.71)]

    # Auto-execute the plan:
    tree_planner.execute_plan(plan, target="192.168.1.1", on_output=print)
"""

from __future__ import annotations
import re
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field
from shadowcypher.core.logger import logger

# ── Available security actions ────────────────────────────────────────────────

SECURITY_ACTIONS = [
    "port_scan",        # nmap service fingerprint
    "vuln_scan",        # nuclei templates
    "web_scan",         # nikto
    "cve_lookup",       # correlate services against NVD
    "threat_intel",     # OTX + AbuseIPDB + URLhaus
    "subdomain_enum",   # subfinder
    "sql_injection",    # sqlmap
    "osint",            # WHOIS + passive recon
]

# Human-readable descriptions for AI prompt
ACTION_DESCRIPTIONS = {
    "port_scan":      "Nmap service/version scan — discovers open ports and running services",
    "vuln_scan":      "Nuclei template scan — checks for known CVE patterns and misconfigs",
    "web_scan":       "Nikto web vulnerability scanner — checks HTTP endpoints",
    "cve_lookup":     "NVD CVE correlation — matches discovered services against vulnerability DB",
    "threat_intel":   "OTX/AbuseIPDB/URLhaus lookup — checks IP/domain reputation",
    "subdomain_enum": "Subfinder subdomain enumeration — discovers additional attack surface",
    "sql_injection":  "SQLmap injection test — tests web params for SQL injection",
    "osint":          "Passive WHOIS/DNS reconnaissance — no active probing",
}

# Safety gates: actions that should always confirm before running
CONFIRM_BEFORE_RUN = {"sql_injection", "vuln_scan"}


# ── State type ────────────────────────────────────────────────────────────────

@dataclass
class PlanState:
    target: str
    context: str                         # initial context provided by operator
    actions_taken: list[str] = field(default_factory=list)
    findings_summary: str = ""           # accumulated finding text
    estimated_score: float = 0.0         # AI-estimated value of this path

    def path_str(self) -> str:
        return " → ".join(self.actions_taken) if self.actions_taken else "(root)"


# ── Scorer ────────────────────────────────────────────────────────────────────

def _keyword_score(text: str) -> float:
    """Fast heuristic scorer from AI prediction text — no LLM needed for scoring."""
    text_l = text.lower()
    score = 0.0
    # High value keywords
    for kw in ("critical", "rce", "remote code", "cve-20", "exploit", "unauthenticated",
               "injection", "admin", "root", "shell", "kev", "epss"):
        if kw in text_l:
            score += 0.15
    # Medium value
    for kw in ("vulnerability", "open port", "service", "version", "disclosure",
               "misconfiguration", "weak"):
        if kw in text_l:
            score += 0.07
    # Diminishing returns for repeated actions
    return min(score, 1.0)


def _ask_ai_prediction(target: str, action: str, context: str,
                        actions_taken: list[str]) -> tuple[str, float]:
    """
    Ask the local AI to predict what this action would find.
    Returns (prediction_text, utility_score).
    Falls back to keyword heuristics if AI unavailable.
    """
    from shadowcypher.ai.providers import provider_registry

    history_str = ", ".join(actions_taken) if actions_taken else "none yet"
    prompt = (
        f"Security assessment planning. Target: {target}\n"
        f"Context: {context}\n"
        f"Actions already taken: {history_str}\n\n"
        f"Predict the security findings if we next run: {action}\n"
        f"({ACTION_DESCRIPTIONS.get(action, action)})\n\n"
        f"Be specific about what vulnerabilities, CVEs, or misconfigurations this is likely to reveal "
        f"given the target context. If this action would likely find nothing useful given what's already "
        f"known, say so. Keep response under 100 words."
    )
    system = (
        "You are a senior penetration tester predicting scan results. "
        "Be direct and technical. Mention specific CVEs or vulnerability types when likely."
    )
    try:
        prediction = provider_registry.generate(
            prompt, system_prompt=system, max_tokens=150, temperature=0.3
        ) or ""
    except Exception:
        prediction = f"Likely to reveal {action.replace('_', ' ')} findings on {target}"

    score = _keyword_score(prediction)
    # Penalize actions already taken (avoid redundancy)
    if action in actions_taken:
        score *= 0.2
    return prediction, score


# ── TreeQuest planner ─────────────────────────────────────────────────────────

class AttackChainPlanner:
    """
    Uses Sakana AI's TreeQuest MCTS to find the highest-value sequence of
    security assessment actions for a given target.
    """

    def __init__(self, max_depth: int = 4, budget: int = 20,
                 algorithm: str = "mcts"):
        """
        max_depth: max actions in a chain
        budget:    max tree expansions (higher = better quality, slower)
        algorithm: "mcts" | "bfs" | "bestfirst"
        """
        self.max_depth = max_depth
        self.budget    = budget
        self.algorithm = algorithm
        self._lock     = threading.Lock()

    def _make_algo(self):
        try:
            from treequest import StandardMCTS, TreeOfThoughtsBFSAlgo
            if self.algorithm == "bfs":
                return TreeOfThoughtsBFSAlgo()
            return StandardMCTS(samples_per_action=2, exploration_weight=1.414)
        except ImportError:
            logger.warning("tree_planner", "treequest not installed — using greedy fallback")
            return None

    def plan(
        self,
        target: str,
        context: str = "",
        actions: list[str] = None,
        on_progress: Callable = None,
    ) -> list[tuple[str, float]]:
        """
        Plan the optimal sequence of security assessment actions.

        Args:
            target:      IP, hostname, or URL to assess
            context:     Any known context (open ports, services, etc.)
            actions:     Override default action set
            on_progress: Optional streaming callback for progress updates

        Returns:
            List of (action, score) tuples, highest score first.
            Safe to pass directly to execute_plan().
        """
        available = actions or SECURITY_ACTIONS
        algo = self._make_algo()

        if algo is None:
            return self._greedy_plan(target, context, available, on_progress)

        if on_progress:
            on_progress(f"[PLAN] TreeQuest MCTS planning attack chain for {target} "
                        f"(budget={self.budget}, depth={self.max_depth})...\n")

        try:
            from treequest import top_k

            # generate_fn: given (action, parent_state) → (new_state, score)
            def _generate(action: str, parent_state: Optional[PlanState]) -> tuple[PlanState, float]:
                if parent_state is None:
                    parent_state = PlanState(target=target, context=context)
                if len(parent_state.actions_taken) >= self.max_depth:
                    return parent_state, 0.0
                prediction, score = _ask_ai_prediction(
                    target, action, context, parent_state.actions_taken
                )
                if on_progress:
                    on_progress(f"[PLAN] {parent_state.path_str()} → {action}  score={score:.2f}\n")
                new_state = PlanState(
                    target=target,
                    context=context,
                    actions_taken=parent_state.actions_taken + [action],
                    findings_summary=parent_state.findings_summary + f"\n{action}: {prediction[:200]}",
                    estimated_score=score,
                )
                return new_state, score

            # Build generate_fn mapping: one function per action
            generate_fns = {action: lambda s, a=action: _generate(a, s) for action in available}

            # Run tree search
            state = algo.init_tree()
            for step in range(self.budget):
                state, trial = algo.ask(state, actions=available)
                parent_state: Optional[PlanState] = trial.parent_state
                new_state, score = _generate(trial.action, parent_state)
                state = algo.tell(state, trial.trial_id, (new_state, score))

            # Extract top results
            results = top_k(state, algo, k=min(5, len(available)))
            plan = []
            seen = set()
            for node_state, score in results:
                if node_state and node_state.actions_taken:
                    last_action = node_state.actions_taken[-1]
                    if last_action not in seen:
                        plan.append((last_action, score))
                        seen.add(last_action)

            if on_progress:
                on_progress(f"[PLAN] Best path: {' → '.join(a for a, _ in plan)}\n")

            return plan or self._greedy_plan(target, context, available, on_progress)

        except Exception as e:
            logger.warning("tree_planner", f"TreeQuest planning failed: {e} — using greedy")
            return self._greedy_plan(target, context, available, on_progress)

    def _greedy_plan(self, target: str, context: str, available: list[str],
                     on_progress: Callable = None) -> list[tuple[str, float]]:
        """Fallback: score each action independently, return sorted list."""
        if on_progress:
            on_progress("[PLAN] Using greedy scorer (treequest unavailable)\n")
        scored = []
        for action in available:
            _, score = _ask_ai_prediction(target, action, context, [])
            scored.append((action, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def execute_plan(
        self,
        plan: list[tuple[str, float]],
        target: str,
        on_output: Callable = None,
        confirm_fn: Callable = None,
        max_actions: int = 4,
    ) -> dict[str, str]:
        """
        Execute the top actions from a plan.

        Args:
            plan:        Output of plan() — [(action, score), ...]
            target:      Target to run actions against
            on_output:   Streaming output callback
            confirm_fn:  Optional callable(action, target) → bool for dangerous actions.
                         If None, dangerous actions (sql_injection, vuln_scan) are SKIPPED.
            max_actions: Maximum actions to run (default 4)

        Returns:
            dict mapping action → raw output string
        """
        from shadowcypher.ai.intent import TOOL_REGISTRY, _register_tools
        _register_tools()

        results: dict[str, str] = {}

        for action, score in plan[:max_actions]:
            # Safety gate
            if action in CONFIRM_BEFORE_RUN:
                if confirm_fn is None:
                    if on_output:
                        on_output(f"[PLAN] Skipping {action} — requires explicit confirmation\n")
                    continue
                if not confirm_fn(action, target):
                    if on_output:
                        on_output(f"[PLAN] Operator declined {action}\n")
                    continue

            # Map action → intent type
            intent_type = {
                "port_scan":      "nmap_scan",
                "vuln_scan":      "nuclei_scan",
                "web_scan":       "nikto_scan",
                "sql_injection":  "sqlmap_scan",
                "subdomain_enum": "subdomain_enum",
                "threat_intel":   "ip_reputation",
                "osint":          "whois_lookup",
            }.get(action, action)

            fn = TOOL_REGISTRY.get(intent_type)
            if not fn:
                if on_output:
                    on_output(f"[PLAN] Tool not available: {action}\n")
                continue

            output_lines: list[str] = []

            def _collect(line: str, _lines=output_lines):
                _lines.append(line)
                if on_output:
                    on_output(line)

            if on_output:
                on_output(f"\n[PLAN] Executing: {action} on {target}  (score={score:.2f})\n")
            try:
                fn(target, _collect)
                results[action] = "".join(output_lines)
            except Exception as e:
                results[action] = f"[ERROR] {e}"
                if on_output:
                    on_output(f"[PLAN] {action} failed: {e}\n")

        return results

    def plan_and_execute(
        self,
        target: str,
        context: str = "",
        on_output: Callable = None,
        confirm_fn: Callable = None,
        max_actions: int = 4,
    ) -> tuple[list[tuple[str, float]], dict[str, str], str]:
        """
        Full pipeline: plan → execute → assess.

        Returns:
            (plan, execution_results, assessment_text)
        """
        plan = self.plan(target, context, on_progress=on_output)

        if on_output:
            on_output(f"\n[PLAN] Executing top {max_actions} actions...\n")

        results = self.execute_plan(
            plan, target,
            on_output=on_output,
            confirm_fn=confirm_fn,
            max_actions=max_actions,
        )

        # Assess findings
        assessment = ""
        try:
            from shadowcypher.core.assessor import assessor
            # Collect CVE matches from cve_feed if a port scan was run
            cve_matches = []
            if "port_scan" in results or "cve_lookup" in results:
                try:
                    from shadowcypher.modules.cve_feed import cve_feed
                    # Extract service banners from port scan output
                    scan_output = results.get("port_scan", results.get("cve_lookup", ""))
                    services = re.findall(r"(\w[\w\s\-\.]+?)\s+([\d]+\.[\d]+[\.\d]*)", scan_output)
                    if services:
                        banners = [f"{s[0].strip()} {s[1]}" for s in services[:10]]
                        cve_matches = cve_feed.correlate_target(target, services=banners, on_output=on_output)
                except Exception:
                    pass

            # Collect threat intel if that was run
            ti_results = []
            if "threat_intel" in results:
                try:
                    from shadowcypher.modules.threat_intel import threat_intel
                    ti_result = threat_intel.lookup_ip(target)
                    ti_results = [ti_result]
                except Exception:
                    pass

            assessment = assessor.assess_findings(
                cve_matches=cve_matches,
                threat_results=ti_results,
                target=target,
            )
            if on_output and assessment:
                on_output(f"\n{'='*60}\n{assessment}\n{'='*60}\n")
        except Exception as e:
            logger.warning("tree_planner", f"Assessment failed: {e}")

        return plan, results, assessment


# Global singleton
tree_planner = AttackChainPlanner(max_depth=4, budget=16, algorithm="mcts")
