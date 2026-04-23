"""
UltraPlan — The Apex Strategic Roadmap Generator.
Integrates with the ShadowHub mission-dispatch for high-fidelity planning.
"""

import json
import re
from shadowcypher.core.hub import hub
from shadowcypher.core.session import session
from shadowcypher.core.logger import logger

class UltraPlan:
    """Manages the multi-step engagement roadmap using Apex Swarm intelligence."""

    @staticmethod
    def generate_roadmap(use_ai: bool = True):
        """Generate a strategic roadmap for the current engagement."""
        project = session.current_project
        if not project:
            return "ERROR: No active session project found."

        logger.info("ultraplan", f"PLANNING_MISSION_FOR: {project.name}")

        if use_ai:
            # We dispatch a mission to the AI to generate the roadmap
            query = f"PROJECT: {project.name}\nTARGETS: {project.targets}\nSCOPE: {project.scope}\nGenerate a 5-step tactical roadmap (Recon, Discovery, Exploitation, Post-Ex, Reporting) in JSON format."
            
            # Using synchronous mission call for the plan generation logic
            result = hub.orchestrator.execute_query_sync(
                query,
                agent_role="commander",  # Force the commander role for planning
            )
            
            # Extract JSON array
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                try:
                    project.roadmap = json.loads(match.group(0))
                    return project.roadmap
                except: pass

        # Fallback to Template loop (Deterministic)
        return UltraPlan._build_default(project)

    @staticmethod
    def _build_default(project):
        target = project.targets[0] if project.targets else "TARGET_IP"
        template = [
            {"phase": "Recon", "objective": f"Enumerate {target}", "tool": "nmap", "status": "pending"},
            {"phase": "Discovery", "objective": "Vulnerability scanning", "tool": "nuclei", "status": "pending"},
            {"phase": "Exploitation", "objective": "Service breach", "tool": "msf", "status": "pending"},
            {"phase": "Maintenance", "objective": "Internal Pivot", "tool": "proxychains", "status": "pending"},
            {"phase": "Exfiltration", "objective": "Data extraction", "tool": "exfil", "status": "pending"}
        ]
        project.roadmap = template
        return template
