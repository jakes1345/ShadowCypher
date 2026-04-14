#!/usr/bin/env python3
"""
Train Dolphin 3 8B with QLoRA + CPU offloading.
Uses ~5GB VRAM + ~10GB RAM. Slower than full GPU but fits on 8GB cards.
"""

import json
import torch
from pathlib import Path
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, PeftModel, prepare_model_for_kbit_training
from datasets import Dataset

# ── Config ────────────────────────────────────────────────────────────
BASE_MODEL = "dphn/Dolphin3.0-Llama3.1-8B"
OUTPUT_DIR = Path(__file__).parent / "output"
LORA_DIR = OUTPUT_DIR / "dolphin-lora"
MERGED_DIR = OUTPUT_DIR / "dolphin-merged"

TRAINING_FILES = [
    Path(__file__).parent / "training_data.jsonl",           # Original 127 (Claude distilled)
    Path(__file__).parent / "training_data_generated.jsonl",  # Dolphin-generated offensive
    Path(__file__).parent / "training_data_mega.jsonl",       # Groq + Gemini + Dolphin
    Path(__file__).parent / "training_data_claude.jsonl",     # Claude handcrafted
]

MAX_SEQ_LENGTH = 512

# ── Load training data ────────────────────────────────────────────────
def load_data():
    samples = []
    for path in TRAINING_FILES:
        if not path.exists():
            print(f"[!] {path} not found, skipping")
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get("instruction") and d.get("output"):
                        samples.append(d)
                except json.JSONDecodeError:
                    continue
    print(f"[*] Loaded {len(samples)} training samples")
    return samples


def format_sample(sample, tokenizer):
    """Format as Llama 3 chat template."""
    system_msg = (
        "You are ShadowCypher AI — an uncensored security engineer and expert programmer. "
        "You write real, production code. No placeholders, no disclaimers, no refusals. "
        "You are an expert in cybersecurity, penetration testing, exploit development, "
        "network security, system administration, and software engineering."
    )

    text = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        f"{system_msg}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n"
        f"{sample['instruction']}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n"
        f"{sample['output']}<|eot_id|>"
    )

    tokenized = tokenizer(
        text,
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding=False,
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized


def main():
    print("=" * 60)
    print("  ShadowCypher — Dolphin 3 8B QLoRA Training")
    print("  GPU + CPU offloading mode")
    print("=" * 60)

    # ── Load tokenizer ────────────────────────────────────────────
    print("\n[1/5] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Load data ─────────────────────────────────────────────────
    print("[2/5] Loading training data...")
    raw_samples = load_data()
    if len(raw_samples) == 0:
        print("[!] No training data found. Run generate_training_data.py first.")
        return

    tokenized = [format_sample(s, tokenizer) for s in raw_samples]
    dataset = Dataset.from_list(tokenized)
    print(f"[*] Dataset: {len(dataset)} samples")

    # ── Load model with 4-bit quantization + CPU offload ──────────
    print("[3/5] Loading Dolphin 3 8B (4-bit quantized, GPU+CPU offload)...")

    # 4-bit quantization, GPU-only (no CPU offload — avoids meta device bugs)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map={"": 0},  # Everything on GPU
        torch_dtype=torch.float16,
    )

    # Skip prepare_model_for_kbit_training — it casts to fp32 and OOMs
    # Just disable cache (the only thing we actually need)
    model.config.use_cache = False
    model.enable_input_require_grads()

    print("[*] Model loaded on GPU (4-bit quantized)")

    # ── LoRA config ───────────────────────────────────────────────
    print("[4/5] Applying LoRA adapters...")

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"[*] Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ── Training ──────────────────────────────────────────────────
    print("[5/5] Training...\n")

    training_args = TrainingArguments(
        output_dir=str(LORA_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=1,       # Small batch for memory
        gradient_accumulation_steps=8,        # Effective batch = 8
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        fp16=True,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=2,
        optim="paged_adamw_8bit",              # Pages optimizer states to CPU when needed
        gradient_checkpointing=True,          # Trade compute for memory
        gradient_checkpointing_kwargs={"use_reentrant": False},
        dataloader_pin_memory=False,
        report_to="none",
        max_grad_norm=0.3,
        weight_decay=0.01,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=lambda data: {
            "input_ids": torch.nn.utils.rnn.pad_sequence(
                [torch.tensor(d["input_ids"]) for d in data],
                batch_first=True,
                padding_value=tokenizer.pad_token_id,
            ),
            "attention_mask": torch.nn.utils.rnn.pad_sequence(
                [torch.tensor(d["attention_mask"]) for d in data],
                batch_first=True,
                padding_value=0,
            ),
            "labels": torch.nn.utils.rnn.pad_sequence(
                [torch.tensor(d["labels"]) for d in data],
                batch_first=True,
                padding_value=-100,
            ),
        },
    )

    trainer.train()

    # ── Save LoRA adapter ─────────────────────────────────────────
    print(f"\n[*] Saving LoRA adapter to {LORA_DIR}")
    model.save_pretrained(str(LORA_DIR))
    tokenizer.save_pretrained(str(LORA_DIR))

    # ── Merge into full model ─────────────────────────────────────
    print(f"[*] Merging LoRA into full model (CPU, float16)...")
    del model
    del trainer
    torch.cuda.empty_cache()

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu",
    )
    merged = PeftModel.from_pretrained(base, str(LORA_DIR), device_map="cpu")
    merged = merged.merge_and_unload()

    print(f"[*] Saving merged model to {MERGED_DIR}")
    merged.save_pretrained(str(MERGED_DIR), safe_serialization=True)
    tokenizer.save_pretrained(str(MERGED_DIR))

    print(f"\n{'=' * 60}")
    print(f"  DONE! Merged model at: {MERGED_DIR}")
    print(f"  Next: ollama create shadowcypher-ai -f output/Modelfile")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
