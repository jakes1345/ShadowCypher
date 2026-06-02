"""Core utilities — configuration, logging, async command execution, and input sanitization."""

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.knowledge_graph import kg

# Auto-apply Stealth v2 patches (domain fronting, JA3 spoof, tc jitter, geofencing)
try:
    import shadowcypher.core.stealth_v2  # noqa: F401 — side-effect only
except Exception:
    pass

__all__ = ["config", "logger", "runner", "kg"]
