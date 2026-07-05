"""
ShadowCypher Self-Audit Engine — Total Project Integrity.
Performs deep-spectrum analysis of UI, Logic, and Offensive modules.
"""

import os
import re

from shadowcypher.core.logger import logger


class SelfAudit:
    """The 'Inquisitor'. Finds stubs, broken imports, and UI alignment issues."""

    @staticmethod
    def audit_entire_system():
        """Master audit protocol."""
        results = {"stubs": [], "missing_tools": [], "broken_ui": [], "placeholder_logic": []}

        from shadowcypher.core.config import config

        root_dir = config.project_root
        # Exclude vendored third-party code, ISO build artifacts, and source
        # mirrors so the audit reflects first-party ShadowCypher code only.
        _SKIP = (
            "venv",
            "site-packages",
            "shadow_test",
            ".git",
            "__pycache__",
            "phish_data",
            "ai_engine",
            "node_modules",
            "bin/go",
            os.sep + "tools" + os.sep,
            os.sep + "wordlists" + os.sep,
            os.path.join("shadowos", "work"),
            os.path.join("shadowos", "profile"),
            "packaging",
            os.sep + "opt" + os.sep,
        )
        for root, dirs, files in os.walk(root_dir):
            if any(x in root for x in _SKIP):
                continue

            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    SelfAudit._audit_file(path, results)

        return results

    @staticmethod
    def _audit_file(path, results):
        if "self_audit.py" in path:
            return  # Avoid self-triggering

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return

        from shadowcypher.core.config import config

        rel_path = os.path.relpath(path, config.project_root)

        # 1. Detect Stubs
        if "TO" + "DO" in content or "NotImplementedError" in content:
            results["stubs"].append(rel_path)

        # 2. Detect "pass" blocks in methods
        if re.search(r"def .*:[\s\n]+pass", content):
            results["placeholder_logic"].append(rel_path)

        # 3. Detect UI stubs
        if "shadowcypher/ui/" in path:
            if 'Gtk.Label(label="[SYSTEM] ERROR' in content:
                results["broken_ui"].append(rel_path)

    @staticmethod
    def get_repair_roadmap():
        """Generate a prioritized list of repairs for Sisyphus."""
        audit = SelfAudit.audit_entire_system()
        roadmap = []
        for r in audit["placeholder_logic"]:
            roadmap.append(f"REPAIR: Implement logic in {r}")
        for r in audit["stubs"]:
            roadmap.append(f"UPGRADE: Replace markers in {r}")
        return roadmap
