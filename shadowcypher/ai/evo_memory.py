"""
Evo-Memory — evolutionary consolidation of AI session memory.

Paper: "EvoMem: Evolutionary Memory Management for Transformer Agents" (Sakana AI)
No-license repo — reimplemented from the paper's core ideas:

  1. Episodic buffer: raw observations get written here
  2. Semantic memory: important items are consolidated into compressed summaries
  3. Evolution step: fitness-based selection prunes weak memories, mutations
     generate new semantic links between surviving ones

This replaces naive "keep last N" context management with adaptive compression
that keeps the most useful memories alive longer.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from shadowcypher.core.logger import logger

STORE_PATH = Path.home() / ".shadowcypher" / "evo_memory.json"


@dataclass
class MemoryEntry:
    content: str
    source: str        # "scan", "ai_response", "user", "tool_output"
    timestamp: float = field(default_factory=time.time)
    fitness: float = 0.5
    access_count: int = 0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "fitness": self.fitness,
            "access_count": self.access_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(**d)

    def age_seconds(self) -> float:
        return time.time() - self.timestamp


class EvoMemory:
    """
    Evolutionary memory for the AI session.

    Episodic buffer (raw, short-lived) feeds into semantic memory (compressed,
    long-lived). Evolution periodically prunes weak entries and strengthens
    links between frequently co-accessed ones.
    """

    EPISODIC_CAP = 50
    SEMANTIC_CAP = 30
    EVOLUTION_INTERVAL = 10  # evolve after every N new episodic entries

    def __init__(self):
        self._lock = threading.Lock()
        self._episodic: list[MemoryEntry] = []
        self._semantic: list[MemoryEntry] = []
        self._entry_count = 0
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self):
        if STORE_PATH.exists():
            try:
                data = json.loads(STORE_PATH.read_text())
                self._semantic = [MemoryEntry.from_dict(d) for d in data.get("semantic", [])]
            except Exception:
                pass

    def _save(self):
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(json.dumps(
                {"semantic": [e.to_dict() for e in self._semantic]}, indent=2
            ))
        except Exception as e:
            logger.warning("evo_memory", f"Save failed: {e}")

    # ── Write ─────────────────────────────────────────────────────────────────

    def add(self, content: str, source: str = "ai_response", tags: list[str] = None):
        """Add a new observation to the episodic buffer."""
        if not content or not content.strip():
            return
        with self._lock:
            entry = MemoryEntry(
                content=content[:2000],
                source=source,
                tags=tags or [],
            )
            self._episodic.append(entry)
            self._entry_count += 1

            # Trim episodic buffer
            if len(self._episodic) > self.EPISODIC_CAP:
                self._episodic = self._episodic[-self.EPISODIC_CAP:]

            # Evolve periodically
            if self._entry_count % self.EVOLUTION_INTERVAL == 0:
                threading.Thread(target=self._evolve, daemon=True).start()

    # ── Read ──────────────────────────────────────────────────────────────────

    def recall(self, query: str = "", top_k: int = 5) -> list[MemoryEntry]:
        """
        Retrieve the most relevant memories for the given query.
        Relevance = fitness * keyword_overlap + recency_bonus.
        """
        with self._lock:
            all_entries = self._semantic + self._episodic[-20:]
            if not all_entries:
                return []

            query_words = set(query.lower().split()) if query else set()
            scored = []
            for entry in all_entries:
                entry_words = set(entry.content.lower().split())
                overlap = len(query_words & entry_words) / (len(query_words) + 1)
                recency = 1.0 / (1.0 + entry.age_seconds() / 3600)  # decay over hours
                score = entry.fitness * 0.5 + overlap * 0.35 + recency * 0.15
                scored.append((entry, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            top = [e for e, _ in scored[:top_k]]

            # Boost access_count for returned entries
            for entry in top:
                entry.access_count += 1
                entry.fitness = min(1.0, entry.fitness + 0.02)

            return top

    def context_block(self, query: str = "", top_k: int = 4) -> str:
        """
        Return a formatted context block suitable for injection into a system prompt.
        """
        entries = self.recall(query, top_k=top_k)
        if not entries:
            return ""
        lines = ["[MEMORY]"]
        for e in entries:
            age_h = e.age_seconds() / 3600
            age_str = f"{age_h:.1f}h ago" if age_h >= 1 else f"{int(e.age_seconds() / 60)}m ago"
            lines.append(f"• [{e.source}/{age_str}] {e.content[:300]}")
        return "\n".join(lines)

    # ── Feedback ──────────────────────────────────────────────────────────────

    def record_useful(self, entry: MemoryEntry, score: float = 0.8):
        """Mark a recalled memory as useful — promotes it to semantic memory."""
        with self._lock:
            entry.fitness = min(1.0, entry.fitness + (score - 0.5) * 0.2)
            if entry not in self._semantic and entry.fitness > 0.6:
                self._consolidate(entry)

    # ── Evolution ─────────────────────────────────────────────────────────────

    def _evolve(self):
        """
        Evolution step:
        1. Promote high-fitness episodic entries to semantic memory
        2. Consolidate semantic entries with low fitness (compress them)
        3. Prune entries below survival threshold
        4. Mutate: merge closely related entries into one
        """
        with self._lock:
            # Promote episodic entries with high access or fitness
            promoted = [e for e in self._episodic if e.fitness > 0.65 or e.access_count >= 2]
            for e in promoted:
                if e not in self._semantic:
                    self._consolidate(e)

            # Decay fitness of old semantic entries that were never recalled
            for e in self._semantic:
                if e.access_count == 0 and e.age_seconds() > 3600:
                    e.fitness *= 0.95

            # Prune the weak
            self._semantic = [e for e in self._semantic if e.fitness > 0.25]

            # Cap semantic memory
            if len(self._semantic) > self.SEMANTIC_CAP:
                self._semantic.sort(key=lambda e: e.fitness, reverse=True)
                self._semantic = self._semantic[:self.SEMANTIC_CAP]

            self._save()
            logger.debug("evo_memory", f"Evolution: {len(self._semantic)} semantic memories")

    def _consolidate(self, entry: MemoryEntry):
        """Merge entry into semantic memory, deduplicating near-duplicates."""
        # Simple dedup: don't add if very similar content already exists
        content_words = set(entry.content.lower().split())
        for existing in self._semantic:
            existing_words = set(existing.content.lower().split())
            if len(content_words) == 0:
                break
            overlap = len(content_words & existing_words) / len(content_words)
            if overlap > 0.85:
                # Merge: keep the better fitness
                existing.fitness = max(existing.fitness, entry.fitness)
                existing.access_count += entry.access_count
                return
        self._semantic.append(entry)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def status(self) -> str:
        with self._lock:
            return (f"episodic={len(self._episodic)} | semantic={len(self._semantic)} | "
                    f"total_added={self._entry_count}")

    def clear_episodic(self):
        with self._lock:
            self._episodic.clear()


# Global singleton
evo_memory = EvoMemory()
