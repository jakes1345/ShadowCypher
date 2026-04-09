"""
ShadowCypher Sisyphus Protocol — Integrity Monitor.
Monitors codebase health and reports issues. Does NOT auto-modify files.
"""

import os
import time
import threading
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus


class Sisyphus:
    """Background health monitor — reports problems, never auto-repairs code."""

    def __init__(self):
        from shadowcypher.core.config import config
        self.project_root = config.project_root
        self._active = False
        self._thread = None
        self._last_report = {}

    def start(self):
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("sisyphus", "SISYPHUS: Health monitor active (read-only)")

    def stop(self):
        self._active = False

    def _run_loop(self):
        # Initial delay — let the app fully load first
        time.sleep(10)

        while self._active:
            try:
                findings = self._health_check()
                if findings and findings != self._last_report:
                    self._last_report = findings
                    for category, items in findings.items():
                        if items:
                            self.log_status(
                                f"HEALTH [{category}]: {len(items)} issue(s)"
                            )
                time.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error("sisyphus", f"Health check error: {e}")
                time.sleep(60)

    def _health_check(self) -> dict:
        """Read-only scan — NEVER modifies files."""
        results = {
            "syntax_errors": [],
            "import_errors": [],
        }

        src_dir = os.path.join(str(self.project_root), "shadowcypher")
        if not os.path.isdir(src_dir):
            return results

        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path) as fh:
                        compile(fh.read(), path, "exec")
                except SyntaxError as e:
                    results["syntax_errors"].append(f"{f}:{e.lineno}")

        return results

    def log_status(self, msg):
        bus.publish("module_log", {
            "module": "sisyphus",
            "text": msg,
            "level": "WARN",
        })
        logger.info("sisyphus", msg)

    def get_health_report(self) -> dict:
        """On-demand health check for the UI."""
        return self._health_check()


# Global sentinel
sisyphus = Sisyphus()
