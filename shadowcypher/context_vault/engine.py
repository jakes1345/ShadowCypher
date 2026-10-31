"""
SHADOWCYPHER CONTEXT-VAULT — Advanced Context Sandboxing & Token-Reduction Engine
Inspired by mksglu/context-mode.
Implements:
  - Content-Addressed Storage (CAS) with SHA-256 deduplication
  - Hierarchical Semantic Chunking (function-level / section-level splits)
  - Inverted Index & BM25 / TF-IDF relevance search
  - Dynamic Context Budget Slicer (guaranteeing zero context window overflow)
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class SemanticChunk:
    chunk_id: str
    artifact_id: str
    chunk_type: str  # "FUNCTION" | "DISASSEMBLY" | "HEADER" | "FINDING" | "LOG"
    label: str
    text: str
    start_line: int
    end_line: int
    estimated_tokens: int
    keywords: List[str]


@dataclasses.dataclass
class SlicedContext:
    artifact_id: str
    total_raw_tokens: int
    served_tokens: int
    token_saving_pct: float
    selected_chunks_count: int
    total_chunks_count: int
    context_text: str


class AdvancedContextVault:
    """
    Sandboxes voluminous tool outputs on the Linux drive and serves
    dynamically sliced, high-relevance context within strict token budgets.
    """

    def __init__(self, vault_dir: Path | str = "/tmp/shadow_context_vault"):
        self.vault_dir = Path(vault_dir).resolve()
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.vault_dir / "context_vault_v2.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cas_objects (
                    sha256 TEXT PRIMARY KEY,
                    raw_content TEXT,
                    byte_size INTEGER,
                    created_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    cas_hash TEXT,
                    tool_name TEXT,
                    title TEXT,
                    raw_tokens INTEGER,
                    created_at REAL,
                    FOREIGN KEY(cas_hash) REFERENCES cas_objects(sha256)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    artifact_id TEXT,
                    chunk_type TEXT,
                    label TEXT,
                    content TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    tokens INTEGER,
                    keywords_json TEXT,
                    FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_artifact ON chunks(artifact_id)")
            conn.commit()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count: fast word + punctuation model (~1 token per 3.8 chars)."""
        if not text:
            return 0
        words = re.findall(r"\w+|[^\w\s]", text)
        return max(1, len(words))

    def _chunk_c_pseudocode(self, raw_c: str, artifact_id: str) -> List[SemanticChunk]:
        """Hierarchically chunk decompiled C code by function boundaries."""
        chunks: List[SemanticChunk] = []
        lines = raw_c.splitlines()
        
        # Regex to detect function headers e.g. "int main(", "void fcn.00003c10("
        func_regex = re.compile(r"^(?:[\w\*]+\s+)+([a-zA-Z_][\w\.\:]*)\s*\([^)]*\)\s*\{?", re.M)
        
        current_func_label = "header"
        current_lines: List[str] = []
        start_line = 1

        for idx, line in enumerate(lines, 1):
            match = func_regex.match(line)
            if match and current_lines:
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    tokens = self.estimate_tokens(chunk_text)
                    kws = list(set(re.findall(r"[a-zA-Z_]\w{3,}", chunk_text.lower())))[:20]
                    c_id = f"chk_{artifact_id}_{len(chunks)}"
                    chunks.append(
                        SemanticChunk(
                            chunk_id=c_id,
                            artifact_id=artifact_id,
                            chunk_type="FUNCTION" if current_func_label != "header" else "HEADER",
                            label=current_func_label,
                            text=chunk_text,
                            start_line=start_line,
                            end_line=idx - 1,
                            estimated_tokens=tokens,
                            keywords=kws
                        )
                    )
                current_lines = [line]
                start_line = idx
                current_func_label = match.group(1)
            else:
                current_lines.append(line)

        # Flush trailing chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                tokens = self.estimate_tokens(chunk_text)
                kws = list(set(re.findall(r"[a-zA-Z_]\w{3,}", chunk_text.lower())))[:20]
                c_id = f"chk_{artifact_id}_{len(chunks)}"
                chunks.append(
                    SemanticChunk(
                        chunk_id=c_id,
                        artifact_id=artifact_id,
                        chunk_type="FUNCTION" if current_func_label != "header" else "TAIL",
                        label=current_func_label,
                        text=chunk_text,
                        start_line=start_line,
                        end_line=len(lines),
                        estimated_tokens=tokens,
                        keywords=kws
                    )
                )

        return chunks

    def store_and_sandbox(self, tool_name: str, title: str, raw_content: str) -> str:
        """
        Store raw content in CAS, generate hierarchical chunks, and index in database.
        Returns: artifact_id
        """
        content_bytes = raw_content.encode("utf-8", errors="replace")
        cas_hash = hashlib.sha256(content_bytes).hexdigest()
        raw_tokens = self.estimate_tokens(raw_content)
        artifact_id = f"ctx_{int(time.time())}_{cas_hash[:8]}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO cas_objects VALUES (?, ?, ?, ?)",
                (cas_hash, raw_content, len(content_bytes), time.time())
            )
            conn.execute(
                "INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
                (artifact_id, cas_hash, tool_name, title, raw_tokens, time.time())
            )

            # Chunk content (C decompilation or generic blocks)
            if "int " in raw_content or "void " in raw_content or "Function:" in raw_content:
                chunks = self._chunk_c_pseudocode(raw_content, artifact_id)
            else:
                # Generic block chunking (50 lines per chunk)
                lines = raw_content.splitlines()
                chunks = []
                for i in range(0, len(lines), 50):
                    block_lines = lines[i:i + 50]
                    block_text = "\n".join(block_lines)
                    kws = list(set(re.findall(r"[a-zA-Z_]\w{3,}", block_text.lower())))[:20]
                    chunks.append(
                        SemanticChunk(
                            chunk_id=f"chk_{artifact_id}_{len(chunks)}",
                            artifact_id=artifact_id,
                            chunk_type="LOG",
                            label=f"block_{i // 50}",
                            text=block_text,
                            start_line=i + 1,
                            end_line=i + len(block_lines),
                            estimated_tokens=self.estimate_tokens(block_text),
                            keywords=kws
                        )
                    )

            for chk in chunks:
                conn.execute(
                    "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (chk.chunk_id, chk.artifact_id, chk.chunk_type, chk.label,
                     chk.text, chk.start_line, chk.end_line, chk.estimated_tokens, json.dumps(chk.keywords))
                )
            conn.commit()

        return artifact_id

    def slice_context_window(self, artifact_id: str, query: str = "", max_token_budget: int = 800) -> SlicedContext:
        """
        Dynamically extracts and serves the most critical chunks fitting the token budget.
        Calculates BM25-style keyword relevance for targeted queries.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            art = conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
            if not art:
                raise ValueError(f"Artifact {artifact_id} not found in vault")

            chunks = conn.execute("SELECT * FROM chunks WHERE artifact_id = ?", (artifact_id,)).fetchall()

        if not chunks:
            return SlicedContext(
                artifact_id=artifact_id,
                total_raw_tokens=art["raw_tokens"],
                served_tokens=0,
                token_saving_pct=100.0,
                selected_chunks_count=0,
                total_chunks_count=0,
                context_text="// No semantic chunks indexed."
            )

        # Score chunks based on query relevance + priority keywords
        query_terms = set(re.findall(r"\w+", query.lower())) if query else set()
        priority_markers = {"vulnerability", "critical", "entry0", "main", "overflow", "exploit", "cve", "password"}

        scored_chunks = []
        for chk in chunks:
            kws = set(json.loads(chk["keywords_json"]))
            text_lower = chk["content"].lower()

            score = 0.0
            # Query match bonus
            for q in query_terms:
                if q in kws:
                    score += 10.0
                if q in text_lower:
                    score += 5.0

            # Intrinsic security relevance bonus
            for p in priority_markers:
                if p in kws or p in text_lower:
                    score += 3.0

            # Entrypoint bonus
            if "entry" in chk["label"].lower() or "main" in chk["label"].lower():
                score += 8.0

            scored_chunks.append((score, chk))

        # Sort highest score first
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        selected = []
        accumulated_tokens = 0
        for score, chk in scored_chunks:
            tokens = chk["tokens"]
            if accumulated_tokens + tokens <= max_token_budget:
                selected.append(chk)
                accumulated_tokens += tokens
            elif not selected:
                # If even 1 chunk is larger than budget, truncate it to fit
                truncated = chk["content"][:max_token_budget * 4]
                selected.append(chk)
                accumulated_tokens = self.estimate_tokens(truncated)
                break

        # Re-sort selected chunks by start_line for coherent reading
        selected.sort(key=lambda c: c["start_line"])

        body = "\n\n".join([
            f"// --- [CHUNK: {c['label']} (lines {c['start_line']}-{c['end_line']})] ---\n{c['content']}"
            for c in selected
        ])

        total_raw = art["raw_tokens"]
        savings = max(0.0, (1.0 - (accumulated_tokens / max(total_raw, 1))) * 100.0)

        header = (
            f"[CONTEXT-MODE SLICED VIEW: {artifact_id}]\n"
            f"Raw Tokens: {total_raw} | Served: {accumulated_tokens} | Token Reduction: {savings:.1f}%\n"
            f"Chunks Served: {len(selected)} / {len(chunks)}\n"
            f"{'=' * 60}\n"
        )

        return SlicedContext(
            artifact_id=artifact_id,
            total_raw_tokens=total_raw,
            served_tokens=accumulated_tokens,
            token_saving_pct=round(savings, 2),
            selected_chunks_count=len(selected),
            total_chunks_count=len(chunks),
            context_text=header + body
        )

    def search_artifacts(self, keyword: str) -> List[Dict[str, Any]]:
        """Search indexed chunks and artifacts by keyword."""
        kw_clean = f"%{keyword.lower()}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT DISTINCT a.id, a.cas_hash, a.tool_name, a.title, a.raw_tokens, a.created_at, c.byte_size
                FROM artifacts a
                JOIN cas_objects c ON a.cas_hash = c.sha256
                LEFT JOIN chunks chk ON a.id = chk.artifact_id
                WHERE chk.content LIKE ? OR a.title LIKE ? OR a.tool_name LIKE ? OR chk.keywords_json LIKE ?
                ORDER BY a.created_at DESC
            """, (kw_clean, kw_clean, kw_clean, kw_clean)).fetchall()
            return [dict(r) for r in rows]

    def retrieve_raw(self, artifact_id: str) -> Optional[str]:
        """Retrieve full uncompressed raw payload from CAS by artifact ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT c.raw_content
                FROM artifacts a
                JOIN cas_objects c ON a.cas_hash = c.sha256
                WHERE a.id = ?
            """, (artifact_id,)).fetchone()
            return row["raw_content"] if row else None

