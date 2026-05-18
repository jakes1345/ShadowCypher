"""
ShadowContext — The All-Seeing Context Engine.
Allows AI Agents to read project files, system state, and mission data.
"""

import os
import mimetypes
from shadowcypher.core.logger import logger

class ShadowContext:
    """Provides deep architectural and mission context to the AI Swarm."""

    def __init__(self, workspace_root: str):
        self.root = workspace_root

    def list_project_tree(self, depth: int = 2) -> str:
        """Returns a summarized tree of the project for the AI's mental map."""
        tree = []
        for root, dirs, files in os.walk(self.root):
            level = root.replace(str(self.root), '').count(os.sep)
            if level >= depth: continue
            
            indent = ' ' * 4 * level
            tree.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                if f.endswith(('.py', '.md', '.json', '.sh', '.css')):
                    tree.append(f"{sub_indent}{f}")
        return "\n".join(tree)

    def read_file_content(self, relative_path: str) -> str:
        """Reads a specific file for the AI to analyze."""
        abs_path = os.path.realpath(os.path.join(self.root, relative_path))
        if not abs_path.startswith(os.path.realpath(self.root)):
            return "ERROR: Access denied — path traversal blocked."
        if not os.path.exists(abs_path):
            return f"ERROR: File {relative_path} not found."
        
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Truncate if too long (safety for context window)
                if len(content) > 10000:
                    return content[:10000] + "\n... [TRUNCATED]"
                return content
        except Exception as e:
            return f"ERROR: Could not read file: {str(e)}"

    def get_mission_context(self, mission_id: str) -> str:
        """Pulls logs and artifacts related to a specific mission."""
        log_path = os.path.join(self.root, "logs", f"mission_{mission_id}.log")
        if os.path.exists(log_path):
            return self.read_file_content(os.path.relpath(log_path, self.root))
        return "No specific logs found for this mission."

# Global context for the current workspace
from shadowcypher.core.config import config
context = ShadowContext(config.project_root)
