#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // PRE-FLIGHT SYSTEM VERIFICATION
# ==============================================================================
# Executes a comprehensive health check and dependency audit for the platform.
# Validates core architecture, UI bindings, and module integrity.

import sys
import os
import time
import subprocess
import traceback
import logging

# 1. Environment Setup
sys.path.append(os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

def run_step(name, func):
    sys.stdout.write(f"[*] Executing: {name}... ")
    sys.stdout.flush()
    try:
        res = func()
        print(f"\033[1;32mOK\033[0m")
        return True, res
    except Exception as e:
        print(f"\033[1;31mFAILED\033[0m")
        logging.error(f"Validation failure in {name}: {e}")
        return False, None

# --- Verification Functions ---

def audit_dependencies():
    import pkg_resources
    with open("requirements.txt", "r") as f:
        requirements = pkg_resources.parse_requirements(f.read())
    
    missing = []
    for req in requirements:
        try:
            pkg_resources.require(str(req))
        except Exception:
            missing.append(str(req))
    
    if missing:
        raise Exception(f"Missing Dependencies: {missing}")
    return True

def verify_core_architecture():
    from shadowcypher.core.bus import bus
    from shadowcypher.core.config import config
    from shadowcypher.core.logger import logger
    from shadowcypher.core.forensics import registry
    from shadowcypher.core.nexus import nexus
    return True

def verify_module_registry():
    from shadowcypher.modules.ghost_hose import ghost_hose
    from shadowcypher.modules.recon import Recon
    from shadowcypher.modules.app_layer import Layer7
    from shadowcypher.modules.agent_relay import AgentRelay
    return True

def verify_ui_bindings():
    import gi
    gi.require_version("Gtk", "3.0")
    from shadowcypher.ui.support_page import SupportPage
    from shadowcypher.ui.war_map_page import WarMapPage
    return True

def run_diagnostic_probe():
    res = subprocess.run([sys.executable, "shadowcypher/scripts/signal_diagnostic.py"], capture_output=True, text=True)
    if res.returncode != 0:
        raise Exception("Diagnostic probe encountered a non-zero exit code.")
    return True

# --- Main Execution ---

def main():
    print("\n==============================================================================")
    print(" SHADOWCYPHER // SYSTEM HEALTH AUDIT")
    print("==============================================================================\n")
    
    steps = [
        ("Python Environment Dependency Audit", audit_dependencies),
        ("Core Architecture Initialization", verify_core_architecture),
        ("Internal Module Registry Verification", verify_module_registry),
        ("GTK3 User Interface Bindings", verify_ui_bindings),
        ("Subsystem Diagnostic Probe", run_diagnostic_probe)
    ]
    
    passed_count = 0
    for name, func in steps:
        success, _ = run_step(name, func)
        if success: passed_count += 1
        time.sleep(0.2)

    print("\n==============================================================================")
    score = (passed_count / len(steps)) * 100
    if score == 100:
        print(f" [SUCCESS] System Health Score: 100.0% | All subsystems operational.")
    else:
        print(f" [WARNING] System Health Score: {score:.1f}% | Instability detected.")
        sys.exit(1)
    print("==============================================================================\n")

if __name__ == "__main__":
    main()
