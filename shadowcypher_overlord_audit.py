#!/usr/bin/env python3
"""
ShadowCypher OVERLORD Self-Healing & Integrity Engine.
Autonomously discovers and repairs broken tactical infrastructure.
"""

import os
import sys
import subprocess
import re
import importlib.util

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SHADOWCYPHER_DIR = os.path.join(PROJECT_ROOT, "shadowcypher")
UI_DIR = os.path.join(SHADOWCYPHER_DIR, "ui")
MODULES_DIR = os.path.join(SHADOWCYPHER_DIR, "modules")

# MAPPING: PACKAGE_NAME -> IMPORT_NAME
REQUIRED_DEPS = {
    "psutil": "psutil",
    "requests": "requests",
    "pycairo": "cairo",
    "PyGObject": "gi",
}


class OverlordAudit:
    def __init__(self):
        self.fixes_applied = 0
        self.errors_found = 0

    def run_mission(self):
        print("\U0001f916 INITIATING_OVERLORD_SELF_HEALING_SEQUENCE...")
        self._audit_dependencies()
        self._audit_syntax()
        self._audit_ui_mappings()
        self._audit_placeholders()

        print(
            f"\n[MISSION_COMPLETE] ERRORS: {self.errors_found} | FIXES_APPLIED: {self.fixes_applied}"
        )
        if self.fixes_applied > 0:
            print("[INFO] SYSTEM_INTEGRITY_STABILIZED. REBOOT_SUGGESTED.")

    def _audit_dependencies(self):
        print("[STAGE 1] AUDITING_DEPENDENCY_INFRASTRUCTURE...")
        for pkg, imp in REQUIRED_DEPS.items():
            spec = importlib.util.find_spec(imp)
            if spec is None:
                print(f"[WARN] MISSING_CORE_DEP: {pkg}")
                self.errors_found += 1
                try:
                    # Only auto-fix in non-interactive if possible
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    self.fixes_applied += 1
                except (subprocess.CalledProcessError, OSError) as e:
                    print(f"[ERROR] INSTALL_FAILED: {pkg}: {e}")

    def _audit_syntax(self):
        print("[STAGE 2] AUDITING_SYNTAX_INTEGRITY...")
        # Strictly audit ONLY ShadowCypher tactical code
        for root, dirs, files in os.walk(SHADOWCYPHER_DIR):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    try:
                        subprocess.check_output(
                            [sys.executable, "-m", "py_compile", path],
                            stderr=subprocess.STDOUT,
                        )
                    except subprocess.CalledProcessError as e:
                        print(f"[CRITICAL] SYNTAX_ERROR_DETECTED: {path}")
                        self.errors_found += 1

    def _audit_ui_mappings(self):
        print("[STAGE 3] AUDITING_UI_MAPPING_PERSISTENCE...")
        app_path = os.path.join(SHADOWCYPHER_DIR, "app.py")
        if not os.path.exists(app_path):
            return

        with open(app_path, "r") as f:
            content = f.read()

        mapping_match = re.search(r"mapping = (\{.*?\})", content, re.DOTALL)
        if mapping_match:
            try:
                mapping_str = mapping_match.group(1).replace("\n", " ")
                pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', mapping_str)
                for name, ref in pairs:
                    mod_name = ref.split(".")[0]
                    mod_path = os.path.join(UI_DIR, f"{mod_name}.py")
                    if not os.path.exists(mod_path):
                        print(
                            f"[CRITICAL] ORPHANED_UI_PAGE: {name} (Missing {mod_path})"
                        )
                        self.errors_found += 1
                        self._scaffold_page(mod_path, mod_name, ref.split(".")[1])
            except Exception as e:
                print(f"[ERROR] MAPPING_PARSE_FAILURE: {e}")

    def _scaffold_page(self, path, mod_name, class_name):
        print(f"[FIX] SCAFFOLDING_MISSING_MISSION_MODULE: {class_name}")
        content = f'''"""ShadowCypher Autonomous Scaffolding — {class_name} V1.0"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from shadowcypher.ui.base_page import BasePage

class {class_name}(BasePage):
    def __init__(self):
        super().__init__("{mod_name.replace("_", " ").upper()} HUB")
        lbl = Gtk.Label(label="[SYSTEM] SECURE_MODULE_INITIALIZED: {class_name}\\nREPLACE_SKELETON_WITH_TACTICAL_LOGIC.")
        lbl.get_style_context().add_class("text-muted")
        self.pack_start(lbl, True, True, 0)
        self.show_all()
'''
        with open(path, "w") as f:
            f.write(content)
        self.fixes_applied += 1

    def _audit_placeholders(self):
        print("[STAGE 4] DETECTING_BANDAID_PLACEHOLDERS...")
        # Search ONLY ShadowCypher tactical code
        for root, dirs, files in os.walk(SHADOWCYPHER_DIR):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    with open(path, "r") as f:
                        for i, line in enumerate(f):
                            if (
                                "# TODO" in line
                                or "# FIXME" in line
                                or "placeholder" in line.lower()
                            ):
                                if "set_placeholder_text" in line:
                                    continue
                                print(
                                    f"[MISSING_LOGIC] {os.path.basename(path)}:{i + 1} >> {line.strip()}"
                                )
                                self.errors_found += 1


if __name__ == "__main__":
    audit = OverlordAudit()
    audit.run_mission()
