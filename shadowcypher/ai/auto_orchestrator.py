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

# Import AutoAgent Core (Wrapped to avoid crashes if missing dependencies)
try:
    from autoagent import MetaChain, Agent, Response
    from autoagent.registry import get_all_tools
    from autoagent.logger import MetaChainLogger
except ImportError as e:
    logger.error("autoagent", f"AutoAgent core foundation missing: {e}")
    MetaChain = None

class AutoOrchestrator:
    """The High-Intensity execution engine powered by AutoAgent MetaChain."""
    
    def __init__(self, model=None):
        from shadowcypher.ai.providers import provider_registry
        active = provider_registry.active
        self.model = model or (active.model if active else "gemma3")
        self.log_dir = PROJECT_ROOT / "logs" / "autoagent"
        os.makedirs(self.log_dir, exist_ok=True)

    async def run_mission_async(self, query: str, callback=None):
        """Execute a mission using the MetaChain synthesis loop."""
        if not MetaChain:
            return "ERROR: AutoAgent suite is not installed or dependencies missing."

        mission_log = self.log_dir / f"mission_{int(asyncio.get_event_loop().time())}.log"
        mc_logger = MetaChainLogger(mission_log)
        
        # 1. Initialize Apex Agent
        agent = Agent(
            name="ApexPredator",
            instructions="You are the ShadowCypher Supreme Agent. Use all tools to complete the mission. If tools fail, develop new ones.",
            model=self.model,
            functions=list(get_all_tools().values())
        )

        client = MetaChain(log_path=mc_logger)
        
        if callback: callback(f"[AUTOLIVE] Initializing MetaChain Session for: {query}")
        
        # 2. Execute Loop
        try:
            # We hook the logger to the ShadowBus to stream thoughts to the UI
            def _bus_relay(msg):
                bus.publish("mission_thought", msg, ui_thread=True)
            
            # Note: This is an architectural simplification for the bridge
            response = await client.run_async(agent, [{"role": "user", "content": query}])
            
            final_answer = response.messages[-1]["content"]
            return final_answer
        except Exception as e:
            return f"AUTON_CRASH: {str(e)}"

    def execute_mission(self, query: str, callback=None, on_complete=None):
        """Thread-safe synchronous entry point for the ShadowHub."""
        def _wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.run_mission_async(query, callback))
            if on_complete: on_complete(result)
        
        threading.Thread(target=_wrapper, daemon=True).start()

# Global Bridge
auto_orch = AutoOrchestrator()
