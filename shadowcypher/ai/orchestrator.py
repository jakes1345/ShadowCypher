import json
import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

# Import AutoAgent Core — optional; guard so missing autoagent doesn't kill app boot
import sys
import os
from shadowcypher.core.config import config
sys.path.append(os.path.join(str(config.project_root), "ai_engine"))

_AUTOAGENT_AVAILABLE = False
MetaChain = None
Agent = None
registry = None
run_in_client = None
try:
    from autoagent import MetaChain, Agent
    from autoagent.registry import registry
    import autoagent.tools  # Trigger recursive tool registration
    from autoagent.main import run_in_client
    _AUTOAGENT_AVAILABLE = True
except Exception as _autoagent_err:
    logger.warn("ai", f"autoagent unavailable — high-intensity mode disabled: {_autoagent_err}")

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

        # Warm-boot the brain — only if autoagent is actually installed
        self.client = MetaChain() if _AUTOAGENT_AVAILABLE else None

    @property
    def tool_definitions(self) -> str:
        """Dynamically generates the tool manifest from the unified Registry."""
        info = self.registry.tools_info
        manifest = "Available Tactical Tools:\n"
        for name, tool in info.items():
            manifest += f"- {name}: {tool.docstring or 'No description provided.'}\n"
            manifest += f"  Args: {', '.join(tool.args)}\n"
        return manifest

    def execute_query_sync(self, query: str, agent_role: str = "commander", timeout: float = 180.0) -> str:
        """Executes a MetaChain query synchronously. Returns an error string on timeout instead of deadlocking the UI."""
        import queue
        res_queue = queue.Queue()

        self.execute_query_async(
            query,
            agent_role=agent_role,
            on_complete=lambda res: res_queue.put(res)
        )

        try:
            return res_queue.get(timeout=timeout)
        except queue.Empty:
            return f"[AI_TIMEOUT] Mission exceeded {timeout:.0f}s with no response."

    def execute_sync(self, query: str, agent_role: str = "commander", model: Optional[str] = None) -> str:
        """Alias for execute_query_sync for legacy compatibility."""
        return self.execute_query_sync(query, agent_role=agent_role)

    def execute_query_async(self, query: str, callback: Optional[Callable] = None,
                            on_complete: Optional[Callable] = None, agent_role: str = "commander",
                            images: Optional[List[str]] = None, intensity: Optional[str] = None,
                            history: Optional[List[dict]] = None):
        """Initiates an autonomous MetaChain mission with optional multimodal and history context."""
        if not _AUTOAGENT_AVAILABLE:
            msg = "[AI] autoagent not installed — high-intensity mode unavailable. Falling back via engine.generate()."
            if callback: callback(msg)
            if on_complete: on_complete(msg)
            return

        from shadowcypher.ai.agents import AGENT_FLEET

        spec = AGENT_FLEET.get(agent_role, AGENT_FLEET["commander"])
        
        print(f"[*] ORCHESTRATOR_TOOLS_AVAILABLE: {len(self.registry.tools)} core, {len(self.registry.plugin_tools)} plugins")
        aa_agent = Agent(
            name=spec.name,
            model=spec.model if spec.model != "shadowcypher-ai" else self.default_model,
            instructions=spec.system_prompt,
            functions=list(self.registry.tools.values()) + list(self.registry.plugin_tools.values()),
            tool_choice="required"
        )

        def _run():
            loop = None
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
                # Build message context
                messages = []
                if history:
                    messages.extend(history)
                
                user_msg = {"role": "user", "content": query}
                if images:
                    # Multimodal support (simplified for LiteLLM/Ollama)
                    user_msg["images"] = images
                
                messages.append(user_msg)
                
                async def _task():
                    response = await self.client.run_async(aa_agent, messages, debug=True)
                    return response

                response = loop.run_until_complete(_task())
                
                # Defensive extraction of final result
                if hasattr(response, "messages") and response.messages:
                    last_msg = response.messages[-1]
                    if isinstance(last_msg, dict):
                        final_res = last_msg.get("content", "MISSION_COMPLETE: Result synthesized.")
                    else:
                        final_res = getattr(last_msg, "content", "MISSION_COMPLETE: Result synthesized.")
                else:
                    final_res = "MISSION_COMPLETE: Result synthesized."

                if on_complete:
                    on_complete(final_res)
                
                log_update("MISSION_COMPLETE: Result synthesized.")
                
            except Exception as e:
                logger.error("orchestrator", f"META_CHAIN_FAULT: {e}")
                if on_complete:
                    on_complete(f"ERROR: {e}")
            finally:
                if loop is not None:
                    try:
                        loop.close()
                    except Exception:
                        pass

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
        except json.JSONDecodeError:
            # Simple cleanup for common LLM markdown errors
            cleaned = text.strip().strip("```json").strip("```")
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None

# Singleton Export
orchestrator = AIOrchestrator()
# For legacy compatibility in agents.py
TOOL_DEFINITIONS = orchestrator.tool_definitions
