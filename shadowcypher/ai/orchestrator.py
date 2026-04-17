import json
import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

# Import AutoAgent Core
import sys
import os
from shadowcypher.core.config import config
sys.path.append(os.path.join(str(config.project_root), "ai_engine"))

from ai_engine.autoagent import MetaChain, Agent
from ai_engine.autoagent.registry import registry
from ai_engine.autoagent.main import run_in_client

class AIOrchestrator:
    """
    ShadowCypher AI Orchestrator — The Unified Autonomous Brain.
    Integrates HKUDS-2025 MetaChain for recursive task resolution.
    """
    def __init__(self, model="ollama/shadow-ai:latest"):
        self.default_model = model
        self.registry = registry
        self._active_missions = {}
        
        # Configure LiteLLM for local Ollama connectivity
        import litellm
        litellm.api_base = "http://localhost:11434"
        
        # Warm-boot the brain once during startup
        self.client = MetaChain()

    @property
    def tool_definitions(self) -> str:
        """Dynamically generates the tool manifest from the unified Registry."""
        info = self.registry.tools_info
        manifest = "Available Tactical Tools:\n"
        for name, tool in info.items():
            manifest += f"- {name}: {tool.docstring or 'No description provided.'}\n"
            manifest += f"  Args: {', '.join(tool.args)}\n"
        return manifest

    def execute_query_sync(self, query: str, agent_role: str = "commander") -> str:
        """Executes a MetaChain query synchronously and returns the final result string."""
        import queue
        res_queue = queue.Queue()
        
        self.execute_query_async(
            query,
            agent_role=agent_role,
            on_complete=lambda res: res_queue.put(res)
        )
        
        # Block until result
        return res_queue.get()

    def execute_query_async(self, query: str, callback: Optional[Callable] = None, 
                            on_complete: Optional[Callable] = None, agent_role: str = "commander"):
        """Initiates an autonomous MetaChain mission."""
        from shadowcypher.ai.agents import AGENT_FLEET
        
        spec = AGENT_FLEET.get(agent_role, AGENT_FLEET["commander"])
        
        # 1. Translate Spec to AutoAgent.Agent
        aa_agent = Agent(
            name=spec.name,
            model=spec.model if spec.model != "shadowcypher-ai" else self.default_model,
            instructions=spec.system_prompt,
            functions=list(self.registry.tools.values()),
            tool_choice="required"
        )

        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Setup custom logger for the Hub/Dashboard
                def log_update(msg):
                    if callback:
                        callback(msg)
                    bus.publish("module_log", {
                        "module": f"ai/{agent_role}", 
                        "text": msg, 
                        "level": "INFO"
                    })

                log_update(f"STRATEGIZING: Mission assigned to {spec.name}...")
                
                # Execute via MetaChain
                # Note: pass debug=True to get raw logs for diagnostic parity
                messages = [{"role": "user", "content": query}]
                
                async def _task():
                    response = await self.client.run_async(aa_agent, messages, debug=True)
                    return response

                response = loop.run_until_complete(_task())
                
                final_res = response.messages[-1]["content"]
                if on_complete:
                    on_complete(final_res)
                
                log_update("MISSION_COMPLETE: Result synthesized.")
                
            except Exception as e:
                logger.error("orchestrator", f"META_CHAIN_FAULT: {e}")
                if on_complete:
                    on_complete(f"ERROR: {e}")

        threading.Thread(target=_run, daemon=True, name=f"MetaChain-{agent_role}").start()

    def _execute_tool(self, name: str, args: dict, callback: Optional[Callable] = None) -> str:
        """Legacy tool bridge — now dynamically lookups in registry."""
        tools = self.registry.tools
        if name in tools:
            try:
                if callback:
                    callback(f"Executing {name} with args {args}...")
                res = tools[name](**args)
                return str(res)
            except Exception as e:
                return f"TOOL_ERROR: {e}"
        return f"UNKNOWN_TOOL: {name}"

    def _fuzzy_json_repair(self, text: str) -> Optional[Dict]:
        """Repair malformed JSON from models."""
        try:
            return json.loads(text)
        except:
            # Simple cleanup for common LLM markdown errors
            cleaned = text.strip().strip("```json").strip("```")
            try:
                return json.loads(cleaned)
            except:
                return None

# Singleton Export
orchestrator = AIOrchestrator()
# For legacy compatibility in agents.py
TOOL_DEFINITIONS = orchestrator.tool_definitions
