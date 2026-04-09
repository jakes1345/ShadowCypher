"""ShadowCypher Stress-Test Verification Suite."""

import os
import sys
import subprocess
from shadowcypher.core.logger import logger

def smoke_test_modules():
    print("[*] PHASE 1: MODULE SMOKE TEST")
    modules = [
        "shadowcypher.modules.recon",
        "shadowcypher.modules.vuln_scanner",
        "shadowcypher.modules.phishing",
        "shadowcypher.modules.network",
        "shadowcypher.modules.exploit"
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"  [PASS] {mod} imported successfully.")
        except Exception as e:
            print(f"  [FAIL] {mod} failed: {e}")

def testing_phishing_artifacts():
    print("\n[*] PHASE 2: PHISHING ARTIFACT VERIFICATION")
    from shadowcypher.modules.phishing import Phishing
    
    # 1. PDF Test
    print("  [TEST] Generating Malicious PDF...")
    res = Phishing.generate_pdf("http://google.com")
    if "SUCCESS" in res and os.path.exists("payloads") and any(f.endswith(".pdf") for f in os.listdir("payloads")):
        print("    [PASS] PDF generated.")
    else:
        print(f"    [FAIL] PDF generation: {res}")

    # 2. HTML Smuggling Test
    print("  [TEST] Generating HTML Smuggling...")
    # Create a dummy file to smuggle
    with open("payloads/test.bin", "w") as f: f.write("test")
    res = Phishing.generate_html_smuggling("payloads/test.bin", "smuggled.iso")
    if "SUCCESS" in res and any("smuggle" in f for f in os.listdir("payloads")):
        print("    [PASS] HTML Smuggling generated.")
    else:
        print(f"    [FAIL] Smuggling: {res}")

def testing_ai_orchestrator():
    print("\n[*] PHASE 3: AI ORCHESTRATOR RESILIENCE TEST")
    from shadowcypher.ai.orchestrator import AIOrchestrator
    orch = AIOrchestrator()
    
    # Test JSON Repair
    print("  [TEST] Verifying Atomic JSON Repair (HALLUCINATION_FIX)...")
    bad_json = '{"tool": "list_project_tree", ""}'
    repaired = orch._fuzzy_json_repair(bad_json)
    if repaired and repaired.get("tool") == "list_project_tree" and "args" in repaired:
        print("    [PASS] Atomic repair success.")
    else:
        print(f"    [FAIL] Atomic repair failed: {repaired}")

    # Test Agentic Knowledge
    print("  [TEST] Verifying manifest awareness...")
    if os.path.exists("MANIFEST.md"):
        print("    [PASS] Manifest exists.")
    else:
        print("    [FAIL] Manifest missing.")

if __name__ == "__main__":
    print("--- SHADOWCYPHER STRESS TEST START ---")
    smoke_test_modules()
    testing_phishing_artifacts()
    testing_ai_orchestrator()
    print("\n--- STRESS TEST COMPLETE ---")
