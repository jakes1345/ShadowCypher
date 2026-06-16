"""
ShadowGuard — AI Input/Output Security Layer (Rampart-AI inspired).
Runs 100% offline. Blocks prompt injection, jailbreaks, and credential leakage.
"""
import re
import os
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable
from shadowcypher.core.logger import logger

ALLOW = "ALLOW"
BLOCK = "BLOCK"
FLAG = "FLAG"
REDACT = "REDACT"

@dataclass
class GuardResult:
    action: str
    original: str
    cleaned: str
    threats: list = field(default_factory=list)
    score: float = 0.0
    latency_ms: float = 0.0

_INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions?", 0.95),
    (r"disregard\s+your\s+(system\s+)?prompt", 0.95),
    (r"forget\s+(everything|all)\s+(you('ve)?\s+)?(been\s+)?told", 0.90),
    (r"you\s+are\s+now\s+a\s+", 0.85),
    (r"act\s+as\s+if\s+you\s+(are|were)", 0.85),
    (r"pretend\s+(you('re|\s+are)|to\s+be)", 0.80),
    (r"new\s+(system\s+)?prompt[\s:]+", 0.90),
    (r"<\s*system\s*>", 0.90),
    (r"DAN\s+(mode|prompt|jailbreak)", 0.95),
    (r"do\s+anything\s+now", 0.90),
    (r"jailbreak", 0.75),
    (r"developer\s+mode\s+enabled", 0.80),
    (r"(reveal|print|repeat|output)\s+(your\s+)?(system\s+)?(prompt|instructions?|context)", 0.85),
    (r"what\s+(are|were)\s+your\s+(original\s+)?instructions?", 0.80),
    (r"\[\s*SYSTEM\s*\]", 0.85),
    (r"\[\s*INST\s*\].*ignore", 0.80),
    (r"base64\s*decode\s*the\s*following", 0.75),
    (r"translate.*to\s+english.*ignore", 0.80),
]
_COMPILED_INJ = [(re.compile(p, re.IGNORECASE | re.DOTALL), s) for p, s in _INJECTION_PATTERNS]

_CRED_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "[OPENAI_KEY_REDACTED]"),
    (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN_REDACTED]"),
    (r"AKIA[0-9A-Z]{16}", "[AWS_KEY_REDACTED]"),
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "[BEARER_TOKEN_REDACTED]"),
    (r"(password|passwd|pwd)\s*[:=]\s*\S+", "[PASSWORD_REDACTED]"),
    (r"(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?\S+['\"]?", "[API_KEY_REDACTED]"),
    (r"-----BEGIN\s+(RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----", "[PRIVATE_KEY_REDACTED]"),
    (r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b", "[INTERNAL_IP_REDACTED]"),
    (r"(/etc/shadowcypher/|\.shadowcypher/vault/|master\.key)", "[SENSITIVE_PATH_REDACTED]"),
]
_COMPILED_CRED = [(re.compile(p, re.IGNORECASE), r) for p, r in _CRED_PATTERNS]


class ShadowGuard:
    """Offline prompt injection detector and output credential sanitizer."""

    def __init__(self):
        self._enabled = True
        self._strict = False
        self._lock = threading.Lock()
        self._stats = {"scanned": 0, "blocked": 0, "flagged": 0, "redacted": 0}
        self._alert_cb: Optional[Callable] = None
        logger.info("guard", "ShadowGuard ONLINE — injection detection active")

    # ── Public ───────────────────────────────────────────────────────────────

    def scan_input(self, text: str, context: str = "prompt") -> GuardResult:
        """Gate: call before sending any input to Ollama."""
        if not self._enabled:
            return GuardResult(ALLOW, text, text)
        t0 = time.perf_counter()
        threats, top = [], 0.0
        for pat, score in _COMPILED_INJ:
            m = pat.search(text)
            if m:
                threats.append({"type": "injection", "score": score, "match": m.group(0)[:80]})
                top = max(top, score)
        action = self._verdict(top)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        with self._lock:
            self._stats["scanned"] += 1
            if action == BLOCK:
                self._stats["blocked"] += 1
            elif action == FLAG:
                self._stats["flagged"] += 1
        r = GuardResult(action, text, text, threats, top, ms)
        if threats:
            msg = f"[GUARD] {action} score={top:.2f} ctx={context} threats={len(threats)}"
            logger.warning("guard", msg)
            if self._alert_cb:
                self._alert_cb(msg, r)
        return r

    def scan_output(self, text: str) -> GuardResult:
        """Gate: call before displaying any AI output to the user."""
        if not self._enabled:
            return GuardResult(ALLOW, text, text)
        t0 = time.perf_counter()
        cleaned, threats = text, []
        for pat, repl in _COMPILED_CRED:
            new, n = pat.subn(repl, cleaned)
            if n:
                cleaned, threats = new, threats + [{"type": "credential", "repl": repl, "n": n}]
        action = REDACT if cleaned != text else ALLOW
        ms = round((time.perf_counter() - t0) * 1000, 2)
        if threats:
            with self._lock:
                self._stats["redacted"] += 1
            logger.warning("guard", f"[GUARD] OUTPUT_SANITIZED redactions={len(threats)}")
        return GuardResult(action, text, cleaned, threats, 0.0, ms)

    def enable(self): self._enabled = True
    logger.info("guard", "ShadowGuard ENABLED")
    def disable(self): self._enabled = False
    logger.warning("guard", "ShadowGuard DISABLED")
    def set_strict(self, v: bool): self._strict = v
    def on_alert(self, cb): self._alert_cb = cb
    def get_stats(self) -> dict:
        with self._lock:
            return dict(self._stats)

    def _verdict(self, score: float) -> str:
        if score >= 0.90:
            return BLOCK
        if score >= 0.70:
            return BLOCK if self._strict else FLAG
        if score >= 0.40:
            return FLAG
        return ALLOW


guard = ShadowGuard()
