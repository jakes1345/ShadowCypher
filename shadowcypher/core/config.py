"""
ShadowCypher Enterprise Configuration Engine.
Migrated to Pydantic for strict typing and environment variable support.
"""

import os
import json
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure pydantic-settings is available
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback to standard Pydantic if settings plugin is missing
    from pydantic import BaseSettings
    SettingsConfigDict = dict

class AISettings(BaseSettings):
    model: str = "shadowcypher-ai"
    api_base: str = "http://localhost:11434"
    active_provider: str = "ollama"
    temperature: float = 0.3
    max_tokens: int = 4096
    n_ctx: int = 4096
    n_gpu_layers: int = 35
    providers: Dict[str, Any] = {}
    model_file: str = "shadowcypher-ai-q4km.gguf"
    model_repo: str = "jakes1345/shadowcypher-ai"

class ToolPaths(BaseSettings):
    nmap: str = "nmap"
    hydra: str = "hydra"
    john: str = "john"
    hashcat: str = "hashcat"
    aircrack: str = "aircrack-ng"
    tcpdump: str = "tcpdump"
    searchsploit: str = "searchsploit"
    responder: str = "Responder.py"
    msfconsole: str = "msfconsole"
    msfvenom: str = "msfvenom"
    whatweb: str = "whatweb"
    dirb: str = "dirb"
    ffuf: str = "ffuf"
    sherlock: str = "sherlock"
    whois: str = "whois"
    dig: str = "dig"
    openssl: str = "openssl"
    curl: str = "curl"

class IRCSettings(BaseSettings):
    server: str = "irc.libera.chat"
    port: int = 6697
    channel: str = "#shadowcypher"
    use_ssl: bool = True
    auto_connect: bool = False
    sasl_user: str = ""
    sasl_pass: str = ""
    hub_secret: str = ""
    hub_ghost_port: int = 44444
    bot_nick: str = "ShadowSentinel"
    bot_species: str = "apex_predator"
    stealth_mode: bool = False
    sovereign_enabled: bool = False
    sovereign_server: str = "127.0.0.1"
    sovereign_port: int = 6667

class IdentitySettings(BaseSettings):
    handle: str = ""
    role: str = "operator"
    admin_list: list[str] = []

class Config(BaseSettings):
    """Apex Enterprise Configuration Model."""
    model_config = SettingsConfigDict(
        env_prefix="SC_", 
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore"
    )

    # Core metadata
    app_name: str = "ShadowCypher Apex"
    version: str = "2.2.0-enterprise"
    
    # Sub-settings
    ai: AISettings = AISettings()
    tools: ToolPaths = ToolPaths()
    irc: IRCSettings = IRCSettings()
    identity: IdentitySettings = IdentitySettings()
    
    # Path Resolution
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)

    def load_from_json(self, path: Path):
        """Backwards compatibility for legacy config.json."""
        if not path.exists():
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception:
            return

        for k, v in data.items():
            if not hasattr(self, k):
                continue
            attr = getattr(self, k)
            if isinstance(attr, BaseSettings) and isinstance(v, dict):
                for sk, sv in v.items():
                    try:
                        if hasattr(attr, sk):
                            setattr(attr, sk, sv)
                    except Exception:
                        pass  # Skip fields that don't match the model
            else:
                try:
                    setattr(self, k, v)
                except Exception:
                    pass

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Enterprise-grade nested configuration retrieval.
        Supports: config.get("ai", "providers", "anthropic", "api_key")
        """
        current = self
        try:
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                elif hasattr(current, key):
                    current = getattr(current, key)
                else:
                    return default
                if current is None:
                    return default
            return current
        except Exception:
            return default

    def save_to_json(self, path: Optional[Path] = None) -> None:
        """Persist current config to disk."""
        path = path or (self.project_root / "config.json")
        data: Dict[str, Any] = {}
        for key in ["app_name", "version"]:
            data[key] = getattr(self, key)
        for section_name in ["ai", "tools", "irc", "identity"]:
            section = getattr(self, section_name)
            data[section_name] = section.model_dump() if hasattr(section, "model_dump") else dict(section)
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            # Import here to avoid circular at module load
            try:
                from shadowcypher.core.logger import logger
                logger.error("config", f"Failed to save config: {e}")
            except Exception:
                pass

    def set(self, *args: Any):
        """
        Enterprise-grade nested configuration updates.
        Usage: config.set("ai", "active_provider", "anthropic")
        Auto-persists to disk after each change.
        """
        if len(args) < 2:
            return

        keys = args[:-1]
        value = args[-1]

        current = self
        for key in keys[:-1]:
            if hasattr(current, key):
                current = getattr(current, key)
            elif isinstance(current, dict):
                current = current.setdefault(key, {})
            else:
                return

        last_key = keys[-1]
        if hasattr(current, last_key):
            setattr(current, last_key, value)
        elif isinstance(current, dict):
            current[last_key] = value

        self.save_to_json()

    def get_tool_path(self, tool_name: str) -> str:
        """
        Enterprise Tool Resolution Protocol:
        1. Environment Override (SC_TOOLS__<NAME>)
        2. Config Default
        3. Local tools/ Directory (Recursive)
        4. System PATH
        """
        # 1. Check Pydantic model (handles env and config overrides)
        tool_attr = tool_name.lower().replace("-", "_")
        if hasattr(self.tools, tool_attr):
            configured_path = getattr(self.tools, tool_attr)
            if os.path.isabs(configured_path) and os.path.exists(configured_path):
                return configured_path

        # 2. Deep Dive: Local project tools/ directory
        local_dir = self.project_root / "tools"
        if local_dir.exists():
            for root, _, files in os.walk(str(local_dir)):
                for f in files:
                    if f.lower() == tool_name.lower() or f.lower() == f"{tool_name.lower()}.sh":
                        return os.path.join(root, f)

        # 3. System Path
        sys_path = shutil.which(tool_name)
        if sys_path:
            return sys_path

        # 4. Final Fallback
        return getattr(self.tools, tool_attr, tool_name)

# Global singleton
config = Config()
try:
    from shadowcypher.core.onboarding import ensure_user_config
    ensure_user_config(config.project_root)
except Exception:
    pass
config.load_from_json(config.project_root / "config.json")

# Import logger AFTER singleton for enterprise bootstrap
from shadowcypher.core.logger import logger
logger.info("config", f"ENTERPRISE_CORE_LOADED: {config.app_name} v{config.version}")
