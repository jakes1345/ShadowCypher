"""
ShadowCypher AI Provider Registry — Multi-backend model orchestration.

Supports: Ollama (local), OpenAI, Anthropic Claude, Google Gemini,
OpenRouter, Groq, Mistral, Together AI, and any OpenAI-compatible endpoint.

All cloud providers use the OpenAI-compatible /v1/chat/completions API format.
API keys stored in config.json under "ai.providers.<name>.api_key" or via env vars.
"""

import os
import json
import threading
import urllib.request
import urllib.error
from typing import Optional, Callable
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


# ══════════════════════════════════════════════════════════════
# Provider Definitions
# ══════════════════════════════════════════════════════════════

PROVIDERS = {
    "ollama": {
        "name": "Ollama (Local)",
        "base_url": "http://127.0.0.1:11434",
        "api_format": "ollama",
        "env_key": None,
        "default_model": "gemma4",
        "free": True,
        "description": "Local GPU inference via Ollama. No API key needed.",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_format": "openai",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "free": False,
        "description": "GPT-4o, GPT-4-turbo, o1. Highest general intelligence.",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "api_format": "anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
        "free": False,
        "description": "Claude Sonnet/Opus. Best for complex reasoning and code.",
    },
    "google": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_format": "google",
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.5-pro",
        "free": False,
        "description": "Gemini Pro/Ultra. Strong multimodal capabilities.",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_format": "openai",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "anthropic/claude-sonnet-4-20250514",
        "free": False,
        "description": "Multi-model gateway. Access 200+ models with one key.",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_format": "openai",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "free": True,
        "description": "Ultra-fast inference. Free tier available.",
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "api_format": "openai",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-large-latest",
        "free": False,
        "description": "Mistral Large/Medium. Strong code and reasoning.",
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "api_format": "openai",
        "env_key": "TOGETHER_API_KEY",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "free": False,
        "description": "Open-source model hosting. Llama, Mixtral, DeepSeek.",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "api_format": "openai",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "free": False,
        "description": "DeepSeek V3/Coder. Excellent for code generation.",
    },
    "custom": {
        "name": "Custom Endpoint",
        "base_url": "",
        "api_format": "openai",
        "env_key": "CUSTOM_API_KEY",
        "default_model": "",
        "free": True,
        "description": "Any OpenAI-compatible API (vLLM, text-generation-inference, LM Studio, etc.)",
    },
}


class AIProvider:
    """Single AI provider connection — handles auth, requests, and streaming."""

    def __init__(self, provider_id: str, api_key: str = "", base_url: str = "",
                 model: str = ""):
        pdef = PROVIDERS.get(provider_id, PROVIDERS["custom"])
        self.id = provider_id
        self.name = pdef["name"]
        self.base_url = (base_url or pdef["base_url"]).rstrip("/")
        self.api_format = pdef["api_format"]
        self.model = model or pdef["default_model"]
        self.description = pdef["description"]

        # Key resolution: explicit > config.json > env var
        self.api_key = (
            api_key
            or config.get("ai", "providers", provider_id, "api_key", default="")
            or os.environ.get(pdef.get("env_key") or "", "")
        )

    @property
    def is_configured(self) -> bool:
        if self.api_format == "ollama":
            return True  # No key needed
        return bool(self.api_key)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_format == "anthropic":
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
        elif self.api_format == "google":
            pass  # Key goes in URL param
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.id == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/shadow_admin1345/ShadowCypher"
            headers["X-Title"] = "ShadowCypher"
        return headers

    def _build_request(self, messages: list, max_tokens: int, temperature: float,
                       stream: bool = False) -> tuple:
        """Build (url, payload) for the provider's API format."""

        if self.api_format == "ollama":
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                },
            }
            return url, payload

        if self.api_format == "anthropic":
            url = f"{self.base_url}/messages"
            system_msg = ""
            filtered = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    filtered.append(m)
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": filtered,
                "stream": stream,
            }
            if system_msg:
                payload["system"] = system_msg
            return url, payload

        if self.api_format == "google":
            url = (
                f"{self.base_url}/models/{self.model}:"
                f"{'streamGenerateContent' if stream else 'generateContent'}"
                f"?key={self.api_key}"
            )
            contents = []
            system_instruction = None
            for m in messages:
                if m["role"] == "system":
                    system_instruction = {"parts": [{"text": m["content"]}]}
                else:
                    role = "model" if m["role"] == "assistant" else "user"
                    contents.append({"role": role, "parts": [{"text": m["content"]}]})
            payload = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            }
            if system_instruction:
                payload["systemInstruction"] = system_instruction
            return url, payload

        # Default: OpenAI-compatible (openai, openrouter, groq, mistral, together, deepseek, custom)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        return url, payload

    def generate(self, prompt: str, system_prompt: str = "",
                 max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Synchronous generation."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        url, payload = self._build_request(messages, max_tokens, temperature, stream=False)

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            timeout = 300 if self.api_format != "ollama" else 300
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return self._extract_response(data)
        except Exception as e:
            logger.error("ai", f"[{self.name}] Generation error: {e}")
            return f"[Error] {self.name}: {e}"

    def generate_stream(self, prompt: str, system_prompt: str = "",
                        max_tokens: int = 2048, temperature: float = 0.7,
                        on_token: Callable[[str], None] = None) -> str:
        """Streaming generation with token callbacks."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        url, payload = self._build_request(messages, max_tokens, temperature, stream=True)
        full_text = []

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=self._headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    decoded = line.decode("utf-8").strip()
                    if not decoded:
                        continue

                    # SSE format: "data: {...}"
                    if decoded.startswith("data: "):
                        decoded = decoded[6:]
                    if decoded == "[DONE]":
                        break

                    try:
                        chunk = json.loads(decoded)
                        token = self._extract_stream_token(chunk)
                        if token:
                            full_text.append(token)
                            if on_token:
                                on_token(token)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            if on_token:
                on_token(f"\n[Error] {self.name}: {e}")

        return "".join(full_text)

    def _extract_response(self, data: dict) -> str:
        """Extract text from a non-streaming response."""
        if self.api_format == "ollama":
            return data.get("message", {}).get("content", "")
        if self.api_format == "anthropic":
            blocks = data.get("content", [])
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if self.api_format == "google":
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return ""
        # OpenAI-compatible
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def _extract_stream_token(self, chunk: dict) -> str:
        """Extract a single token from a streaming chunk."""
        if self.api_format == "ollama":
            return chunk.get("message", {}).get("content", "")
        if self.api_format == "anthropic":
            if chunk.get("type") == "content_block_delta":
                return chunk.get("delta", {}).get("text", "")
            return ""
        if self.api_format == "google":
            candidates = chunk.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return ""
        # OpenAI-compatible
        choices = chunk.get("choices", [])
        if choices:
            return choices[0].get("delta", {}).get("content", "")
        return ""

    def test_connection(self) -> dict:
        """Quick connectivity test — returns {ok: bool, detail: str}."""
        if self.api_format == "ollama":
            try:
                req = urllib.request.Request(f"{self.base_url}/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                return {"ok": True, "detail": f"Connected. {len(models)} models available."}
            except Exception as e:
                return {"ok": False, "detail": f"Ollama not running: {e}"}

        # For all others, do a minimal generation
        try:
            result = self.generate("Say OK", max_tokens=5, temperature=0)
            if result and not result.startswith("[Error]"):
                return {"ok": True, "detail": f"Connected. Model: {self.model}"}
            return {"ok": False, "detail": result}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def list_models(self) -> list:
        """List available models (Ollama only for now)."""
        if self.api_format == "ollama":
            url = f"{self.base_url}/api/tags"
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                if not models:
                    logger.warn("ai", f"[Ollama] No models found at {url}")
                return models
            except urllib.error.URLError as e:
                logger.error("ai", f"[Ollama] Connection failed at {url}: {e.reason}")
                return []
            except Exception as e:
                logger.error("ai", f"[Ollama] Unexpected failure: {e}")
                return []
        # For cloud providers, return known model list
        known = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o1-mini", "o3-mini"],
            "anthropic": [
                "claude-3-5-sonnet-latest", 
                "claude-3-5-haiku-latest", 
                "claude-3-opus-latest",
                "claude-3-5-sonnet-20241022",
                "claude-sonnet-4-20250514-ULTRATHINK", # Experimental Flag Simulation
                "claude-sonnet-4-20250514-ULTRAPLAN"
            ],
            "google": ["gemini-2.0-pro-exp", "gemini-2.5-pro", "gemini-2.0-flash-exp", "gemini-1.5-pro"],
            "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            "mistral": ["mistral-large-latest", "mistral-medium-latest", "codestral-latest"],
            "deepseek": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
        }
        return known.get(self.id, [self.model])


class ProviderRegistry:
    """Manages all configured AI providers and the active selection."""

    def __init__(self):
        self._providers: dict[str, AIProvider] = {}
        self._active_id: Optional[str] = None
        self._lock = threading.Lock()
        self._load_from_config()

    def _load_from_config(self):
        """Load provider configs from config.json."""
        saved = config.get("ai", "providers", default={})
        for pid, pconf in saved.items():
            if pid in PROVIDERS or pid == "custom":
                self._providers[pid] = AIProvider(
                    pid,
                    api_key=pconf.get("api_key", ""),
                    base_url=pconf.get("base_url", ""),
                    model=pconf.get("model", ""),
                )

        # Always ensure ollama is available
        if "ollama" not in self._providers:
            self._providers["ollama"] = AIProvider("ollama")

        # Set active provider
        active = config.get("ai", "active_provider", default="ollama")
        if active in self._providers:
            self._active_id = active
        else:
            self._active_id = "ollama"

    @property
    def active(self) -> Optional[AIProvider]:
        return self._providers.get(self._active_id)

    @property
    def active_id(self) -> str:
        return self._active_id or "ollama"

    def get(self, provider_id: str) -> Optional[AIProvider]:
        return self._providers.get(provider_id)

    def list_all(self) -> list[dict]:
        """List all providers with status info."""
        result = []
        for pid, pdef in PROVIDERS.items():
            provider = self._providers.get(pid)
            result.append({
                "id": pid,
                "name": pdef["name"],
                "description": pdef["description"],
                "free": pdef["free"],
                "configured": provider.is_configured if provider else False,
                "active": pid == self._active_id,
                "model": provider.model if provider else pdef["default_model"],
                "env_key": pdef.get("env_key", ""),
            })
        return result

    def add_provider(self, provider_id: str, api_key: str = "", base_url: str = "",
                     model: str = "") -> AIProvider:
        """Add or update a provider."""
        with self._lock:
            provider = AIProvider(provider_id, api_key=api_key, base_url=base_url,
                                  model=model)
            self._providers[provider_id] = provider

            # Save to config
            config.set("ai", "providers", provider_id, "api_key", api_key)
            if base_url:
                config.set("ai", "providers", provider_id, "base_url", base_url)
            if model:
                config.set("ai", "providers", provider_id, "model", model)

            logger.info("ai", f"Provider configured: {provider.name} ({provider.model})")
            return provider

    def remove_provider(self, provider_id: str):
        """Remove a provider (can't remove ollama)."""
        if provider_id == "ollama":
            return
        with self._lock:
            self._providers.pop(provider_id, None)
            if self._active_id == provider_id:
                self._active_id = "ollama"
                config.set("ai", "active_provider", "ollama")

    def switch(self, provider_id: str, model: str = "") -> bool:
        """Switch the active provider."""
        with self._lock:
            if provider_id not in self._providers:
                # Auto-create if it's a known provider
                if provider_id in PROVIDERS:
                    self._providers[provider_id] = AIProvider(provider_id)
                else:
                    return False

            provider = self._providers[provider_id]
            if model:
                provider.model = model
                config.set("ai", "providers", provider_id, "model", model)

            self._active_id = provider_id
            config.set("ai", "active_provider", provider_id)
            logger.info("ai", f"Switched to: {provider.name} / {provider.model}")
            return True

    def _get_identity_context(self) -> str:
        """Build identity-aware context for the system prompt."""
        ident = config.identity
        if not ident.handle:
            return ""
        return f" [OPERATOR_ID: {ident.handle} | ROLE: {ident.role.upper()}]"

    def generate(self, prompt: str, system_prompt: str = "",
                 max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Generate using the active provider with identity context."""
        provider = self.active
        if not provider:
            return "[Error] No AI provider configured."
        if not provider.is_configured:
            return f"[Error] {provider.name} needs an API key."

        # Inject Apex Identity
        ctx = self._get_identity_context()
        if ctx:
            system_prompt = f"{system_prompt}\n\nADMIN_IDENTITY_CONTEXT: {ctx}"
            
        return provider.generate(prompt, system_prompt, max_tokens, temperature)

    def generate_stream(self, prompt: str, system_prompt: str = "",
                        max_tokens: int = 2048, temperature: float = 0.7,
                        on_token: Callable[[str], None] = None) -> str:
        """Stream using the active provider with identity context."""
        provider = self.active
        if not provider:
            return ""
        if not provider.is_configured:
            return ""

        # Inject Apex Identity
        ctx = self._get_identity_context()
        if ctx:
            system_prompt = f"{system_prompt}\n\nADMIN_IDENTITY_CONTEXT: {ctx}"

        return provider.generate_stream(prompt, system_prompt, max_tokens, temperature,
                                        on_token=on_token)


# Global singleton
provider_registry = ProviderRegistry()
