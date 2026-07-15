"""
ShadowCypher Memento-Skills Engine — The Self-Evolving Artery.
Implements the 'Read-Execute-Reflect' cycle for autonomous tool refinement.
"""

import os
from pathlib import Path
from typing import Optional

from shadowcypher.core.logger import logger


class MementoEngine:
    """Manages the lifecycle of evolving agentic skills."""

    def __init__(self, skills_dir: str = "shadow_skills"):
        self.skills_dir = Path(os.getcwd()) / skills_dir
        self.skills_dir.mkdir(exist_ok=True)
        self.registry: dict = {}
        self._load_registry()

    def _load_registry(self):
        """Indexes all Markdown-based skill artifacts."""
        for skill_file in self.skills_dir.glob("*.md"):
            name = skill_file.stem
            self.registry[name] = {
                "path": str(skill_file),
                "last_refined": os.path.getmtime(skill_file)
            }
        logger.info("memento", f"MEMENTO_REGISTRY_SYNC: {len(self.registry)} skills indexed.")

    def get_skill(self, name: str) -> str:
        """Retrieves a specific skill's markdown brief."""
        if name in self.registry:
            with open(self.registry[name]["path"], "r") as f:
                return f.read()
        return ""

    def refine_skill(self, name: str, feedback: str, code_patch: Optional[str] = None):
        """
        The 'Reflect/Write' phase.
        Updates the skill artifact based on mission telemetry.
        """
        path = self.skills_dir / f"{name}.md"
        logger.info("memento", f"SKILL_REFINEMENT_LOGGED: {name} (Telemetry: {feedback[:32]}...)")

        if not path.exists():
            with open(path, "w") as f:
                header = f"# SKILL_ARTIFACT: {name.upper()}\n\n"
                f.write(header + f"## TELEMETRY_FEEDBACK\n- {feedback}\n")
        else:
            with open(path, "a") as f:
                f.write(f"\n### REFINEMENT_{int(os.path.getmtime(path))}\n- {feedback}\n")

        self._load_registry()

memento_engine = MementoEngine()
