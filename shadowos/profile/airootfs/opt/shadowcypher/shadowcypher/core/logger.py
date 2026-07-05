"""Activity logger — structured logging for all ShadowCypher operations."""

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


def _resolve_writable_log_dir(preferred: Optional[str]) -> Path:
    """Return the first writable log directory.

    On installed systems /opt/shadowcypher is writable and used directly.
    On the live ISO (and any read-only deploy) /opt is root-owned, so we
    fall back to per-user XDG state — matching the ShadowOS rule that
    operator-private state lives under the user's home, not shared app code.
    """
    candidates = []
    if preferred:
        candidates.append(Path(preferred))
    else:
        candidates.append(Path(__file__).resolve().parent.parent.parent / "logs")
    xdg_state = os.environ.get("XDG_STATE_HOME") or os.path.join(Path.home(), ".local", "state")
    candidates.append(Path(xdg_state) / "shadowcypher" / "logs")
    candidates.append(Path(tempfile.gettempdir()) / "shadowcypher-logs")

    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            # Probe the EXACT operation the handlers will perform: opening the
            # real log files for append. A dir can be writable while a stale,
            # root-owned activity.log (baked into a read-only image) still
            # blocks append — so a generic write-probe is not enough.
            for probe_name in ("activity.log", "operations.jsonl"):
                with open(cand / probe_name, "a"):
                    pass
            return cand
        except OSError:
            continue
    # Absolute last resort — the temp dir itself is essentially always writable.
    return Path(tempfile.gettempdir())


class Logger:
    """Enterprise-grade thread-safe logger with rotation and structured JSON output."""

    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = _resolve_writable_log_dir(log_dir)

        self.log_file = self.log_dir / "activity.log"
        self.ops_log = self.log_dir / "operations.jsonl"

        self._lock = threading.Lock()
        self._current_mission_id: Optional[str] = None

        # 1. Apex Standard Logger (Human Readable)
        self._std_logger = logging.getLogger("ShadowCypher")
        import os

        lvl_name = os.getenv("SHADOW_LOG_LEVEL", "INFO").upper()
        self._std_logger.setLevel(getattr(logging, lvl_name, logging.INFO))
        # Use RotatingFileHandler (Max 10MB per file, 5 backups)
        handler = RotatingFileHandler(self.log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        handler.setFormatter(formatter)
        self._std_logger.addHandler(handler)

        # 2. Add Stdout for Container/Cloud logging
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        self._std_logger.addHandler(console)

        # 3. Operations JSON Storage (Raw records)
        self._memory: list[dict] = []

    def set_mission_context(self, mission_id: Optional[str]):
        """Bind a mission ID to the current thread's logging context."""
        with self._lock:
            self._current_mission_id = mission_id

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _sanitize(self, text: Any) -> Any:
        """Scrubs identifiable information from strings and objects."""
        if isinstance(text, str):
            # Replace home directory with generic path
            import os

            home = os.path.expanduser("~")
            if home in text:
                text = text.replace(home, "/opt/shadowcypher")
            return text
        elif isinstance(text, dict):
            return {k: self._sanitize(v) for k, v in text.items()}
        elif isinstance(text, list):
            return [self._sanitize(i) for i in text]
        return text

    def log(self, level: str, module: str, message: str, **extra):
        """Write a structured log entry."""
        message = self._sanitize(message)
        extra = self._sanitize(extra)

        entry = {
            "timestamp": self._timestamp(),
            "level": level.upper(),
            "module": module,
            "mission_id": self._current_mission_id,
            "message": message,
            **extra,
        }

        with self._lock:
            # Persistent JSONL write
            try:
                with open(self.ops_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception:
                pass  # Fail silently on I/O issues in critical offensive paths

            # Human-readable stream log
            log_msg = f"[{module}] {message}"
            if extra:
                log_msg += f" | {json.dumps(extra)}"

            lvl_num = getattr(logging, level.upper(), logging.INFO)
            self._std_logger.log(lvl_num, log_msg)

    def info(self, module: str, message: str, **extra):
        self.log("INFO", module, message, **extra)

    def debug(self, module: str, message: str, **extra):
        """Standard debug-level logging."""
        self.log("DEBUG", module, message, **extra)

    def warn(self, module: str, message: str, **extra):
        self.log("WARNING", module, message, **extra)

    def warning(self, module: str, message: str, **extra):
        """Standard alias for warn()."""
        self.warn(module, message, **extra)

    def error(self, module: str, message: str, **extra):
        self.log("ERROR", module, message, **extra)

    def critical(self, module: str, message: str, **extra):
        self.log("CRITICAL", module, message, **extra)

    def get_recent_json(self, count: int = 100) -> list[dict]:
        """Read recent entries from the JSONL log file."""
        if not self.ops_log.exists():
            return []
        try:
            with open(self.ops_log, "r") as f:
                lines = f.readlines()
                return [json.loads(line) for line in lines[-count:]]
        except Exception:
            return []

    def close(self):
        """Cleanup logic."""
        pass


# Global singleton instance
logger = Logger()
