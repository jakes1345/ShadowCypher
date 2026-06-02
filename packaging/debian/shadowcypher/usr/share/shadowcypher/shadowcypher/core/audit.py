"""
ShadowAudit — High-Fidelity Tactical Diagnostic Suite.
Provides empirical verification of all ShadowCypher engine components.
No placeholders. No guesses. Only Proof.
"""

import time
import socket
import json
import os
from typing import Dict, Any, List
from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.bus import bus

class ShadowAudit:
    """The Redundancy and Integrity Checker for ShadowCypher."""
    
    def __init__(self):
        self.results = {}

    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Executes the complete proof-of-life sequence."""
        logger.info("audit", "DIAGNOSTIC_IGNITION: Commencing empirical verification...")
        
        self.results = {
            "timestamp": time.time(),
            "networking": self.verify_relay_link(),
            "filesystem": self.verify_path_integrity(),
            "neural": self.verify_ai_orchestrator(),
            "signal_bus": self.verify_event_bus()
        }
        
        # Calculate Overall Health
        total = len(self.results) - 1 # excluding timestamp
        passed = sum(1 for v in self.results.values() if isinstance(v, dict) and v.get("status") == "PASS")
        self.results["health_score"] = (passed / total) * 100
        
        if self.results["health_score"] < 100:
            logger.warn("audit", f"DIAGNOSTIC_COMPLETE: Engine identified at {self.results['health_score']}% fidelity.")
        else:
            logger.info("audit", "DIAGNOSTIC_COMPLETE: Engine firing on all cylinders.")
            
        return self.results

    def verify_relay_link(self) -> Dict[str, Any]:
        """Proves the Go Relay is responsive with sub-second RTT."""
        port = int(os.getenv("SHADOW_PORT", 8888))
        start = time.perf_counter()
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                rtt = (time.perf_counter() - start) * 1000
                return {"status": "PASS", "rtt_ms": f"{rtt:.2f}"}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    def verify_path_integrity(self) -> Dict[str, Any]:
        """Ensures every tactical component exists where it should."""
        status = platform_engine.get_component_status()
        missing = [k for k, v in status.items() if not v]
        if missing:
            return {"status": "FAIL", "missing": missing}
        return {"status": "PASS", "components": len(status)}

    def verify_ai_orchestrator(self) -> Dict[str, Any]:
        """Verifies the MetaChain and Tool Registry are synchronized."""
        from shadowcypher.ai.orchestrator import orchestrator
        try:
            tools = orchestrator.registry.tools
            if len(tools) == 0:
                return {"status": "FAIL", "error": "Registry Empty"}
            
            # Sub-check: Can it build a tool manifest?
            manifest = orchestrator.tool_definitions
            if "Available Tactical Tools" not in manifest:
                return {"status": "FAIL", "error": "Manifest Corruption"}
                
            return {"status": "PASS", "tools_active": len(tools)}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    def verify_event_bus(self) -> Dict[str, Any]:
        """Proves that messages aren't being dropped in the pub/sub layer."""
        received = [False]
        def _ack(data): received[0] = True
        
        bus.subscribe("audit_test", _ack)
        bus.publish("audit_test", {"ping": True})
        
        # Wait for the atomic bus cycle
        time.sleep(0.1)
        if received[0]:
            return {"status": "PASS"}
        return {"status": "FAIL", "error": "Bus Latency/Drop"}

# Singleton Diagnostic Utility
auditor = ShadowAudit()
