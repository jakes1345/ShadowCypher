#!/usr/bin/env python3
"""
ShadowCypher Overlord — Startup integrity check.
Validates syntax and reports issues. Does NOT install packages or scaffold files.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SHADOWCYPHER_DIR = PROJECT_ROOT / "shadowcypher"


class ApexOverlord:
    def __init__(self):
        self.errors = 0

    def stabilize(self):
        print("\u26a1 [APEX_OVERLORD] INITIATING_GROUND_UP_STABILIZATION...")
        self._audit_syntax()
        self._audit_ui_integrity()

        if self.errors == 0:
            print(f"\n[STABILIZATION_COMPLETE] SYSTEM_FAULTS: 0 | STATUS: NOMINAL")
        else:
            print(f"\n[STABILIZATION_COMPLETE] SYSTEM_FAULTS: {self.errors}")

    def _audit_syntax(self):
        print("[APEX] AUDITING_SYNTAX...")
        for root, dirs, files in os.walk(SHADOWCYPHER_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path) as fh:
                        compile(fh.read(), path, "exec")
                except SyntaxError as e:
                    print(f"[FAIL] SYNTAX_ERROR: {path}:{e.lineno} — {e.msg}")
                    self.errors += 1

    def _audit_ui_integrity(self):
        """Check that all page modules referenced in app.py exist."""
        print("[APEX] AUDITING_UI_STRUCTURE...")
        import re
        app_path = SHADOWCYPHER_DIR / "app.py"
        ui_dir = SHADOWCYPHER_DIR / "ui"
        if not app_path.exists():
            return

        with open(app_path) as f:
            content = f.read()

        mapping = re.search(r"mapping = (\{.*?\})", content, re.DOTALL)
        if mapping:
            pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', mapping.group(1))
            for name, ref in pairs:
                mod_name = ref.split(".")[0]
                mod_path = ui_dir / f"{mod_name}.py"
                if not mod_path.exists():
                    print(f"[WARN] MISSING_PAGE: {name} → {mod_path.name}")
                    self.errors += 1


if __name__ == "__main__":
    ApexOverlord().stabilize()
