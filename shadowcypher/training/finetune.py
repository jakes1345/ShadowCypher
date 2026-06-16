"""
Shadow AI fine-tuning via Unsloth + TRL.
Base model: google/gemma-3-1b-it (instruction-tuned, matches MediaPipe target)
Output: LoRA adapter merged to full model, exported for MediaPipe LiteRT

Requirements:
  pip install unsloth trl datasets torch

Usage:
  python finetune.py
  # Outputs: shadow_model/ (full merged weights)
  # Convert to LiteRT .task with: ai_edge_torch (see README)
"""

import json
from pathlib import Path

TRAIN_FILE = Path(__file__).parent / "shadow_train.jsonl"
EVAL_FILE = Path(__file__).parent / "shadow_eval.jsonl"
OUTPUT_DIR = Path(__file__).parent / "shadow_model"

MAX_SEQ_LEN = 512
BATCH_SIZE = 2
GRAD_ACCUM = 4
EPOCHS = 2
LR = 2e-4
LORA_RANK = 16


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def conversations_to_gemma(example: dict) -> dict:
    """Format conversations list into Gemma chat template string."""
    turns = example["conversations"]
    parts = []
    for turn in turns:
        role = turn["role"]
        content = turn["content"]
        if role == "system":
            parts.append(f"<start_of_turn>system\n{content}<end_of_turn>")
        elif role == "user":
            parts.append(f"<start_of_turn>user\n{content}<end_of_turn>")
        elif role == "assistant":
            parts.append(f"<start_of_turn>model\n{content}<end_of_turn>")
    return {"text": "\n".join(parts) + "\n"}


def main():
    from unsloth import FastLanguageModel
    from trl import SFTTrainer, SFTConfig
    from datasets import Dataset

    print("[finetune] Loading base model: google/gemma-3-1b-it")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="google/gemma-3-1b-it",
        max_seq_length=MAX_SEQ_LEN,
        dtype=None,  # auto-detect
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=LORA_RANK * 2,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    print(f"[finetune] Loading dataset from {TRAIN_FILE}")
    train_data = load_jsonl(TRAIN_FILE)
    eval_data = load_jsonl(EVAL_FILE)

    train_ds = Dataset.from_list([conversations_to_gemma(ex) for ex in train_data])
    eval_ds = Dataset.from_list([conversations_to_gemma(ex) for ex in eval_data])

    print(f"[finetune] Train: {len(train_ds)} | Eval: {len(eval_ds)}")

    training_args = SFTConfig(
        output_dir=str(OUTPUT_DIR / "checkpoints"),
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        learning_rate=LR,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=25,
        eval_strategy="steps",
        eval_steps=200,
        save_steps=500,
        fp16=True,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LEN,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        args=training_args,
    )

    print("[finetune] Starting training...")
    trainer.train()

    print(f"[finetune] Saving merged model to {OUTPUT_DIR / 'merged'}")
    model.save_pretrained_merged(str(OUTPUT_DIR / "merged"), tokenizer, save_method="merged_16bit")

    print("""
[finetune] Done.

Next step — convert to MediaPipe LiteRT .task format:
  pip install ai-edge-torch
  python convert_to_litert.py  (see shadowcypher/training/convert_to_litert.py)

Then place the .task file on-device:
  adb push shadow_model.task /sdcard/Download/
  # Shadow app downloads it to internal storage on user request
""")


if __name__ == "__main__":
    main()
