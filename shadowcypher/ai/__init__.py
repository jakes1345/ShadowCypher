"""AI engine — offline Classic Brain + agent fleet + team-specific security prompts.

Public API:
    from shadowcypher.ai import brain          # offline conversational engine
    brain.respond(nick, message)               # main convo entry
    brain.audit_judge / audit_hunter / audit_architect  # unlock-gate heuristics
"""

from shadowcypher.ai.engine import ai_engine
from shadowcypher.ai.agents import agent_router
from shadowcypher.ai.classic_brain import brain

__all__ = ["ai_engine", "agent_router", "brain"]
