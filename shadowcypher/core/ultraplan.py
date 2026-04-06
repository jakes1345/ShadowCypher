"""UltraPlan — Autonomous engagement roadmap generator."""

import json
from shadowcypher.core.session import session
from shadowcypher.ai.engine import ai_engine
from shadowcypher.core.logger import logger


class UltraPlan:
    """Manages the autonomous multi-step roadmap for an engagement."""

    @staticmethod
    def generate_roadmap() -> list[dict]:
        """Generate a strategic roadmap for the current engagement."""
        if not session.current_project:
            return []

        p = session.current_project
        logger.info("ultraplan", f"Generating strategic roadmap for: {p.name}")
        
        prompt = f"""### PROJECT: {p.name}
TARGETS: {p.targets}
SCOPE: {p.scope}

As the lead Security Architect, generate a 5-step strategic roadmap for this penetration test.
Each step must have a 'phase', 'objective', and 'primary_tool'.
Phase options: Recon, Discovery, Exploitation, Post-Exploitation, Reporting.
Format strictly as JSON."""

        try:
            roadmap_json = ai_engine.generate_stream(
                prompt, 
                system_prompt="You are the UltraPlan Architect. Be strategic and professional."
            )
            # Find JSON and parse
            import re
            match = re.search(r'\[.*\]', roadmap_json, re.DOTALL)
            if match:
                roadmap = json.loads(match.group(0))
                # Store roadmap in project metadata for session persistence
                # Mock storage in reports for now
                p.roadmap = roadmap
                return roadmap
        except Exception as e:
            logger.error("ultraplan", f"Failed to generate roadmap: {e}")
            return []
        return []
