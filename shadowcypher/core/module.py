"""
BaseModule — The Ground-Up Foundation for all ShadowCypher tactical modules.
Centralizes execution, logging, and event-driven intelligence.
"""

# NOTE: hub is NOT imported here to avoid a circular import chain:
#   module.py → hub.py → ai/__init__ → red_team_agent → cve_feed → module.py
# Instead, hub is lazily imported inside methods that need it.
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner

class BaseModule:
    """
    Tactical Module Base.
    Ensures all modules use the Apex architecture consistently.
    """
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.active_tasks = []

    def execute(self, task_name: str, command: any, callback=None):
        """Unified command execution with mission awareness."""
        task_id = runner.execute_task(f"{self.module_name.upper()}_{task_name}", command, callback=callback)
        self.active_tasks.append(task_id)
        
        # Publish start event
        bus.publish("module_action", {
            "module": self.module_name,
            "action": task_name,
            "status": "STARTED",
            "task_id": task_id
        })
        
        return task_id

    def log(self, text: str, level: str = "INFO"):
        """Centralized logging to hub/telemetry."""
        logger.info(self.module_name, text)
        bus.publish("module_log", {"module": self.module_name, "text": text, "level": level})

    def dispatch_to_hub(self, mission: str):
        """Send a mission to the hub (lazy import avoids circular dep)."""
        from shadowcypher.core.hub import hub  # deferred
        return hub.dispatch_mission(mission)

    @staticmethod
    def get_tool_path(name: str) -> str:
        from shadowcypher.core.config import config
        return config.get_tool_path(name)
