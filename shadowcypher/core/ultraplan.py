"""UltraPlan — Engagement roadmap generator.

Creates a structured pentest roadmap for the current project.
Works with or without AI — falls back to a deterministic template
when Ollama isn't running.
"""

import json
import re
from shadowcypher.core.session import session
from shadowcypher.core.logger import logger


# Standard pentest methodology roadmap (PTES-aligned)
_DEFAULT_ROADMAP = [
    {
        "phase": "Recon",
        "objective": "Enumerate targets, discover hosts, identify live services",
        "primary_tool": "nmap",
        "commands": ["nmap -sn {target}", "nmap -sV -p- {target}"],
        "status": "pending",
    },
    {
        "phase": "Discovery",
        "objective": "Identify vulnerabilities, misconfigurations, and weak points",
        "primary_tool": "nikto",
        "commands": ["nikto -h {target}", "nmap --script vuln {target}", "searchsploit {service}"],
        "status": "pending",
    },
    {
        "phase": "Exploitation",
        "objective": "Exploit discovered vulnerabilities to gain access",
        "primary_tool": "sqlmap",
        "commands": ["sqlmap -u {target} --batch", "hydra -l admin -P rockyou.txt {target} ssh"],
        "status": "pending",
    },
    {
        "phase": "Post-Exploitation",
        "objective": "Escalate privileges, pivot, extract data",
        "primary_tool": "manual",
        "commands": ["whoami", "id", "cat /etc/passwd", "netstat -tlnp"],
        "status": "pending",
    },
    {
        "phase": "Reporting",
        "objective": "Document findings, generate professional report",
        "primary_tool": "reporting_engine",
        "commands": [],
        "status": "pending",
    },
]


class UltraPlan:
    """Manages the multi-step engagement roadmap."""

    @staticmethod
    def generate_roadmap(use_ai: bool = True) -> list[dict]:
        """Generate a strategic roadmap for the current engagement.

        If AI is available and use_ai=True, asks the LLM to customize
        the roadmap based on targets and scope. Otherwise returns the
        standard PTES template with target substitution.
        """
        if not session.current_project:
            return []

        p = session.current_project
        logger.info("ultraplan", f"Generating roadmap for: {p.name}")

        # Try AI-enhanced roadmap if requested
        if use_ai:
            ai_roadmap = UltraPlan._generate_ai_roadmap(p)
            if ai_roadmap:
                p.roadmap = ai_roadmap
                return ai_roadmap

        # Fall back to deterministic template
        roadmap = UltraPlan._build_default_roadmap(p)
        p.roadmap = roadmap
        return roadmap

    @staticmethod
    def _build_default_roadmap(project) -> list[dict]:
        """Build a standard roadmap with target substitution."""
        import copy
        roadmap = copy.deepcopy(_DEFAULT_ROADMAP)
        target = project.targets[0] if project.targets else "TARGET"

        for step in roadmap:
            step["commands"] = [
                cmd.replace("{target}", target).replace("{service}", "unknown")
                for cmd in step["commands"]
            ]
        return roadmap

    @staticmethod
    def _generate_ai_roadmap(project) -> list[dict]:
        """Try to generate an AI-customized roadmap. Returns None on failure."""
        try:
            from shadowcypher.ai.engine import ai_engine
            if not ai_engine.is_loaded:
                return None

            prompt = f"""PROJECT: {project.name}
TARGETS: {project.targets}
SCOPE: {project.scope}

Generate a 5-step penetration testing roadmap as a JSON array.
Each step: {{"phase": "...", "objective": "...", "primary_tool": "...", "commands": [...], "status": "pending"}}
Phases: Recon, Discovery, Exploitation, Post-Exploitation, Reporting.
Use real commands (nmap, nikto, sqlmap, hydra, searchsploit).
Return ONLY the JSON array, no other text."""

            result = ai_engine.generate(
                prompt,
                system_prompt="You are a penetration testing strategist. Output only valid JSON.",
                max_tokens=1024,
            )

            # Extract JSON array from response
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                roadmap = json.loads(match.group(0))
                if isinstance(roadmap, list) and len(roadmap) >= 3:
                    return roadmap

        except Exception as e:
            logger.info("ultraplan", f"AI roadmap failed, using template: {e}")

        return None

    @staticmethod
    def advance_phase(phase_name: str):
        """Mark a roadmap phase as completed."""
        if not session.current_project or not hasattr(session.current_project, 'roadmap'):
            return
        for step in getattr(session.current_project, 'roadmap', []):
            if step.get("phase") == phase_name:
                step["status"] = "completed"
                logger.info("ultraplan", f"Phase completed: {phase_name}")
                return

    @staticmethod
    def get_current_phase() -> dict:
        """Get the first pending phase in the roadmap."""
        if not session.current_project or not hasattr(session.current_project, 'roadmap'):
            return {}
        for step in getattr(session.current_project, 'roadmap', []):
            if step.get("status") == "pending":
                return step
        return {}
