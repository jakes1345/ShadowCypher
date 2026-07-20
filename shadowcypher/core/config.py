"""
ShadowCypher Enterprise Configuration Engine.
Migrated to Pydantic for strict typing and environment variable support.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    model: str = "claude-haiku-4-5-20251001"
    api_base: str = "http://localhost:11434"
    active_provider: str = "ollama"
    temperature: float = 0.3
    max_tokens: int = 4096
    n_ctx: int = 4096
    n_gpu_layers: int = 35
    providers: Dict[str, Any] = {}
    model_file: str = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    model_repo: str = "bartowski/Llama-3.2-3B-Instruct-GGUF"


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
    sqlmap: str = "sqlmap"
    nikto: str = "nikto"
    nuclei: str = "nuclei"
    dalfox: str = "dalfox"
    amass: str = "amass"
    naabu: str = "naabu"
    katana: str = "katana"
    yara: str = "yara"
    rkhunter: str = "rkhunter"
    lynis: str = "lynis"
    fail2ban_client: str = "fail2ban-client"
    testssl: str = "testssl.sh"
    proxychains4: str = "proxychains4"
    cloudflared: str = "cloudflared"
    certbot: str = "certbot"


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


class StealthSettings(BaseSettings):
    proxy_url: str = ""  # e.g. "socks5://127.0.0.1:9050"
    relay_enabled: bool = False
    enforce_privacy: bool = False
    nexus_relay_url: str = "http://127.0.0.1:9999"


class Config(BaseSettings):
    """Apex Enterprise Configuration Model."""

    model_config = SettingsConfigDict(env_prefix="SC_", env_nested_delimiter="__", env_file=".env", extra="ignore")

    # Core metadata
    app_name: str = "ShadowCypher Apex"
    version: str = "3.0.0-enterprise"
    api_base_url: str = "https://api.shadowcypher.site"

    # Sub-settings
    ai: AISettings = AISettings()
    tools: ToolPaths = ToolPaths()
    irc: IRCSettings = IRCSettings()
    identity: IdentitySettings = IdentitySettings()
    stealth: StealthSettings = StealthSettings()

    # Path Resolution
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)

    def load_from_json(self, path: Path):
        """Backwards compatibility for legacy config.json."""
        if not path.exists():
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            import sys
            print(f"WARNING: Failed to load config from {path}: {e}", file=sys.stderr)
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
                    except Exception as e:
                        import sys
                        print(f"DEBUG: Failed to set nested config {k}.{sk}: {e}", file=sys.stderr)
            else:
                try:
                    setattr(self, k, v)
                except Exception as e:
                    import sys
                    print(f"DEBUG: Failed to set config {k}: {e}", file=sys.stderr)

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Enterprise-grade nested configuration retrieval.
        Supports: config.get("ai", "providers", "anthropic", "api_key")
        """
        current: Any = self
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

    def writable_config_path(self) -> Path:
        """Return a config.json path we can actually write to.

        Installed systems keep config next to the app in a writable project
        root. On the live ISO (and any read-only /opt deploy) that directory is
        root-owned — or overlay-mounted so ownership *looks* writable but writes
        still fail — so operator config lives under XDG config home instead,
        matching the ShadowOS rule that operator-private state belongs in the
        user's home, not shared app code. We probe with a real write rather
        than trusting os.access(), which is unreliable on overlayfs.
        """
        cache_key = str(self.project_root)
        cached = _writable_cfg_cache.get(cache_key)
        if cached is not None:
            return cached
        local = self.project_root / "config.json"
        if _path_is_writable(local):
            resolved = local
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
            resolved = Path(xdg) / "shadowcypher" / "config.json"
        _writable_cfg_cache[cache_key] = resolved
        return resolved

    def save_to_json(self, path: Optional[Path] = None) -> None:
        """Persist current config to disk."""
        path = Path(path) if path else self.writable_config_path()
        data: Dict[str, Any] = {}
        for key in ["app_name", "version"]:
            data[key] = getattr(self, key)
        for section_name in ["ai", "tools", "irc", "identity", "stealth"]:
            section = getattr(self, section_name)
            data[section_name] = section.model_dump() if hasattr(section, "model_dump") else dict(section)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
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

        current: Any = self
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
                return str(configured_path)

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


_writable_cfg_cache: Dict[str, Path] = {}


def _path_is_writable(target: Path) -> bool:
    """Probe the EXACT config file for append-writability.

    Testing the directory is not enough: on the live ISO a root-run import
    (apply-fixes runs as root) can leave a root-owned config.json in an
    otherwise-writable dir, which then blocks the operator. os.access() is also
    unreliable on overlayfs. So we attempt to open the real file and clean up
    if we created it, leaving onboarding to populate it properly.
    """
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        with open(target, "a"):
            pass
        if not existed:
            try:
                target.unlink()
            except OSError:
                pass
        return True
    except OSError:
        return False


# Global singleton
config = Config()
# 1. Baked defaults ship in the (possibly read-only) project root.
config.load_from_json(config.project_root / "config.json")
# 2. Per-user overrides live in a writable location (XDG on the live ISO).
try:
    from shadowcypher.core.onboarding import ensure_user_config

    _user_cfg = ensure_user_config(config.project_root, config.writable_config_path())
    config.load_from_json(_user_cfg)
except Exception as e:
    import sys
    print(f"WARNING: config startup failed: {e}", file=sys.stderr)

# Import logger AFTER singleton for enterprise bootstrap
from shadowcypher.core.logger import logger

logger.info("config", f"ENTERPRISE_CORE_LOADED: {config.app_name} v{config.version}")
