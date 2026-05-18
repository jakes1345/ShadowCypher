"""Session and Project management — track engagements, targets, and scope."""

import os
import json
from datetime import datetime
from pathlib import Path
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger
from shadowcypher.core.reporting import Report


class Project:
    """A professional security engagement project."""

    def __init__(
        self,
        name: str,
        description: str = "",
        targets: list[str] = None,
        scope: list[str] = None,
    ):
        self.name = name
        self.description = description
        self.targets = targets or []
        self.scope = scope or []  # Subnets or specific IPs in-scope
        self.roadmap = []  # Multi-phase engagement plan (populated by UltraPlan)
        self.created = datetime.now().isoformat()
        self.last_accessed = datetime.now().isoformat()
        self.report = Report(project_name=name)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "targets": self.targets,
            "scope": self.scope,
            "created": self.created,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: dict):
        p = cls(
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            targets=data.get("targets", []),
            scope=data.get("scope", []),
        )
        p.created = data.get("created", p.created)
        p.last_accessed = data.get("last_accessed", p.last_accessed)
        return p


class SessionManager:
    """Manages multiple projects and the current active engagement."""

    def __init__(self):
        self.projects_dir = Path(config.project_root) / "projects"
        self.projects_dir.mkdir(exist_ok=True)
        self.current_project: Project = None
        self._load_last_session()

    def get_projects(self) -> list[str]:
        """Get list of active project names."""
        return [p.stem for p in self.projects_dir.glob("*.json")]

    def create_project(
        self,
        name: str,
        description: str = "",
        targets: list[str] = None,
        scope: list[str] = None,
    ) -> Project:
        """Create and switch to a new project."""
        p = Project(name, description, targets, scope)
        self.current_project = p
        self.save_current()
        logger.info("session", f"Created new project: {name}")
        return p

    def load_project(self, name: str) -> bool:
        """Load an existing project by name with tactical locking."""
        path = self.projects_dir / f"{name}.json"
        if not path.exists():
            return False
        
        from shadowcypher.core.utils import file_lock
        try:
            with file_lock(str(path)):
                with open(path, "r") as f:
                    data = json.load(f)
            self.current_project = Project.from_dict(data)
            self.current_project.last_accessed = datetime.now().isoformat()
            self.save_current()
            logger.info("session", f"Loaded project: {name}")
            return True
        except Exception as e:
            logger.error("session", f"Failed to load project {name}: {e}")
            return False

    def save_current(self):
        """Save active project state with atomic locking."""
        if not self.current_project:
            return
        path = self.projects_dir / f"{self.current_project.name}.json"
        
        from shadowcypher.core.utils import file_lock
        try:
            with file_lock(str(path)):
                with open(path, "w") as f:
                    json.dump(self.current_project.to_dict(), f, indent=4)

            # Save as last session
            last_session_path = self.projects_dir / "last_session.txt"
            with file_lock(str(last_session_path)):
                with open(last_session_path, "w") as f:
                    f.write(self.current_project.name)
        except Exception as e:
            logger.error("session", f"Project save failed: {e}")

    def _load_last_session(self):
        """Auto-load last project on startup."""
        path = self.projects_dir / "last_session.txt"
        if path.exists():
            name = path.read_text().strip()
            if self.load_project(name):
                return

        # Fallback if no valid project loaded
        if not list(self.projects_dir.glob("*.json")):
            self.create_project(
                "Shadow_Operation_Alpha",
                "Default operational scope.",
                ["127.0.0.1"],
                [],
            )

    def is_in_scope(self, target: str) -> bool:
        if not self.current_project or not self.current_project.scope:
            return True
        import ipaddress

        for s in self.current_project.scope:
            if target == s:
                return True
            try:
                net = ipaddress.ip_network(s, strict=False)
                addr = ipaddress.ip_address(target)
                if addr in net:
                    return True
            except ValueError:
                if target.endswith("." + s) or target == s:
                    return True
        return False


# Global singleton
session = SessionManager()
