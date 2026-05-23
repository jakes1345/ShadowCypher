"""AI engine — offline Classic Brain + agent fleet + team-specific security prompts.

Public API:
    from shadowcypher.ai import brain          # offline conversational engine
    brain.respond(nick, message)               # main convo entry
    brain.audit_judge / audit_hunter / audit_architect  # unlock-gate heuristics
    from shadowcypher.ai import guard          # ShadowGuard prompt injection gate
    from shadowcypher.ai import red_team       # Autonomous recon→report agent
    from shadowcypher.ai import payload_mutator # AI-powered payload signature evasion
"""

from shadowcypher.ai.engine import ai_engine
from shadowcypher.ai.agents import agent_router
from shadowcypher.ai.classic_brain import brain
from shadowcypher.ai.guard import guard
from shadowcypher.ai.red_team_agent import red_team
from shadowcypher.ai.payload_mutator import payload_mutator

__all__ = ["ai_engine", "agent_router", "brain", "guard", "red_team", "payload_mutator"]
