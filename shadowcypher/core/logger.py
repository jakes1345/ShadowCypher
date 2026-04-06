"""Activity logger — structured logging for all ShadowCypher operations."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class Logger:
    """Thread-safe activity logger with persistent file handles."""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = str(Path(__file__).resolve().parent.parent.parent / "logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "activity.log"
        self.ops_log = self.log_dir / "operations.jsonl"
        self._memory: list[dict] = []
        self._lock = threading.Lock()
        self._activity_fh = None
        self._ops_fh = None

    def _ensure_handles(self):
        """Lazily open file handles (once, not every write)."""
        if self._activity_fh is None:
            try:
                self._activity_fh = open(self.log_file, "a", buffering=1)
            except OSError:
                pass
        if self._ops_fh is None:
            try:
                self._ops_fh = open(self.ops_log, "a", buffering=1)
            except OSError:
                pass

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def log(self, level: str, module: str, message: str, **extra):
        """Write a log entry."""
        entry = {
            "timestamp": self._timestamp(),
            "level": level.upper(),
            "module": module,
            "message": message,
            **extra,
        }

        with self._lock:
            self._memory.append(entry)
            if len(self._memory) > 10000:
                self._memory = self._memory[-5000:]

            self._ensure_handles()

            line = f"[{entry['timestamp']}] [{level.upper()}] [{module}] {message}"
            if extra:
                line += f" | {json.dumps(extra)}"

            if self._activity_fh:
                try:
                    self._activity_fh.write(line + "\n")
                except OSError:
                    pass
            if self._ops_fh:
                try:
                    self._ops_fh.write(json.dumps(entry) + "\n")
                except OSError:
                    pass

    def info(self, module: str, message: str, **extra):
        self.log("INFO", module, message, **extra)

    def warn(self, module: str, message: str, **extra):
        self.log("WARN", module, message, **extra)

    def error(self, module: str, message: str, **extra):
        self.log("ERROR", module, message, **extra)

    def critical(self, module: str, message: str, **extra):
        self.log("CRITICAL", module, message, **extra)

    def get_recent(self, count: int = 100, module: str = None) -> list[dict]:
        """Get recent log entries, optionally filtered by module."""
        with self._lock:
            entries = self._memory
            if module:
                entries = [e for e in entries if e["module"] == module]
            return entries[-count:]

    def get_log_text(self, count: int = 200) -> str:
        """Get raw log text for display."""
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
            return "".join(lines[-count:])
        except FileNotFoundError:
            return "No log file found."

    def close(self):
        """Close file handles."""
        with self._lock:
            if self._activity_fh:
                self._activity_fh.close()
                self._activity_fh = None
            if self._ops_fh:
                self._ops_fh.close()
                self._ops_fh = None


# Global singleton
logger = Logger()
