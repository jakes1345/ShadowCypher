#!/usr/bin/env python3
"""
ShadowCypher Apex Overlord — Enterprise Bootstrap & Integrity Validator.
Google-grade pre-flight engine for system stabilization and dependency auditing.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Dict

# Force high-priority paths
PROJECT_ROOT = Path(__file__).resolve().parent
SHADOWCYPHER_DIR = PROJECT_ROOT / "shadowcypher"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"

class ApexOverlord:
    """
    Advanced System Validator — Ensures the ShadowCypher platform is in a 
    NOMINAL state before initiating offensive operations.
    """

    def __init__(self):
        self.faults = 0
        self.warnings = 0

    def stabilize(self):
        """Execute a full-spectrum system audit."""
        print("\033[1;36m[\u26a1] APEX_OVERLORD: INITIATING_SYSTEM_STABILIZATION_V3\033[0m")
        
        self._audit_dependencies()
        self._audit_codebase()
        self._audit_ui_integrity()
        self._audit_environment()

        self._print_final_report()

    def _audit_dependencies(self):
        """Cross-reference requirements.txt with the active Python environment."""
        print("[APEX] AUDITING_DEPENDENCIES...")
        if not REQUIREMENTS_FILE.exists():
            print("  [!] WARNING: requirements.txt not found. Skipping dependency check.")
            self.warnings += 1
            return

        # High-fidelity package-to-module mapping for enterprise auditing
        PKG_MAP = {
            "pygobject": "gi",
            "pycairo": "cairo",
            "scikit-learn": "sklearn",
            "pydantic-settings": "pydantic_settings",
            "cryptography": "cryptography",
            "psutil": "psutil"
        }

        with open(REQUIREMENTS_FILE, "r") as f:
            for line in f:
                raw_pkg = line.strip().split(">")[0].split("=")[0].split("[")[0].strip()
                if not raw_pkg or raw_pkg.startswith("#"): continue
                
                # Resolve the actual module name for verification
                module_name = PKG_MAP.get(raw_pkg.lower(), raw_pkg.lower().replace("-", "_"))
                
                spec = importlib.util.find_spec(module_name)
                if not spec:
                    print(f"  [FAIL] MISSING_PKG: {raw_pkg} (Module: {module_name})")
                    self.faults += 1

    def _audit_codebase(self):
        """Static analysis for syntax integrity across the entire project."""
        print("[APEX] AUDITING_CODEBASE_INTEGRITY...")
        for root, _, files in os.walk(SHADOWCYPHER_DIR):
            if "__pycache__" in root: continue
            for f in files:
                if not f.endswith(".py"): continue
                path = Path(root) / f
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        compile(fh.read(), str(path), "exec")
                except SyntaxError as e:
                    print(f"  [FAIL] SYNTAX_FAULT: {path.relative_to(PROJECT_ROOT)}:L{e.lineno}")
                    self.faults += 1
                except Exception:
                    pass

    def _audit_ui_integrity(self):
        """Validate UI component mapping and asset availability."""
        print("[APEX] AUDITING_UX_PIPELINE...")
        assets = [
            SHADOWCYPHER_DIR / "ui" / "index.css",
            PROJECT_ROOT / "native" / "icons" / "shadowcypher-256.png"
        ]
        for asset in assets:
            if not asset.exists():
                print(f"  [WARN] MISSING_ASSET: {asset.name}")
                self.warnings += 1

    def _audit_environment(self):
        """Check for critical environment configurations (X11/Wayland/Sudo)."""
        print("[APEX] AUDITING_SYSTEM_ENVIRONMENT...")
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            print("  [!] WARNING: No Display Server detected. UI components may fail.")
            self.warnings += 1

    def _print_final_report(self):
        print("\n\033[1;32m" + "═" * 50 + "\033[0m")
        status = "NOMINAL" if self.faults == 0 else "CRITICAL_FAULT"
        color = "\033[1;32m" if self.faults == 0 else "\033[1;31m"
        
        print(f"  STABILIZATION_REPORT:")
        print(f"  SYSTEM_STATUS: {color}{status}\033[0m")
        print(f"  FAULTS_DETECTED: {self.faults}")
        print(f"  WARNINGS_ISSUED: {self.warnings}")
        print("\033[1;32m" + "═" * 50 + "\033[0m\n")

if __name__ == "__main__":
    ApexOverlord().stabilize()
