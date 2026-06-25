"""
doc-to-lora — fine-tune a local Ollama model on security documents.

Based on Sakana AI's doc-to-lora (MIT license).
Converts a corpus of security documents (CVE advisories, tool manuals,
vulnerability reports) into a LoRA adapter for the local Ollama model.

Pipeline:
  1. Ingest documents from a directory (txt, pdf, html, md)
  2. Chunk into training examples via sliding window
  3. Generate Q&A pairs from each chunk (using current AI model)
  4. Write JSONL training file for llama.cpp or Ollama fine-tuning
  5. Launch fine-tuning via llama.cpp (if available)

Usage:
    from shadowcypher.ai.doc_lora import doc_lora
    doc_lora.train_on_dir("/path/to/security-docs", model="qwen3:8b")
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

from shadowcypher.core.logger import logger

LORA_WORK_DIR = Path.home() / ".shadowcypher" / "lora"

CHUNK_SIZE = 800     # characters per training chunk
CHUNK_OVERLAP = 100  # overlap between chunks


class DocLoRA:
    """Fine-tune local models on security document corpora."""

    def __init__(self):
        LORA_WORK_DIR.mkdir(parents=True, exist_ok=True)

    # ── Document ingestion ────────────────────────────────────────────────────

    def _read_file(self, path: Path) -> str:
        """Read text from txt/md/html files. PDF requires pdfminer."""
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".log", ".csv"}:
            try:
                return path.read_text(errors="replace")
            except Exception:
                return ""
        if suffix == ".html":
            text = path.read_text(errors="replace")
            return re.sub(r"<[^>]+>", " ", text)
        if suffix == ".pdf":
            try:
                from pdfminer.high_level import extract_text
                return extract_text(str(path))
            except ImportError:
                logger.warning("doc_lora", "pdfminer not installed — skipping PDF")
                return ""
        return ""

    def _chunk(self, text: str) -> list[str]:
        """Sliding window chunking."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunks.append(text[start:end].strip())
            start += CHUNK_SIZE - CHUNK_OVERLAP
        return [c for c in chunks if len(c) > 100]

    # ── Q&A generation ────────────────────────────────────────────────────────

    def _generate_qa(self, chunk: str, on_output: Callable = None) -> list[dict]:
        """Use the AI to generate Q&A pairs from a text chunk."""
        prompt = (
            "You are creating training data for a security AI. "
            "Given the text below, generate 2-3 question-answer pairs. "
            "Questions should be specific and technical. "
            "Format as JSON array: [{\"question\": \"...\", \"answer\": \"...\"}]\n\n"
            f"TEXT:\n{chunk[:600]}\n\nJSON:"
        )
        try:
            from shadowcypher.ai.providers import provider_registry
            raw = provider_registry.generate(prompt, max_tokens=400, temperature=0.4)
            # Extract JSON from response
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                pairs = json.loads(m.group(0))
                return [p for p in pairs if isinstance(p, dict) and "question" in p and "answer" in p]
        except Exception as e:
            logger.debug("doc_lora", f"QA gen failed: {e}")
        return []

    # ── Training data export ──────────────────────────────────────────────────

    def _write_jsonl(self, pairs: list[dict], out_path: Path):
        """Write training pairs as Ollama/llama.cpp JSONL format."""
        with open(out_path, "w") as f:
            for p in pairs:
                record = {
                    "messages": [
                        {"role": "user", "content": p["question"]},
                        {"role": "assistant", "content": p["answer"]},
                    ]
                }
                f.write(json.dumps(record) + "\n")
        logger.info("doc_lora", f"Wrote {len(pairs)} training pairs to {out_path}")

    # ── Main API ──────────────────────────────────────────────────────────────

    def prepare_dataset(
        self,
        source_dir: str,
        on_output: Callable = None,
        max_files: int = 50,
    ) -> Path:
        """
        Ingest documents from source_dir, generate Q&A pairs, write JSONL.

        Args:
            source_dir: Directory containing security documents.
            on_output:  Progress callback.
            max_files:  Cap on files to process (to avoid runaway cost).

        Returns:
            Path to the output JSONL training file.
        """
        emit = on_output or (lambda x: None)
        src = Path(source_dir)
        if not src.exists():
            raise FileNotFoundError(f"Source dir not found: {source_dir}")

        extensions = {".txt", ".md", ".html", ".log", ".pdf", ".csv"}
        files = [f for f in src.rglob("*") if f.suffix.lower() in extensions][:max_files]
        emit(f"[DocLoRA] Found {len(files)} files in {source_dir}\n")

        all_pairs = []
        for i, fpath in enumerate(files):
            emit(f"[DocLoRA] [{i+1}/{len(files)}] Processing {fpath.name}...\n")
            text = self._read_file(fpath)
            if not text:
                continue
            chunks = self._chunk(text)
            for chunk in chunks[:10]:  # max 10 chunks per file
                pairs = self._generate_qa(chunk, on_output)
                all_pairs.extend(pairs)

        emit(f"[DocLoRA] Generated {len(all_pairs)} Q&A pairs\n")

        out_path = LORA_WORK_DIR / "training_data.jsonl"
        self._write_jsonl(all_pairs, out_path)
        emit(f"[DocLoRA] Dataset saved: {out_path}\n")
        return out_path

    def train(
        self,
        model: str = "qwen3:8b",
        dataset_path: str = None,
        on_output: Callable = None,
        epochs: int = 3,
    ):
        """
        Launch LoRA fine-tuning via llama.cpp (if installed).

        Args:
            model:        Base model name (Ollama format, e.g. "qwen3:8b").
            dataset_path: Path to JSONL training file (uses last prepared dataset if None).
            on_output:    Progress callback.
            epochs:       Training epochs.
        """
        emit = on_output or (lambda x: None)
        data_file = Path(dataset_path) if dataset_path else LORA_WORK_DIR / "training_data.jsonl"

        if not data_file.exists():
            emit("[DocLoRA] No training data found. Run prepare_dataset() first.\n")
            return

        # Check for llama.cpp fine-tuning binary
        ft_bin = None
        for candidate in ["llama-finetune", "/usr/local/bin/llama-finetune",
                           str(Path.home() / "llama.cpp/llama-finetune")]:
            if Path(candidate).exists() or subprocess.run(
                ["which", candidate], capture_output=True
            ).returncode == 0:
                ft_bin = candidate
                break

        if not ft_bin:
            emit("[DocLoRA] llama.cpp fine-tuning binary not found.\n")
            emit("[DocLoRA] Install llama.cpp and compile with: make -j llama-finetune\n")
            emit(f"[DocLoRA] Training data is ready at: {data_file}\n")
            emit("[DocLoRA] You can also use Unsloth or axolotl with this JSONL dataset.\n")
            return

        out_dir = LORA_WORK_DIR / "lora_out"
        out_dir.mkdir(exist_ok=True)

        cmd = [
            ft_bin,
            "--model-base", model,
            "--train-data", str(data_file),
            "--output-dir", str(out_dir),
            "--epochs", str(epochs),
            "--lora-r", "16",
            "--lora-alpha", "32",
        ]
        emit(f"[DocLoRA] Starting fine-tuning: {' '.join(cmd)}\n")

        def _run():
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    emit(f"[DocLoRA] {line}")
                proc.wait()
                emit(f"[DocLoRA] Training complete (exit {proc.returncode}). LoRA at: {out_dir}\n")
            except Exception as e:
                emit(f"[DocLoRA] Training failed: {e}\n")

        threading.Thread(target=_run, daemon=True, name="DocLoRA").start()

    def train_on_dir(
        self,
        source_dir: str,
        model: str = "qwen3:8b",
        on_output: Callable = None,
        epochs: int = 3,
    ):
        """Convenience: prepare dataset then launch training."""
        def _run():
            try:
                data_file = self.prepare_dataset(source_dir, on_output=on_output)
                self.train(model=model, dataset_path=str(data_file),
                           on_output=on_output, epochs=epochs)
            except Exception as e:
                if on_output:
                    on_output(f"[DocLoRA] Error: {e}\n")

        threading.Thread(target=_run, daemon=True, name="DocLoRA-Pipeline").start()

    def status(self) -> str:
        data_file = LORA_WORK_DIR / "training_data.jsonl"
        if data_file.exists():
            lines = sum(1 for _ in open(data_file))
            return f"training_data.jsonl: {lines} examples | lora_dir: {LORA_WORK_DIR}"
        return f"No training data yet | work_dir: {LORA_WORK_DIR}"


# Global singleton
doc_lora = DocLoRA()
