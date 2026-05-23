"""AI Engine — Dual backend: Ollama (primary) and llama-cpp-python (fallback).

Uses Ollama REST API at localhost:11434 for GPU-accelerated inference.
Falls back to llama-cpp-python if Ollama is unavailable.
"""

import os
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.ai.providers import provider_registry
from shadowcypher.ai.guard import guard, BLOCK, FLAG


OLLAMA_BASE = getattr(config.ai, 'api_base', 'http://127.0.0.1:11434')


class AIEngine:
    """Local LLM inference engine with Ollama and llama-cpp-python backends."""

    def __init__(self):
        self._llm = None  # llama-cpp-python instance (fallback)
        self._lock = threading.Lock()
        self._loading = False
        self._loaded = False
        self._backend = None  # "ollama" or "llamacpp"
        self._model_name = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def is_loading(self) -> bool:
        return self._loading

    @property
    def backend(self) -> Optional[str]:
        return self._backend

    @property
    def model_name(self) -> Optional[str]:
        return self._model_name

    # ──────────────────────────────────────────────────────────────────
    # Ollama backend
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _ollama_request(endpoint: str, data: dict = None, timeout: int = 10) -> Optional[dict]:
        """Make a request to the Ollama API."""
        url = f"{OLLAMA_BASE}{endpoint}"
        try:
            if data is not None:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
            else:
                req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, json.JSONDecodeError):
            return None

    @staticmethod
    def _ollama_stream(endpoint: str, data: dict, on_token: Callable[[str], None] = None,
                       timeout: int = 300) -> str:
        """Stream a response from Ollama API."""
        url = f"{OLLAMA_BASE}{endpoint}"
        full_text = []
        in_think = False
        think_buf = []
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            # Buffer and suppress <think>...</think> blocks
                            think_buf.append(token)
                            combined = "".join(think_buf)
                            if "<think>" in combined:
                                in_think = True
                            if in_think:
                                if "</think>" in combined:
                                    in_think = False
                                    after = combined.split("</think>", 1)[1]
                                    think_buf = [after] if after else []
                                    if after:
                                        full_text.append(after)
                                        if on_token:
                                            on_token(after)
                                # suppress tokens while inside <think>
                                continue
                            # No think block active — flush buffer
                            out = "".join(think_buf)
                            think_buf = []
                            if out:
                                full_text.append(out)
                                if on_token:
                                    on_token(out)
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            if on_token:
                on_token(f"\n[Error] {e}")
        return "".join(full_text)

    @staticmethod
    def _strip_think(text: str) -> str:
        """Strip <think>...</think> blocks that Qwen3 may emit despite /no_think."""
        import re
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    @staticmethod
    def check_ollama() -> bool:
        """Check if Ollama is running."""
        result = AIEngine._ollama_request("/api/tags", timeout=3)
        return result is not None

    @staticmethod
    def list_ollama_models() -> list[str]:
        """List models available in Ollama."""
        result = AIEngine._ollama_request("/api/tags", timeout=5)
        if result and "models" in result:
            return [m["name"] for m in result["models"]]
        return []

    @staticmethod
    def detect_vram_gb() -> float:
        """Return total GPU VRAM in GB, or 0 if no GPU detected."""
        try:
            import subprocess
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                timeout=5, stderr=subprocess.DEVNULL, text=True,
            )
            return sum(int(x.strip()) for x in out.strip().splitlines() if x.strip()) / 1024
        except Exception:
            pass
        try:
            import subprocess
            out = subprocess.check_output(
                ["rocm-smi", "--showmeminfo", "vram", "--json"],
                timeout=5, stderr=subprocess.DEVNULL, text=True,
            )
            import json as _json
            data = _json.loads(out)
            total = sum(int(v.get("VRAM Total Memory (B)", 0)) for v in data.values() if isinstance(v, dict))
            return total / (1024 ** 3)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def recommended_base_model(vram_gb: float = 0) -> dict:
        """Return the recommended Dolphin model tier for the detected VRAM."""
        if vram_gb <= 0:
            vram_gb = AIEngine.detect_vram_gb()

        if vram_gb >= 22:
            return {
                "model": "dolphin-mixtral:8x7b",
                "size_gb": 26,
                "tier": "elite",
                "description": "Mixtral 8x7B uncensored — best reasoning, full MoE architecture",
            }
        if vram_gb >= 12:
            return {
                "model": "dolphin-llama3.1:8b-q8_0",
                "size_gb": 8.5,
                "tier": "pro",
                "description": "Llama 3.1 8B Q8 uncensored — maximum quality 8B, fills 16GB cleanly",
            }
        if vram_gb >= 7:
            return {
                "model": "dolphin-llama3:8b",
                "size_gb": 4.7,
                "tier": "standard",
                "description": "Llama 3 8B uncensored — zero refusals, strong reasoning",
            }
        return {
            "model": "dolphin-mistral:7b",
            "size_gb": 3.8,
            "tier": "lite",
            "description": "Mistral 7B uncensored — runs on 6GB VRAM or CPU",
        }

    def _select_ollama_model(self) -> Optional[str]:
        """Select best available Ollama model for security work."""
        models = self.list_ollama_models()
        if not models:
            return None

        # ShadowCypher tuned models first, then Dolphin tier, then generalist fallbacks
        preferences = [
            "shadowcypher-ai",
            "shadow-sec",
            "shadow-uncensored",
            "shadow-coder",
            "shadow-opus",
            "shadow-recon",
            "shadow-tool",
            "dolphin-mixtral",
            "dolphin-llama3.1",
            "dolphin-llama3",
            "dolphin-mistral",
            "dolphin",
            "qwen2.5-coder",
            "qwen3",
            "llama3.1",
            "granite",
            "qwen",
            "llama3",
            "mistral",
        ]

        for pref in preferences:
            for model in models:
                if pref in model.lower():
                    return model

        return models[0] if models else None

    # ──────────────────────────────────────────────────────────────────
    # Loading
    # ──────────────────────────────────────────────────────────────────

    def load(self, on_progress: Optional[Callable[[str], None]] = None,
             model_override: Optional[str] = None) -> bool:
        """Load the AI model. Tries Ollama first, then llama-cpp-python."""
        with self._lock:
            if self._loaded:
                return True
            if self._loading:
                return False
            self._loading = True

        # Try Ollama first
        if on_progress:
            on_progress("Checking Ollama backend...\n")

        if self.check_ollama():
            model = model_override or self._select_ollama_model()
            if model:
                if on_progress:
                    on_progress(f"Ollama running — using model: {model}\n")

                # Ensure model is pulled/ready
                if on_progress:
                    on_progress(f"Warming up {model}...\n")

                # Do a quick test generation to warm up the model
                test = self._ollama_request("/api/chat", {
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "options": {"num_predict": 1},
                }, timeout=120)

                if test and "message" in test:
                    self._backend = "ollama"
                    self._model_name = model
                    self._loaded = True
                    self._loading = False
                    if on_progress:
                        on_progress(f"Model ready: {model} (Ollama + CUDA)\n")
                    logger.info("ai", f"Ollama backend loaded: {model}")
                    return True
                else:
                    if on_progress:
                        on_progress(f"Model {model} failed to respond, trying llama-cpp fallback...\n")
            else:
                if on_progress:
                    on_progress("No models found in Ollama. Trying llama-cpp...\n")
        else:
            if on_progress:
                on_progress("Ollama not running. Trying llama-cpp-python...\n")

        # Fallback to llama-cpp-python
        return self._load_llamacpp(on_progress)

    def _load_llamacpp(self, on_progress: Callable[[str], None] = None) -> bool:
        """Fallback: load model with llama-cpp-python."""
        try:
            model_path = self._get_model_path()

            if not os.path.exists(model_path):
                if on_progress:
                    on_progress("Model not found locally. Downloading...\n")
                model_path = self._download_model(on_progress)
                if not model_path or not os.path.exists(model_path):
                    self._loading = False
                    return False

            if on_progress:
                on_progress("Loading model into GPU memory via llama-cpp...\n")

            try:
                from llama_cpp import Llama
            except ImportError:
                msg = "llama-cpp-python not installed. Run: pip install llama-cpp-python"
                logger.error("ai", msg)
                if on_progress:
                    on_progress(f"ERROR: {msg}\n")
                self._loading = False
                return False

            n_gpu = config.get("ai", "n_gpu_layers", default=35)
            n_ctx = config.get("ai", "n_ctx", default=4096)

            self._llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu,
                n_threads=6,
                verbose=False,
            )

            self._backend = "llamacpp"
            self._model_name = os.path.basename(model_path)
            self._loaded = True
            self._loading = False

            if on_progress:
                on_progress(f"Model loaded: {self._model_name} (llama-cpp + CUDA)\n")
            logger.info("ai", "llama-cpp backend loaded", path=model_path)
            return True

        except Exception as e:
            self._loading = False
            msg = f"Failed to load model: {e}"
            logger.error("ai", msg)
            if on_progress:
                on_progress(f"ERROR: {msg}\n")
            return False

    def _get_model_path(self) -> str:
        models_dir = Path(config.project_root) / "models"
        models_dir.mkdir(exist_ok=True)
        model_file = config.get("ai", "model_file")
        return str(models_dir / model_file)

    def _download_model(self, on_progress=None) -> str:
        try:
            from huggingface_hub import hf_hub_download
            repo = config.get("ai", "model_repo")
            filename = config.get("ai", "model_file")
            models_dir = Path(config.project_root) / "models"
            models_dir.mkdir(exist_ok=True)
            if on_progress:
                on_progress(f"Downloading {filename} from {repo}...\n")
            model_path = hf_hub_download(
                repo_id=repo, filename=filename,
                local_dir=str(models_dir), local_dir_use_symlinks=False,
            )
            if on_progress:
                on_progress(f"Download complete: {model_path}\n")
            return model_path
        except ImportError:
            if on_progress:
                on_progress("ERROR: huggingface_hub not installed\n")
            return ""
        except Exception as e:
            if on_progress:
                on_progress(f"ERROR: Download failed: {e}\n")
            return ""

    def load_async(self, on_progress: Callable[[str], None] = None,
                   on_complete: Callable[[bool], None] = None,
                   model_override: str = None):
        """Load model in background thread."""
        def _worker():
            success = self.load(on_progress, model_override=model_override)
            if on_complete:
                on_complete(success)
        threading.Thread(target=_worker, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────
    # Generation
    # ──────────────────────────────────────────────────────────────────

    def generate(self, prompt: str, system_prompt: str = "",
                 max_tokens: int = None, temperature: float = None,
                 stream: bool = False) -> str:
        """Generate a response. Routes through provider registry for cloud backends."""
        if max_tokens is None:
            max_tokens = config.get("ai", "max_tokens", default=2048)
        if temperature is None:
            temperature = config.get("ai", "temperature", default=0.7)

        # ── ShadowGuard: scan input before hitting Ollama ──
        gate = guard.scan_input(prompt, context="generate")
        if gate.action == BLOCK:
            return (f"[SHADOWGUARD] BLOCKED — Prompt injection detected "
                    f"(score={gate.score:.2f}). Request denied.")
        if gate.action == FLAG:
            logger.warning("ai", f"SHADOWGUARD_FLAG score={gate.score:.2f} — proceeding with caution")

        # Local Ollama is always preferred. Try it first regardless of _loaded state.
        if self._loaded and self._backend == "llamacpp":
            raw = self._generate_llamacpp(prompt, system_prompt, max_tokens, temperature)
            return guard.scan_output(raw).cleaned

        # Try Ollama (either tracked as loaded, or just running in background)
        ollama_model = self._model_name or self._select_ollama_model()
        if ollama_model:
            self._model_name = ollama_model
            result = self._generate_ollama(prompt, system_prompt, max_tokens, temperature)
            if not result.startswith("[Error]"):
                return guard.scan_output(result).cleaned

        # Fallback: cloud provider
        active = provider_registry.active
        if active and active.id != "ollama" and active.is_configured:
            raw = provider_registry.generate(prompt, system_prompt, max_tokens, temperature)
            return guard.scan_output(raw).cleaned

        return "[AI offline] Ollama is not running and no cloud provider is configured."

    def _generate_ollama(self, prompt: str, system_prompt: str,
                         max_tokens: int, temperature: float) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # Prepend /no_think to suppress Qwen3 chain-of-thought loops
        messages.append({"role": "user", "content": f"/no_think\n{prompt}"})

        result = self._ollama_request("/api/chat", {
            "model": self._model_name,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }, timeout=300)

        if result and "message" in result:
            response = self._strip_think(result["message"].get("content", ""))
            logger.info("ai", "Ollama generation complete")
            return response

        # Ollama returned nothing — try cloud fallback
        logger.warning("ai", "Ollama returned empty response, trying cloud fallback")
        active = provider_registry.active
        if active and active.id != "ollama" and active.is_configured:
            return provider_registry.generate(prompt, system_prompt, max_tokens, temperature)
        return "[Error] Ollama returned no response and no cloud fallback is configured."

    def _generate_llamacpp(self, prompt: str, system_prompt: str,
                           max_tokens: int, temperature: float) -> str:
        if not self._llm:
            return "[Error] llama-cpp model not loaded"

        if system_prompt:
            full_prompt = f"[INST] {system_prompt}\n\n{prompt} [/INST]"
        else:
            full_prompt = f"[INST] {prompt} [/INST]"

        try:
            result = self._llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.1,
                stop=["[INST]", "</s>"],
            )
            return result["choices"][0]["text"].strip()
        except Exception as e:
            return f"[Error] {e}"

    def generate_stream(self, prompt: str, system_prompt: str = "",
                        max_tokens: int = None, temperature: float = None,
                        on_token: Callable[[str], None] = None) -> str:
        """Stream tokens one at a time for real-time display."""
        if max_tokens is None:
            max_tokens = config.get("ai", "max_tokens", default=2048)
        if temperature is None:
            temperature = config.get("ai", "temperature", default=0.7)

        # llamacpp has its own stream path
        if self._loaded and self._backend == "llamacpp":
            return self._stream_llamacpp(prompt, system_prompt, max_tokens, temperature, on_token)

        # Try Ollama first (streaming)
        ollama_model = self._model_name or self._select_ollama_model()
        if ollama_model:
            self._model_name = ollama_model
            result = self._stream_ollama(prompt, system_prompt, max_tokens, temperature, on_token)
            if result:
                return result

        # Fallback: cloud provider
        active = provider_registry.active
        if active and active.id != "ollama" and active.is_configured:
            return provider_registry.generate_stream(prompt, system_prompt, max_tokens,
                                                     temperature, on_token=on_token)

        if on_token:
            on_token("[AI offline] Ollama is not running and no cloud provider is configured.\n")
        return ""

    def _stream_ollama(self, prompt, system_prompt, max_tokens, temperature, on_token):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": f"/no_think\n{prompt}"})

        return self._ollama_stream("/api/chat", {
            "model": self._model_name,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }, on_token=on_token)

    def _stream_llamacpp(self, prompt, system_prompt, max_tokens, temperature, on_token):
        if not self._llm:
            if on_token:
                on_token("[Error] Model not loaded\n")
            return ""

        if system_prompt:
            full_prompt = f"[INST] {system_prompt}\n\n{prompt} [/INST]"
        else:
            full_prompt = f"[INST] {prompt} [/INST]"

        full_text = []
        try:
            for chunk in self._llm(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.1,
                stop=["[INST]", "</s>"],
                stream=True,
            ):
                token = chunk["choices"][0]["text"]
                full_text.append(token)
                if on_token:
                    on_token(token)
        except Exception as e:
            if on_token:
                on_token(f"\n[Error] {e}")
        return "".join(full_text)

    # ──────────────────────────────────────────────────────────────────
    # Ollama model management
    # ──────────────────────────────────────────────────────────────────

    def pull_model(self, model_name: str, on_progress: Callable[[str], None] = None) -> bool:
        """Pull a model from Ollama registry."""
        url = f"{OLLAMA_BASE}/api/pull"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({"name": model_name, "stream": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1800) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        status = chunk.get("status", "")
                        if on_progress:
                            total = chunk.get("total", 0)
                            completed = chunk.get("completed", 0)
                            if total > 0:
                                pct = (completed / total) * 100
                                on_progress(f"{status}: {pct:.1f}%\n")
                            else:
                                on_progress(f"{status}\n")
                    except json.JSONDecodeError:
                        continue
            return True
        except Exception as e:
            if on_progress:
                on_progress(f"Pull failed: {e}\n")
            return False

    def switch_model(self, model_name: str, on_progress: Callable[[str], None] = None) -> bool:
        """Switch to a different Ollama model."""
        if self._backend != "ollama":
            if on_progress:
                on_progress("Can only switch models when using Ollama backend\n")
            return False

        if on_progress:
            on_progress(f"Switching to {model_name}...\n")

        # Test the model
        test = self._ollama_request("/api/chat", {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": False,
            "options": {"num_predict": 1},
        }, timeout=120)

        if test and "message" in test:
            self._model_name = model_name
            if on_progress:
                on_progress(f"Switched to {model_name}\n")
            logger.info("ai", f"Model switched to: {model_name}")
            return True

        if on_progress:
            on_progress(f"Failed to load {model_name}\n")
        return False

    def execute_quantum_task(self, prompt: str,
                             on_output: Optional[Callable[[str], None]] = None,
                             on_complete: Optional[Callable[[str], None]] = None):
        """Execute a high-stakes task using the autonomous AutoOrchestrator bridge."""
        if on_output:
            on_output("[QUANTUM] Engaging Autonomous MetaChain for deep tactical execution...\n")

        try:
            from shadowcypher.ai.auto_orchestrator import auto_orch
        except ImportError as e:
            logger.warning("ai", f"auto_orchestrator unavailable: {e}")
            if on_output:
                on_output("[QUANTUM] Autonomous mode unavailable — auto_orchestrator not loaded.\n")
            if on_complete:
                on_complete("UNAVAILABLE")
            return

        logger.info("ai", "QUANTUM_ORCHESTRATION: Delegating to AutoAgent foundation")
        auto_orch.execute_mission(
            query=prompt,
            callback=on_output,
            on_complete=on_complete
        )

    def unload(self):
        """Unload model from memory."""
        with self._lock:
            self._llm = None
            self._loaded = False
            self._loading = False
            self._backend = None
            self._model_name = None
        logger.info("ai", "Model unloaded")


# Global singleton
ai_engine = AIEngine()
