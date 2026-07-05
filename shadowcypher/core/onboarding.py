"""
First-run onboarding. On fresh install, generates `config.json` from the
template with a random hub_secret. Operator name is set via UI dialog on first
launch. Idempotent — safe to call every startup.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path


RESERVED_NAMES = {"shadow", "shadowcypher"}

def is_valid_name(name: str) -> tuple[bool, str | None]:
    """Validate operator name. Returns (is_valid, error_message)."""
    if not name:
        return False, "Name cannot be empty."

    if len(name) < 2:
        return False, "Name must be at least 2 characters."

    if len(name) > 32:
        return False, "Name must be 32 characters or less."

    if name.lower() in RESERVED_NAMES:
        return False, f"'{name}' is reserved and cannot be used."

    # Allow alphanumeric, spaces, hyphens, underscores
    if not all(c.isalnum() or c in " _-" for c in name):
        return False, "Name can only contain letters, numbers, spaces, hyphens, and underscores."

    return True, None


def ensure_user_config(project_root: Path, cfg_path: Path | None = None) -> Path:
    """Ensure config.json exists. Creates it from config.example.json if missing.

    ``cfg_path`` overrides where the active config is written (used on read-only
    deployments to redirect operator config to the user's home). Defaults to
    ``project_root/config.json`` for installed systems.

    Returns the path to the active config.json.
    Safe to call repeatedly — only writes if config.json does not exist.
    """
    cfg_path = Path(cfg_path) if cfg_path else project_root / "config.json"
    if cfg_path.exists():
        return cfg_path

    example = project_root / "config.example.json"
    if example.exists():
        data = json.loads(example.read_text())
    else:
        data = {}

    data.setdefault("irc", {})
    data["irc"]["hub_secret"] = secrets.token_hex(24)
    data["irc"]["bot_nick"] = data["irc"].get("bot_nick") or "ShadowSentinel"

    data.setdefault("identity", {})
    # Name is set via UI dialog, not auto-generated

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2))
    try:
        cfg_path.chmod(0o600)
    except Exception:
        pass
    return cfg_path


def set_nickname(project_root: Path, new_nick: str, cfg_path: Path | None = None) -> None:
    """Persist a new handle/nick to config.json."""
    cfg_path = ensure_user_config(project_root, cfg_path)
    data = json.loads(cfg_path.read_text())
    data.setdefault("identity", {})["handle"] = new_nick
    data.setdefault("irc", {})["bot_nick"] = data["irc"].get("bot_nick") or "ShadowSentinel"
    cfg_path.write_text(json.dumps(data, indent=2))
