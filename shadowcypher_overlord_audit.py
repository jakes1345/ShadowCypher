#!/usr/bin/env python3
"""
ShadowCypher APEX_OVERLORD — The Ultimate Self-Healing Sentinel.
Ground-Up Integrity Guard for the Apex Predator Architecture.
"""

import os
import sys
import subprocess
import re
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SHADOWCYPHER_DIR = PROJECT_ROOT / "shadowcypher"
UI_DIR = SHADOWCYPHER_DIR / "ui"

# APEX_DEPENDENCIES: Python and System binaries
PYTHON_DEPS = {
    "psutil": "psutil",
    "requests": "requests",
    "PyGObject": "gi",
    "pycairo": "cairo"
}

SYSTEM_TOOLS = ["nmap", "nuclei", "sqlmap", "msfconsole", "mold"]

class ApexOverlord:
    def __init__(self):
        self.fixes = 0
        self.errors = 0

    def stabilize(self):
        print("\u26a1 [APEX_OVERLORD] INITIATING_GROUND_UP_STABILIZATION...")
        
        # 1. Dependency Hardening
        self._check_python_deps()
        self._check_system_tools()
        
        # 2. Structural Audit
        self._audit_syntax()
        self._audit_ui_integrity()
        self._purge_legacy_placeholders()

        print(f"\n[STABILIZATION_COMPLETE] ERRORS: {self.errors} | FIXES: {self.fixes}")

    def _check_python_deps(self):
        for pkg, imp in PYTHON_DEPS.items():
            if importlib.util.find_spec(imp) is None:
                print(f"[FIX] INSTALLING_PYTHON_DEP: {pkg}")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    self.fixes += 1
                except: self.errors += 1

    def _check_system_tools(self):
        for tool in SYSTEM_TOOLS:
            if subprocess.run(["which", tool], capture_output=True).returncode != 0:
                print(f"[CRITICAL] MISSING_SYSTEM_TOOL: {tool}")
                self.errors += 1

    def _audit_syntax(self):
        print("[APEX] AUDITING_SYNTAX...")
        for root, _, files in os.walk(SHADOWCYPHER_DIR):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    if subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True).returncode != 0:
                        print(f"[FAIL] SYNTAX_ERROR: {path}")
                        self.errors += 1

    def _audit_ui_integrity(self):
        print("[APEX] AUDITING_UI_STRUCTURE...")
        app_path = SHADOWCYPHER_DIR / "app.py"
        if not app_path.exists(): return

        with open(app_path, "r") as f: content = f.read()
        
        mapping = re.search(r"mapping = (\{.*?\})", content, re.DOTALL)
        if mapping:
            pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', mapping.group(1))
            for name, ref in pairs:
                mod_name = ref.split(".")[0]
                mod_path = UI_DIR / f"{mod_name}.py"
                if not mod_path.exists():
                    print(f"[REPAIR] SCAFFOLDING_MISSING_PAGE: {name}")
                    self._scaffold_apex_page(mod_path, ref.split(".")[1])

    def _scaffold_apex_page(self, path, class_name):
        content = f'''"""Apex Scaffolding — {class_name} V2.0"""
from shadowcypher.ui.base_page import BasePage

class {class_name}(BasePage):
    def __init__(self):
        super().__init__("{class_name.upper()}")
        self.log("APEX_AUTONOMOUS_SCAFFOLD: Module ready for logic injection.", "SYSTEM")
'''
        with open(path, "w") as f: f.write(content)
        self.fixes += 1

    def _purge_legacy_placeholders(self):
        print("[APEX] SCANNING_FOR_PLACEHOLDER_LEAKS...")
        for root, _, files in os.walk(SHADOWCYPHER_DIR):
            for file in files:
                if file.endswith(".py") or file.endswith(".css"):
                    path = os.path.join(root, file)
                    with open(path, "r") as f:
                        for i, line in enumerate(f):
                            if "# TODO" in line or "# FIXME" in line:
                                print(f"[WARN] LEAK: {os.path.basename(path)}:{i+1}")
                                self.errors += 1

if __name__ == "__main__":
    ApexOverlord().stabilize()
