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
    model: str = "gemma3"
    api_base: str = "http://localhost:11434"
    active_provider: str = "ollama"
    temperature: float = 0.3
    max_tokens: int = 4096
    n_ctx: int = 4096
    n_gpu_layers: int = 35

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
    server: str = "127.0.0.1"
    port: int = 8888
    channel: str = "#shadowcypher"
    use_ssl: bool = False
    auto_connect: bool = True
    sasl_user: str = "ShadowSentinel"
    sasl_pass: str = ""
    hub_secret: str = "SHADOW_MASTER_SECRET_2026"
    hub_ghost_port: int = 44444

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

    def set(self, *args: Any):
        """
        Enterprise-grade nested configuration updates.
        Usage: config.set("ai", "active_provider", "anthropic")
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
                return # Should not happen in strict Pydantic mode
        
        last_key = keys[-1]
        if hasattr(current, last_key):
            setattr(current, last_key, value)
        elif isinstance(current, dict):
            current[last_key] = value

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
config.load_from_json(config.project_root / "config.json")

# Import logger AFTER singleton for enterprise bootstrap
from shadowcypher.core.logger import logger
logger.info("config", f"ENTERPRISE_CORE_LOADED: {config.app_name} v{config.version}")
