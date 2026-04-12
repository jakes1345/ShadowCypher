"""Activity logger — structured logging for all ShadowCypher operations."""

import json
import threading
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class Logger:
    """Enterprise-grade thread-safe logger with rotation and structured JSON output."""

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            log_dir = str(Path(__file__).resolve().parent.parent.parent / "logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / "activity.log"
        self.ops_log = self.log_dir / "operations.jsonl"
        
        self._lock = threading.Lock()
        self._current_mission_id: Optional[str] = None
        
        # 1. Apex Standard Logger (Human Readable)
        self._std_logger = logging.getLogger("ShadowCypher")
        self._std_logger.setLevel(logging.INFO)
        # Use RotatingFileHandler (Max 10MB per file, 5 backups)
        handler = RotatingFileHandler(self.log_file, maxBytes=10*1024*1024, backupCount=5)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
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

    def log(self, level: str, module: str, message: str, **extra):
        """Write a structured log entry."""
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
                pass # Fail silently on I/O issues in critical offensive paths

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
                return [json.loads(l) for l in lines[-count:]]
        except Exception:
            return []

    def close(self):
        """Cleanup logic."""
        pass


# Global singleton instance
logger = Logger()
