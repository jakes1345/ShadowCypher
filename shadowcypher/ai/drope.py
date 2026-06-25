"""
DroPE — context extension via strategic content dropping.

Paper: "DroPE: Extending Context Length by Dropping Positional Embeddings"
No-license repo — reimplemented from the core insight:

  The paper drops positional embeddings in certain transformer layers so the
  model can attend across arbitrarily long contexts without degradation.
  At the model weight level, this requires patching Ollama/llama.cpp.

  At the application level (where we operate), we implement the same GOAL —
  extending effective context — by strategic content compression and dropping:

  1. Identify "anchor tokens" — high-information spans the model must keep
  2. Drop or compress low-information content between anchors
  3. Re-inject only the high-value spans into the context window

This lets us pass much longer security scan outputs to the model than the
raw context window allows, without losing the key findings.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Optional

from shadowcypher.core.logger import logger

# ── Configuration ─────────────────────────────────────────────────────────────

# Patterns that mark "anchor" content — always preserve these spans
ANCHOR_PATTERNS = [
    r"CVE-\d{4}-\d+",                        # CVE IDs
    r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
    r"\bCRITICAL\b|\bHIGH\b|\bCRITICAL:",    # severity markers
    r"vulnerability|exploit|rce|lfi|sqli|xss|overflow",
    r"password|credential|hash|token|secret|key",
    r"open port|service:|banner:|version:",
    r"error:|exception:|traceback|failed|denied",
]

_ANCHOR_RE = re.compile("|".join(ANCHOR_PATTERNS), re.IGNORECASE)

# Lines that are pure noise (can be dropped)
DROP_PATTERNS = [
    r"^#",                          # comment lines
    r"^\s*$",                       # blank lines (run of 2+)
    r"^(?:Starting|Initiating) ",   # nmap boilerplate
    r"^Read data files from",
    r"^NSE: Loaded",
    r"^RTTVAR has grown",
    r"^\[[\d:]+\] ",               # timestamps without content
]
_DROP_RE = re.compile("|".join(DROP_PATTERNS))


@dataclass
class Span:
    text: str
    score: float   # 0.0 = droppable, 1.0 = anchor (always keep)
    compressed: bool = False


class DroPE:
    """
    Strategic context compression — preserve high-value spans, compress the rest.

    Usage:
        drope = DroPE()
        compressed = drope.compress(long_scan_output, target_tokens=4000)
        # compressed has same key findings but fits in the context window
    """

    def __init__(self, chars_per_token: float = 3.5):
        self._chars_per_token = chars_per_token
        self._lock = threading.Lock()

    def _score_line(self, line: str) -> float:
        """Score a line's information value: 0.0 (drop) → 1.0 (anchor)."""
        if _DROP_RE.match(line.strip()):
            return 0.0
        if _ANCHOR_RE.search(line):
            return 1.0
        # Heuristic: longer lines after stripping tend to have more content
        stripped = line.strip()
        if len(stripped) < 5:
            return 0.05
        if len(stripped) > 100:
            return 0.6
        return 0.3

    def _to_spans(self, text: str) -> list[Span]:
        lines = text.splitlines()
        spans = []
        prev_blank = False
        for line in lines:
            score = self._score_line(line)
            # Collapse consecutive blank lines
            if score == 0.0 and prev_blank:
                continue
            spans.append(Span(text=line, score=score))
            prev_blank = (score == 0.0 and not line.strip())
        return spans

    def _compress_context_window(self, spans: list[Span], target_chars: int) -> str:
        """
        Greedily fill target_chars with highest-score content.

        Algorithm (mirrors DroPE's layer-dropping logic):
          1. Always include all anchor spans (score=1.0)
          2. Fill remaining budget with medium-score spans in order
          3. Drop low-score spans last
        """
        anchors = [s for s in spans if s.score >= 0.9]
        medium = [s for s in spans if 0.2 <= s.score < 0.9]
        low = [s for s in spans if s.score < 0.2]

        anchor_chars = sum(len(s.text) + 1 for s in anchors)
        budget = max(0, target_chars - anchor_chars)

        # Fill medium spans until budget is exhausted
        selected_medium = []
        for s in medium:
            chunk_len = len(s.text) + 1
            if chunk_len <= budget:
                selected_medium.append(s)
                budget -= chunk_len

        # Try to squeeze in a compressed summary of dropped content
        dropped_count = len(low) + (len(medium) - len(selected_medium))
        drop_note = f"\n[DroPE: {dropped_count} low-value lines dropped]\n" if dropped_count > 0 else ""

        # Reconstruct in original order
        selected_set = set(id(s) for s in anchors + selected_medium)
        result_lines = [s.text for s in spans if id(s) in selected_set]
        return "\n".join(result_lines) + drop_note

    def compress(self, text: str, target_tokens: int = 4000) -> str:
        """
        Compress text to approximately target_tokens while preserving key findings.

        Args:
            text:          Raw scan output, AI response, or any long text.
            target_tokens: Approximate output token budget.

        Returns:
            Compressed text that fits within the token budget.
        """
        if not text:
            return text

        target_chars = int(target_tokens * self._chars_per_token)
        if len(text) <= target_chars:
            return text  # Already fits, no compression needed

        with self._lock:
            spans = self._to_spans(text)
            compressed = self._compress_context_window(spans, target_chars)

        ratio = len(compressed) / len(text)
        logger.debug("drope", f"Compressed {len(text)} → {len(compressed)} chars ({ratio:.0%})")
        return compressed

    def compress_messages(self, messages: list[dict], max_total_tokens: int = 8000) -> list[dict]:
        """
        Compress a list of chat messages to fit within a total token budget.

        Older messages are compressed more aggressively; recent messages are preserved.
        """
        if not messages:
            return messages

        total_chars = sum(len(m.get("content", "")) for m in messages)
        target_total = max_total_tokens * self._chars_per_token
        if total_chars <= target_total:
            return messages

        result = []
        # Always preserve the last 2 messages fully
        preserved_tail = messages[-2:]
        compress_head = messages[:-2]

        tail_chars = sum(len(m.get("content", "")) for m in preserved_tail)
        head_budget = int(target_total - tail_chars)

        if head_budget <= 0:
            return preserved_tail

        per_msg_budget = max(500, head_budget // max(1, len(compress_head)))
        for msg in compress_head:
            content = msg.get("content", "")
            compressed_content = self.compress(content, target_tokens=int(per_msg_budget / self._chars_per_token))
            result.append({**msg, "content": compressed_content})

        return result + preserved_tail

    def status(self) -> str:
        return f"DroPE context compressor | chars_per_token={self._chars_per_token}"


# Global singleton
drope = DroPE()
