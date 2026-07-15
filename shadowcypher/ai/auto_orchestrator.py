"""
ShadowCypher Auto-Orchestrator — thin bridge to the agent fleet.

All dispatch goes through AgentRouter which handles:
  - MetaChain (autoagent) when installed
  - Direct provider call (Ollama / cloud) when not
  - Automatic cloud fallback when Ollama is offline

This module exists for backwards compatibility — new code should call
agent_router.dispatch_async() directly.
"""

from shadowcypher.core.bus import bus


class AutoOrchestrator:
    """Thin delegate — routes missions through the unified agent fleet."""

    def execute_mission(self, query: str, callback=None, on_complete=None,
                        agent_role: str = "security"):
        """Non-blocking mission dispatch. Resolves provider automatically."""
        from shadowcypher.ai.agents import agent_router

        def _relay_callback(msg):
            if callback:
                callback(msg)
            bus.publish("mission_thought", msg, ui_thread=True)

        agent_router.dispatch_async(
            query,
            callback=_relay_callback,
            on_complete=on_complete,
            force_agent=agent_role,
            use_ai_routing=False,
        )

    def execute_mission_sync(self, query: str, callback=None,
                             agent_role: str = "security", timeout: float = 300) -> str:
        """Blocking dispatch with timeout."""
        import queue
        q: queue.Queue[str] = queue.Queue()
        self.execute_mission(query, callback=callback,
                             on_complete=q.put, agent_role=agent_role)
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return f"[TIMEOUT] Mission exceeded {timeout:.0f}s"


# Global singleton
auto_orch = AutoOrchestrator()
