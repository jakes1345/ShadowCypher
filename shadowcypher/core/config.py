"""Configuration management for ShadowCypher."""

import os
import json
from pathlib import Path


DEFAULT_CONFIG = {
    "ai": {
        "model_repo": "TheBloke/WhiteRabbitNeo-V1.5-7B-GGUF",
        "model_file": "whiterabbitneo-v1.5-7b.Q4_K_M.gguf",
        "n_ctx": 4096,
        "n_gpu_layers": 35,
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    "tools": {
        "nmap_path": "/usr/bin/nmap",
        "hydra_path": "/usr/bin/hydra",
        "john_path": "/usr/sbin/john",
        "hashcat_path": "/usr/bin/hashcat",
        "aircrack_path": "/usr/bin/aircrack-ng",
        "tcpdump_path": "/usr/bin/tcpdump",
    },
    "wordlists": {
        "default": "wordlists/rockyou.txt",
    },
    "ui": {
        "theme": "matrix",
        "window_width": 1400,
        "window_height": 900,
    },
}


class Config:
    """Load/save configuration from JSON file."""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.config_file = self.project_root / "config.json"
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Load config from disk, merging with defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                self._deep_merge(self.data, saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        """Persist current config to disk."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass

    def get(self, *keys, default=None):
        """Get a nested config value. e.g. config.get('ai', 'model_repo')"""
        d = self.data
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return default
        return d

    def set(self, *keys_and_value):
        """Set a nested config value. Last arg is the value."""
        if len(keys_and_value) < 2:
            return
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]
        d = self.data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    def _deep_merge(self, base: dict, override: dict):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def get_wordlist_path(self) -> str:
        wl = self.get("wordlists", "default", default="wordlists/rockyou.txt")
        full = self.project_root / wl
        if full.exists():
            return str(full)
        return wl

    def get_tool_path(self, tool: str) -> str:
        return self.get("tools", f"{tool}_path", default=tool)


# Global singleton
config = Config()
