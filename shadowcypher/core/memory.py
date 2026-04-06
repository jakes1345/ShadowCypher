"""Dream System — Memory consolidation for autonomous security agents."""

import os
from datetime import datetime
from shadowcypher.core.session import session
from shadowcypher.ai.engine import ai_engine
from shadowcypher.core.logger import logger


class DreamSystem:
    """Consolidates project data into a durable MEMORY.md file."""

    DREAM_PROMPT = """Analyze the following security engagement logs and findings. 
Consolidate them into a clean, hierarchical 'MEMORY.md' document.
Focus on:
1. Identified Targets & Open Ports
2. Discovered Vulnerabilities
3. Potential Attack Vectors
4. Key Intelligence (LOOT)
5. Outstanding Tasks

Format purely as Markdown. Be precise and professional."""

    @staticmethod
    def dream():
        """Trigger a memory consolidation 'dream'."""
        if not session.current_project:
            return

        logger.info("memory", "AI is 'dreaming' to consolidate memory...")
        
        # Gather all current context
        p = session.current_project
        findings = [f.to_dict() for f in p.report.findings]
        
        raw_context = f"""PROJECT: {p.name}
TARGETS: {p.targets}
SCOPE: {p.scope}
FINDINGS: {findings}
"""
        
        try:
            # Generate the consolidated memory
            memory_md = ai_engine.generate_stream(
                f"### START RECON DATA:\n{raw_context}\n\n### CONSOLIDATE MEMORY:",
                system_prompt=DreamSystem.DREAM_PROMPT
            )
            
            # Save to MEMORY.md in the project workspace
            report_dir = session.current_project.report.reports_dir
            memory_path = os.path.join(report_dir, "MEMORY.md")
            
            with open(memory_path, "w") as f:
                f.write(f"Last Consolidated: {datetime.now().isoformat()}\n\n")
                f.write(memory_md)
                
            logger.info("memory", f"Memory consolidated to {memory_path}")
            return memory_path
            
        except Exception as e:
            logger.error("memory", f"Dreaming failed: {e}")
            return None

    @staticmethod
    def get_memory() -> str:
        """Fetch the latest consolidated memory for AI context."""
        if not session.current_project:
            return ""
            
        memory_path = os.path.join(session.current_project.report.reports_dir, "MEMORY.md")
        if os.path.exists(memory_path):
            with open(memory_path, "r") as f:
                return f.read()
        return ""
