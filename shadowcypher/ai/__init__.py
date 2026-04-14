"""AI engine — local LLM inference, agent fleet, and team-specific security prompts."""

from shadowcypher.ai.engine import ai_engine
from shadowcypher.ai.agents import agent_router

__all__ = ["ai_engine", "agent_router"]
