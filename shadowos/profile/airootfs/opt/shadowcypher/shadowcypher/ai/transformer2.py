"""
Transformer² — self-adaptive task inference via expert mixing.

Sakana AI paper: "Self-Adaptive Large Language Models using Evolutionary Strategies"
Paper implementation (application-level approximation):
  - Maintain named "expert configurations" per task type (the ΔW approximation)
  - First-pass classifier identifies task type from the query
  - Mix expert configs to produce the best system prompt + parameters
  - Fitness-track which expert mixes produce best outcomes

The paper does weight-space mixing; we do prompt-space mixing. Same principle,
no model modification needed.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from shadowcypher.core.logger import logger

# ── Expert definitions ────────────────────────────────────────────────────────
# Each expert is a named configuration tuned for a specific security task type.

EXPERTS: dict[str, dict[str, Any]] = {
    "recon": {
        "system": "You are a reconnaissance specialist. Focus on enumeration, service identification, and attack surface mapping. Be comprehensive and systematic.",
        "temperature": 0.3,
        "max_tokens": 600,
        "keywords": ["scan", "enumerate", "recon", "discover", "fingerprint", "nmap", "masscan", "port", "service"],
    },
    "exploit": {
        "system": "You are an exploitation expert. Focus on vulnerability identification, CVE analysis, and exploitation pathways. Reason step by step through attack chains.",
        "temperature": 0.5,
        "max_tokens": 800,
        "keywords": ["exploit", "vulnerability", "cve", "payload", "rce", "sqli", "xss", "overflow", "injection", "bypass"],
    },
    "forensics": {
        "system": "You are a digital forensics analyst. Focus on evidence preservation, artifact analysis, timeline reconstruction, and attribution indicators.",
        "temperature": 0.2,
        "max_tokens": 700,
        "keywords": ["forensic", "artifact", "log", "timeline", "ioc", "indicator", "evidence", "malware", "memory"],
    },
    "osint": {
        "system": "You are an OSINT investigator. Focus on passive reconnaissance, open-source intelligence, data correlation, and intelligence synthesis.",
        "temperature": 0.4,
        "max_tokens": 700,
        "keywords": ["osint", "domain", "whois", "email", "social", "linkedin", "wayback", "dns", "certificate"],
    },
    "web": {
        "system": "You are a web application security expert. Focus on OWASP Top 10, API security, authentication flaws, and web-specific attack vectors.",
        "temperature": 0.4,
        "max_tokens": 700,
        "keywords": ["web", "http", "api", "jwt", "cookie", "csrf", "cors", "header", "burp", "waf"],
    },
    "network": {
        "system": "You are a network security engineer. Focus on protocol analysis, firewall bypass, lateral movement, and network architecture weaknesses.",
        "temperature": 0.4,
        "max_tokens": 700,
        "keywords": ["network", "firewall", "vpn", "vlan", "switch", "router", "bgp", "arp", "mitm", "pivot"],
    },
    "report": {
        "system": "You are a senior security consultant writing for executive and technical audiences. Structure findings clearly with severity ratings, business impact, and actionable remediation steps.",
        "temperature": 0.2,
        "max_tokens": 1200,
        "keywords": ["report", "summary", "findings", "remediation", "risk", "compliance", "audit", "assessment"],
    },
    "general": {
        "system": "You are a senior security researcher with broad expertise across offensive and defensive security.",
        "temperature": 0.5,
        "max_tokens": 600,
        "keywords": [],
    },
}

STORE_PATH = Path.home() / ".shadowcypher" / "t2_fitness.json"

# ── Transformer² ──────────────────────────────────────────────────────────────

class Transformer2:
    """
    Self-adaptive LLM routing via expert mixing.

    Classifies each query into one or more expert types, then mixes their
    configurations (prompt + temperature) to produce optimal inference params.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._fitness: dict[str, list[float]] = self._load_fitness()

    def _load_fitness(self) -> dict[str, list[float]]:
        if STORE_PATH.exists():
            try:
                return json.loads(STORE_PATH.read_text())
            except Exception:
                pass
        return {k: [0.5] for k in EXPERTS}

    def _save_fitness(self):
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(json.dumps(self._fitness, indent=2))
        except Exception as e:
            logger.warning("transformer2", f"Fitness save failed: {e}")

    def _classify(self, query: str) -> dict[str, float]:
        """Score each expert by keyword overlap with the query."""
        q = query.lower()
        scores: dict[str, float] = {}
        for name, cfg in EXPERTS.items():
            if name == "general":
                continue
            kws = cfg["keywords"]
            if not kws:
                scores[name] = 0.0
                continue
            hits = sum(1 for kw in kws if kw in q)
            scores[name] = hits / len(kws)

        # Weight by historical fitness
        for name in list(scores.keys()):
            hist = self._fitness.get(name, [0.5])
            avg_fitness = sum(hist[-10:]) / len(hist[-10:])
            scores[name] = scores[name] * 0.7 + avg_fitness * 0.3

        # If no keyword hits, fall back to general
        if max(scores.values(), default=0) < 0.05:
            scores["general"] = 1.0
        else:
            scores["general"] = 0.0

        return scores

    def adapt(self, query: str, top_k: int = 2) -> dict[str, Any]:
        """
        Produce an adapted inference configuration for the given query.

        Returns dict with: system_prompt, temperature, max_tokens, experts_used.
        """
        with self._lock:
            scores = self._classify(query)

        # Pick top-k experts
        sorted_experts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected = [(name, score) for name, score in sorted_experts[:top_k] if score > 0.01]
        if not selected:
            selected = [("general", 1.0)]

        # Normalize weights
        total = sum(s for _, s in selected)
        weights = [(name, s / total) for name, s in selected]

        # Mix configurations
        system_parts = []
        temperature = 0.0
        max_tokens = 0
        for name, w in weights:
            cfg = EXPERTS[name]
            if cfg["system"] not in system_parts:
                system_parts.append(cfg["system"])
            temperature += cfg["temperature"] * w
            max_tokens += cfg["max_tokens"] * w

        system_prompt = " ".join(system_parts) if len(system_parts) > 1 else system_parts[0]

        return {
            "system_prompt": system_prompt,
            "temperature": round(temperature, 2),
            "max_tokens": int(max_tokens),
            "experts_used": [name for name, _ in weights],
        }

    def record_feedback(self, experts_used: list[str], score: float):
        """Record outcome quality for the experts that were used."""
        with self._lock:
            for expert in experts_used:
                if expert not in self._fitness:
                    self._fitness[expert] = []
                self._fitness[expert].append(score)
                self._fitness[expert] = self._fitness[expert][-50:]
            self._save_fitness()

    def expert_report(self) -> str:
        """One-line expert fitness summary."""
        lines = []
        for name, scores in self._fitness.items():
            avg = sum(scores[-10:]) / len(scores[-10:]) if scores else 0.5
            lines.append(f"{name}={avg:.2f}")
        return " | ".join(lines)


# Global singleton
transformer2 = Transformer2()
