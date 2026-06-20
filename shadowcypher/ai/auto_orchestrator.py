"""
ShadowCypher Auto-Orchestrator — The MetaChain Synthesis Bridge.
Integrates the High-Spectrum AI Security Suite (AutoAgent) into ShadowCypher.
"""

import os
import sys
import asyncio
import threading
from typing import List, Optional
from pathlib import Path

# Fix paths for AutoAgent inclusion
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AI_ENGINE_PATH = PROJECT_ROOT / "ai_engine"
sys.path.append(str(AI_ENGINE_PATH))

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.core.stealth import stealth

# Import AutoAgent Core (Wrapped to avoid crashes if missing dependencies)
try:
    from autoagent import MetaChain, Agent, Response
    from autoagent.registry import registry
    from autoagent.logger import MetaChainLogger
except ImportError as e:
    logger.error("autoagent", f"AutoAgent core foundation missing: {e}")
    MetaChain = None

class AutoOrchestrator:
    """The High-Intensity execution engine powered by AutoAgent MetaChain."""
    
    def __init__(self, model=None):
        from shadowcypher.ai.providers import provider_registry
        active = provider_registry.active
        self.model = model or (active.model if active else "shadowcypher-ai")
        if active and active.id == "ollama" and not self.model.startswith("ollama/"):
            self.model = f"ollama/{self.model}"
        self.log_dir = PROJECT_ROOT / "logs" / "autoagent"
        os.makedirs(self.log_dir, exist_ok=True)
        stealth.engage()
        
        # Purge registry of noise and register tactical tools
        if MetaChain:
            import importlib
            from autoagent.registry import registry
            registry._registry["tools"] = {}
            registry._registry_info["tools"] = {}
            # Re-register only what we need
            import autoagent.tools.security_tools
            importlib.reload(autoagent.tools.security_tools)

    async def run_mission_async(self, query: str, callback=None):
        """Execute a mission using the MetaChain synthesis loop."""
        if not MetaChain:
            return "ERROR: AutoAgent suite is not installed or dependencies missing."

        mission_log = self.log_dir / f"mission_{int(asyncio.get_event_loop().time())}.log"
        mc_logger = MetaChainLogger(mission_log)
        
        # 1. Initialize the security-engagement agent. The operator is
        #    responsible for ensuring every target is authorised.
        agent = Agent(
            name="ShadowCypherAgent",
            instructions=(
                "You are the ShadowCypher security-engagement agent. You execute "
                "authorised penetration-testing and vulnerability-assessment tasks "
                "against targets the operator has explicit written permission to test.\n\n"
                "CRITICAL: You MUST ground every finding in real tool output. "
                "Do not fabricate data, simulate results, or guess. If a tool was "
                "not actually invoked, say so — do not invent output.\n\n"
                "Methodology:\n"
                "  1. RECON  — dns_history_recon, nmap: map the attack surface.\n"
                "  2. VULN   — nuclei_scan, ffuf_fuzz: enumerate misconfigurations and CVEs.\n"
                "  3. VERIFY — sqlmap_scan or equivalent: validate the finding.\n\n"
                "Report only what tools produced. Flag anything outside apparent "
                "engagement scope and pause for operator approval."
            ),
            model=self.model,
            functions=list(registry.tools.values()),
            tool_choice="required",
        )

        client = MetaChain(log_path=mc_logger)
        
        if callback:
            callback(f"[AUTOLIVE] Initializing MetaChain Session for: {query}")
        
        # 2. Execute Loop
        try:
            # We hook the logger to the ShadowBus to stream thoughts to the UI
            def _bus_relay(msg):
                bus.publish("mission_thought", msg, ui_thread=True)
            
            # Note: This is an architectural simplification for the bridge
            response = await client.run_async(agent, [{"role": "user", "content": query}], debug=True)
            
            final_answer = response.messages[-1]["content"] if response.messages else ""
            return final_answer
        except Exception as e:
            return f"AUTON_CRASH: {str(e)}"

    def execute_mission(self, query: str, callback=None, on_complete=None):
        """Thread-safe synchronous entry point for the ShadowHub."""
        def _wrapper():
            loop = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.run_mission_async(query, callback))
            except Exception as e:
                result = f"AUTON_CRASH: {e}"
            finally:
                if loop is not None:
                    try:
                        loop.close()
                    except Exception:
                        pass
            if on_complete:
                on_complete(result)

        threading.Thread(target=_wrapper, daemon=True).start()

# Global Bridge
auto_orch = AutoOrchestrator()
