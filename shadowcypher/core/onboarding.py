"""
First-run onboarding. On fresh install, generates `config.json` from the
template with a random hub_secret and an auto-derived nickname. Idempotent —
safe to call every startup.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path

from shadowcypher.core.logger import logger


def _default_nick() -> str:
    base = (os.environ.get("USER") or os.environ.get("USERNAME") or "operator")
    base = "".join(c for c in base if c.isalnum() or c in "_-")[:12] or "operator"
    return f"{base}_{secrets.token_hex(2)}"


def ensure_user_config(project_root: Path) -> Path:
    """Ensure config.json exists. Creates it from config.example.json if missing.

    Returns the path to the active config.json.
    Safe to call repeatedly — only writes if config.json does not exist.
    """
    cfg_path = project_root / "config.json"
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
    if not data["identity"].get("handle"):
        data["identity"]["handle"] = _default_nick()

    cfg_path.write_text(json.dumps(data, indent=2))
    try:
        cfg_path.chmod(0o600)
    except Exception as e:
        logger.warning("onboarding", f"chmod config failed: {e}")
    return cfg_path


def set_nickname(project_root: Path, new_nick: str) -> None:
    """Persist a new handle/nick to config.json."""
    cfg_path = ensure_user_config(project_root)
    data = json.loads(cfg_path.read_text())
    data.setdefault("identity", {})["handle"] = new_nick
    data.setdefault("irc", {})["bot_nick"] = data["irc"].get("bot_nick") or "ShadowSentinel"
    cfg_path.write_text(json.dumps(data, indent=2))
