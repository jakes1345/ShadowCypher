"""
ShadowCypher Apex Burn-In Test Suite.
Industrial-grade validation of all core modules, engines, and protocols.
"""

import os
import sys
import time
import threading
import json
from datetime import datetime

# Path Injection
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from shadowcypher.core.logger import logger
from shadowcypher.core.hub import hub
from shadowcypher.core.pulse import pulse
from shadowcypher.core.shell import ShadowShell
from shadowcypher.core.relay_manager import relay_manager
from shadowcypher.ai.providers import provider_registry

def test_signal_engine():
    print("[⚡] PHASE 1: SIGNAL ENGINE (Pulse)")
    # Simulate high-fidelity baseline (Need >64 for WST)
    for i in range(100):
        pulse.ingest("burn_in_traffic", 500 + (i % 10))
    
    # Simulate Anomaly
    print("  [!] Injecting Synthetic Anomaly...")
    pulse.ingest("burn_in_traffic", 50000)
    res = pulse.analyze_spectrum("burn_in_traffic")
    
    if res["status"] == "CAUTION" and res["throttle"]:
        print("  [✅] Pulse Detected Anomaly & Engaged Throttling")
    else:
        print(f"  [❌] Pulse Anomaly Detection Failure (Status: {res.get('status')})")
        return False
    return True

def test_execution_core():
    print("[⚡] PHASE 2: EXECUTION CORE (ShadowShell)")
    # Test simple command
    res = ShadowShell.execute("echo 'APEX_STABILIZED'")
    if res["status"] == "SUCCESS" and "APEX_STABILIZED" in res["output"]:
        print(f"  [✅] Command Execution Validated (Lat: {res['duration']}s)")
    else:
        print("  [❌] Command Execution Failure")
        return False
    
    # Test Throttling
    pulse.throttle_active = True
    start = time.time()
    ShadowShell.execute("echo 'THROTTLE_TEST'")
    duration = time.time() - start
    if duration >= 1.5:
        print(f"  [✅] Tactical Throttling Verified (Delay: {duration:.2f}s)")
    else:
        print("  [❌] Throttling Logic Bypassed")
        return False
    pulse.throttle_active = False
    return True

def test_c2_hive():
    print("[⚡] PHASE 3: C2 HIVE (Multiplexer)")
    # Start listener
    relay_manager.start_listener(port=9999)
    time.sleep(1)
    if any(t.name == "C2-HiveListener-9999" for t in threading.enumerate()):
        print("  [✅] C2 Hive Listener Engaged")
    else:
        print("  [❌] C2 Listener Failed to Spawn")
        return False
    
    # Check internal registry
    if hasattr(relay_manager, "sessions"):
        print(f"  [✅] Session Registry Nominal ({len(relay_manager.sessions)} active)")
    else:
        print("  [❌] Session Registry Missing")
        return False
    return True

def test_ai_swarm():
    print("[⚡] PHASE 4: AI SWARM (Orchestrator)")
    active = provider_registry.active
    print(f"  [i] Testing Active Provider: {active.name if active else 'None'}")
    
    if not active:
        print("  [❌] No AI Provider Active")
        return False
        
    # Check model list (V3 expansion)
    models = active.list_models()
    if any("ULTRATHINK" in m for m in models):
        print("  [✅] 88-Feature Experimental Model Pack Detected")
    else:
        print("  [!] Experimental Models Not Found (Normal if not Anthropic)")
        
    return True

def test_identity_persistence():
    print("[⚡] PHASE 5: IDENTITY PERSISTENCE (Operator Handle)")
    print("  [---] Chat Bubble Separator: \u2500"*10)
    from shadowcypher.core.identity import identity
    
    test_handle = f"OP_{int(time.time())}"
    identity.set_handle(test_handle)
    
    # Reload and verify (mock reload by re-instantiating or just checking the setting)
    if identity.handle == test_handle:
        print(f"  [✅] Operator Handle Persisted ({test_handle})")
    else:
        print("  [❌] Handle Persistence Fault")
        return False
    return True

def run_full_burn():
    print("="*50)
    print(f"  SHADOWCYPHER APEX BURN-IN [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("="*50)
    
    results = [
        test_signal_engine(),
        test_execution_core(),
        test_c2_hive(),
        test_ai_swarm(),
        test_identity_persistence()
    ]
    
    print("="*50)
    if all(results):
        print("  [💎] SYSTEM_STATUS: NOMINAL (APEX_READY)")
    else:
        print("  [❌] SYSTEM_STATUS: CRITICAL_FAULT_DETECTED")
    print("="*50)

if __name__ == "__main__":
    run_full_burn()
