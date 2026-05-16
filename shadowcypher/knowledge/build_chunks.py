#!/usr/bin/env python3
"""
Fast KB chunker — no ML dependencies.
Reads all *.md files under this directory, chunks them, writes chunks.json.
Run this every time you edit an MD file to refresh the search index.

Output: chunks.json  (used by assistant.js BM25 search and build_index.py embeddings)
Usage:  python3 build_chunks.py
"""

import json
import re
import hashlib
import time
from pathlib import Path
from collections import Counter

KNOWLEDGE_DIR = Path(__file__).parent
CHUNKS_FILE = KNOWLEDGE_DIR / "chunks.json"

CHUNK_WORDS = 350    # target words per chunk
OVERLAP_WORDS = 60   # words carried into next chunk
MIN_CHARS = 50       # discard tiny fragments


def tokenize_bm25(text: str) -> list[str]:
    """Lowercase word tokens for BM25 scoring. Also add bigrams for phrase matching."""
    t = text.lower()
    t = re.sub(r"cve[- ](\d{4})[- ](\d+)", r"cve-\1-\2", t)
    t = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "ip_addr", t)
    t = re.sub(r"'(s|ll|re|ve|m|d|t)\b", "", t)
    tokens = re.findall(r"\b[a-z][a-z0-9\-\.]{0,30}\b", t)
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return tokens + bigrams


def chunk_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path.relative_to(KNOWLEDGE_DIR))
    chunks = []

    # Split on any heading level (# through ###)
    parts = re.split(r"(^#{1,3} .+$)", text, flags=re.MULTILINE)

    current_header = ""
    buffer_words: list[str] = []

    def flush(header: str, words: list[str]) -> None:
        if not words:
            return
        content = " ".join(words).strip()
        if len(content) < MIN_CHARS:
            return
        full = f"{header}\n{content}".strip() if header else content
        chunk_id = hashlib.md5(full.encode()).hexdigest()[:12]
        chunks.append({
            "id": chunk_id,
            "file": rel,
            "section": header.lstrip("# ").strip(),
            "text": full,
            "bm25_tokens": tokenize_bm25(full),
        })

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if re.match(r"^#{1,3} ", part):
            # Flush current buffer with overlap before starting new section
            if buffer_words:
                flush(current_header, buffer_words)
            current_header = part
            buffer_words = []
        else:
            words = part.split()
            i = 0
            while i < len(words):
                batch = words[i: i + CHUNK_WORDS]
                buffer_words.extend(batch)

                if len(buffer_words) >= CHUNK_WORDS:
                    flush(current_header, buffer_words)
                    # Keep tail for overlap
                    buffer_words = buffer_words[-OVERLAP_WORDS:]

                i += len(batch)

    if buffer_words:
        flush(current_header, buffer_words)

    return chunks


def main():
    print("=== ShadowCypher KB Chunker ===\n")
    t0 = time.time()

    all_chunks: list[dict] = []
    md_files = sorted(f for f in KNOWLEDGE_DIR.rglob("*.md"))

    for f in md_files:
        if f.name.startswith("_"):
            continue
        fc = chunk_file(f)
        all_chunks.extend(fc)
        print(f"  {f.relative_to(KNOWLEDGE_DIR)}: {len(fc)} chunks")

    print(f"\nTotal: {len(all_chunks)} chunks from {len(md_files)} files")

    # Deduplicate by id
    seen: set[str] = set()
    deduped = []
    for c in all_chunks:
        if c["id"] not in seen:
            seen.add(c["id"])
            deduped.append(c)

    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = CHUNKS_FILE.stat().st_size / 1024
    elapsed = time.time() - t0
    print(f"Written: chunks.json ({size_kb:.0f} KB) in {elapsed:.2f}s")
    print("\nDeploy to Android assets:")
    print(f"  cp {CHUNKS_FILE} android/assistant/src/main/assets/chunks.json")


if __name__ == "__main__":
    main()
