"""AI engine — offline Classic Brain + agent fleet + team-specific security prompts.

Public API:
    from shadowcypher.ai import brain          # offline conversational engine
    brain.respond(nick, message)               # main convo entry
    brain.audit_judge / audit_hunter / audit_architect  # unlock-gate heuristics
    from shadowcypher.ai import guard          # ShadowGuard prompt injection gate
    from shadowcypher.ai import adversary      # Autonomous recon→report agent
    from shadowcypher.ai import variant_gen    # AI-powered signature variant generator
"""

from shadowcypher.ai.engine import ai_engine
from shadowcypher.ai.agents import agent_router
from shadowcypher.ai.classic_brain import brain
from shadowcypher.ai.guard import guard
from shadowcypher.ai.adversary_sim import adversary
from shadowcypher.ai.variant_generator import variant_gen

__all__ = ["ai_engine", "agent_router", "brain", "guard", "adversary", "variant_gen"]
