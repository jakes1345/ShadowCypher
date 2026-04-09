"""Configuration management for ShadowCypher."""

import os
import json
from pathlib import Path


DEFAULT_CONFIG = {
    "ai": {
        "model": "gemma3",
        "n_ctx": 4096,
        "n_gpu_layers": 35,
        "api_base": "http://localhost:11434"
    },
    "tools": {
        "nmap_path": "nmap",
        "hydra_path": "hydra",
        "john_path": "john",
        "hashcat_path": "hashcat",
        "aircrack_path": "aircrack-ng",
        "tcpdump_path": "tcpdump",
        "searchsploit_path": "searchsploit",
        "responder_path": "Responder.py"
    },
    "wordlists": {
        "default": "wordlists/common.txt",
    },
}

class Config:
    """Advanced mission-aware configuration engine."""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.config_file = self.project_root / "config.json"
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                self._deep_merge(self.data, saved)
            except Exception as e:
                pass  # Logger not yet available during init

    def save(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception: pass

    def get(self, *keys, default=None):
        d = self.data
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return default
        return d

    def set(self, *keys_and_value):
        if len(keys_and_value) < 2: return
        keys, value = keys_and_value[:-1], keys_and_value[-1]
        d = self.data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def _deep_merge(self, base: dict, override: dict):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def get_tool_path(self, tool: str) -> str:
        """Deep Search Logic: Config -> tools/ -> system PATH."""
        # 1. Check config override
        path_key = f"{tool.lower().replace('-', '_')}_path"
        config_path = self.get("tools", path_key)
        
        # 2. Check Local project tools/ directory (Deep Level Autonomy)
        local_dir = self.project_root / "tools"
        if local_dir.exists():
            # Recursive check for the binary in tools/
            for root, dirs, files in os.walk(str(local_dir)):
                for f in files:
                    if f.lower() == tool.lower() or f.lower() == f"{tool.lower()}.sh":
                        return os.path.join(root, f)
                    if tool.lower() == "responder.py" and f.lower() == "responder.py":
                        return os.path.join(root, f)

        # 3. Check System PATH via 'which'
        import shutil
        sys_path = shutil.which(tool)
        if sys_path:
            return sys_path

        # 4. Final Fallback (Config default or raw name)
        return config_path or tool

# Global singleton
config = Config()

# Import logger AFTER singleton to avoid circular import
from shadowcypher.core.logger import logger
