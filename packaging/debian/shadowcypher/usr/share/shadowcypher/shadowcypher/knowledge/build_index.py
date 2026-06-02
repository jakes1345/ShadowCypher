#!/usr/bin/env python3
"""
Build knowledge base search index using bge-small-en-v1.5 ONNX.
Outputs:
  - index.npy    : float32 embeddings (N, 384)
  - chunks.json  : list of {id, file, section, text, bm25_tokens}
  - metadata.json: build timestamp, model, chunk count

Dependencies:
  pip install onnxruntime transformers numpy
  pip install huggingface_hub  # for model download

Model: BAAI/bge-small-en-v1.5 (INT8 ONNX, ~32MB)
"""

import os
import sys
import json
import re
import hashlib
import time
from pathlib import Path

import numpy as np

# ── Config ──────────────────────────────────────────────────────────────────

KNOWLEDGE_DIR = Path(__file__).parent
INDEX_FILE = KNOWLEDGE_DIR / "index.npy"
CHUNKS_FILE = KNOWLEDGE_DIR / "chunks.json"
METADATA_FILE = KNOWLEDGE_DIR / "metadata.json"
MODEL_DIR = KNOWLEDGE_DIR / "model"

CHUNK_SIZE = 400      # target tokens per chunk
CHUNK_OVERLAP = 80    # overlap between consecutive chunks
MIN_CHUNK_CHARS = 60  # discard tiny chunks

MODEL_REPO = "BAAI/bge-small-en-v1.5"
MODEL_ONNX_PATH = MODEL_DIR / "model.onnx"

# ── Markdown chunking ───────────────────────────────────────────────────────

def load_and_chunk_md(filepath: Path) -> list[dict]:
    """Split markdown file into overlapping chunks preserving section context."""
    text = filepath.read_text(encoding="utf-8")
    rel = filepath.relative_to(KNOWLEDGE_DIR)

    # Split on H2/H3 headers to get natural sections
    sections = re.split(r"(^#{1,3} .+$)", text, flags=re.MULTILINE)
    chunks = []
    current_header = ""
    buffer = []
    word_count = 0

    def flush(header, buf):
        content = "\n".join(buf).strip()
        if len(content) < MIN_CHUNK_CHARS:
            return []
        # Prepend section header for context
        full = f"{header}\n{content}".strip() if header else content
        chunk_id = hashlib.md5(full.encode()).hexdigest()[:12]
        # Simple BM25 token list: lowercase words, strip punctuation
        tokens = re.findall(r"\b[a-z0-9][a-z0-9\-\.]*\b", full.lower())
        return [{
            "id": chunk_id,
            "file": str(rel),
            "section": header.strip("# ").strip(),
            "text": full,
            "bm25_tokens": tokens,
        }]

    for part in sections:
        part = part.strip()
        if not part:
            continue
        if re.match(r"^#{1,3} ", part):
            # Flush previous buffer
            if buffer:
                chunks.extend(flush(current_header, buffer))
            current_header = part
            buffer = []
            word_count = 0
        else:
            # Accumulate into buffer; split at CHUNK_SIZE words with overlap
            words = part.split()
            i = 0
            while i < len(words):
                batch = words[i:i + CHUNK_SIZE]
                buffer.append(" ".join(batch))
                word_count += len(batch)
                if word_count >= CHUNK_SIZE:
                    chunks.extend(flush(current_header, buffer))
                    # Keep last CHUNK_OVERLAP words for next chunk
                    overlap_words = " ".join(buffer).split()[-CHUNK_OVERLAP:]
                    buffer = [" ".join(overlap_words)]
                    word_count = len(overlap_words)
                i += CHUNK_SIZE

    if buffer:
        chunks.extend(flush(current_header, buffer))

    return chunks


def load_all_chunks() -> list[dict]:
    chunks = []
    for md_file in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        if md_file.name.startswith("_"):
            continue
        file_chunks = load_and_chunk_md(md_file)
        chunks.extend(file_chunks)
        print(f"  {md_file.relative_to(KNOWLEDGE_DIR)}: {len(file_chunks)} chunks")
    return chunks


# ── Model download & embedding ──────────────────────────────────────────────

def download_model():
    """Download bge-small-en-v1.5 ONNX INT8 from HuggingFace."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    if MODEL_ONNX_PATH.exists():
        print(f"  Model already at {MODEL_ONNX_PATH}, skipping download")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading {MODEL_REPO} ONNX model (~32MB)...")

    # Try to get the ONNX optimized version
    try:
        path = snapshot_download(
            repo_id="optimum/bge-small-en-v1.5",
            allow_patterns=["*.onnx", "*.json", "*.txt", "tokenizer*"],
            local_dir=str(MODEL_DIR),
        )
        # Find the ONNX file
        onnx_files = list(MODEL_DIR.rglob("*.onnx"))
        if onnx_files:
            # Copy to expected path if needed
            if not MODEL_ONNX_PATH.exists():
                import shutil
                shutil.copy(onnx_files[0], MODEL_ONNX_PATH)
        print(f"  Downloaded to {MODEL_DIR}")
    except Exception as e:
        print(f"  optimum/bge-small-en-v1.5 failed ({e}), trying BAAI/bge-small-en-v1.5...")
        snapshot_download(
            repo_id="BAAI/bge-small-en-v1.5",
            allow_patterns=["onnx/*", "tokenizer*", "*.json", "*.txt"],
            local_dir=str(MODEL_DIR),
        )
        # Rename onnx/ subdir files
        onnx_subdir = MODEL_DIR / "onnx"
        if onnx_subdir.exists():
            for f in onnx_subdir.iterdir():
                f.rename(MODEL_DIR / f.name)
            onnx_subdir.rmdir()


def load_tokenizer():
    """Load tokenizer from model dir."""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print("ERROR: transformers not installed. Run: pip install transformers")
        sys.exit(1)

    # Try local model dir first, then HuggingFace
    if (MODEL_DIR / "tokenizer_config.json").exists():
        return AutoTokenizer.from_pretrained(str(MODEL_DIR))
    return AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")


def compute_embeddings(texts: list[str]) -> np.ndarray:
    """Compute embeddings using ONNX Runtime, batch of texts."""
    try:
        import onnxruntime as ort
    except ImportError:
        print("ERROR: onnxruntime not installed. Run: pip install onnxruntime")
        sys.exit(1)

    # Find ONNX model file
    onnx_candidates = list(MODEL_DIR.rglob("*.onnx"))
    if not onnx_candidates:
        print(f"ERROR: No .onnx file found in {MODEL_DIR}")
        sys.exit(1)

    # Prefer model_quantized.onnx (INT8) or model.onnx
    onnx_file = None
    for candidate in onnx_candidates:
        if "quantized" in candidate.name or "int8" in candidate.name.lower():
            onnx_file = candidate
            break
    if onnx_file is None:
        onnx_file = onnx_candidates[0]

    print(f"  Using ONNX model: {onnx_file.name}")

    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(str(onnx_file), sess_options=sess_options)

    tokenizer = load_tokenizer()

    # BGE models benefit from prepending query/passage instruction
    # For indexing (passages): "Represent this sentence for searching relevant passages: "
    prefix = "Represent this sentence for searching relevant passages: "
    texts = [prefix + t for t in texts]

    BATCH = 32
    all_embeddings = []

    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )

        # ONNX Runtime expects numpy arrays
        inputs = {
            "input_ids": encoded["input_ids"].astype(np.int64),
            "attention_mask": encoded["attention_mask"].astype(np.int64),
        }
        if "token_type_ids" in encoded:
            inputs["token_type_ids"] = encoded["token_type_ids"].astype(np.int64)

        outputs = session.run(None, inputs)

        # Use [CLS] token embedding (first token) — BGE pooling strategy
        # Some models output last_hidden_state [batch, seq, 384]
        # Others output pooler_output [batch, 384]
        if len(outputs[0].shape) == 3:
            embeddings = outputs[0][:, 0, :]  # CLS token
        else:
            embeddings = outputs[0]

        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms

        all_embeddings.append(embeddings.astype(np.float32))

        print(f"  Embedded batch {i // BATCH + 1}/{(len(texts) + BATCH - 1) // BATCH}")

    return np.vstack(all_embeddings)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== ShadowCypher Knowledge Base Index Builder ===\n")

    print("1. Loading and chunking markdown files...")
    chunks = load_all_chunks()
    print(f"   Total chunks: {len(chunks)}\n")

    if not chunks:
        print("ERROR: No chunks found. Make sure knowledge/*.md files exist.")
        sys.exit(1)

    print("2. Downloading/verifying embedding model...")
    download_model()
    print()

    print("3. Computing embeddings...")
    texts = [c["text"] for c in chunks]
    t0 = time.time()
    embeddings = compute_embeddings(texts)
    elapsed = time.time() - t0
    print(f"   Done in {elapsed:.1f}s. Shape: {embeddings.shape}\n")

    print("4. Saving index...")
    np.save(INDEX_FILE, embeddings)
    with open(CHUNKS_FILE, "w") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    metadata = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": MODEL_REPO,
        "chunks": len(chunks),
        "embedding_dim": embeddings.shape[1],
        "files": list({c["file"] for c in chunks}),
    }
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

    index_size = os.path.getsize(INDEX_FILE) / 1024 / 1024
    chunks_size = os.path.getsize(CHUNKS_FILE) / 1024
    print(f"   index.npy:   {index_size:.1f} MB")
    print(f"   chunks.json: {chunks_size:.0f} KB")
    print(f"   metadata.json written\n")
    print(f"=== Done. {len(chunks)} chunks indexed. ===")


if __name__ == "__main__":
    main()
