"""
Mission Control — Enterprise Transaction Management for offensive operations.
Provides context managers to track missions and correlate logs across threads.
"""

import uuid
# Unused import removed to pass Ruff verification
from typing import Optional
from shadowcypher.core.logger import logger

class MissionContext:
    """Manages the lifecycle and traceability of a ShadowCypher Mission."""

    def __init__(self, mission_name: str, mission_id: Optional[str] = None):
        self.mission_name = mission_name
        self.mission_id = mission_id or f"MSN-{uuid.uuid4().hex[:8].upper()}"
        self.start_time = None

    def __enter__(self):
        # Bind this mission to the global logger for the current thread/context
        logger.set_mission_context(self.mission_id)
        logger.info("missions", f"MISSION_START: {self.mission_name}", 
                    mission_id=self.mission_id, status="STARTED")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "COMPLETED" if exc_type is None else "FAILED"
        if exc_type:
             logger.error("missions", f"MISSION_CRASH: {self.mission_name}", 
                          mission_id=self.mission_id, error=str(exc_val))
        
        logger.info("missions", f"MISSION_END: {self.mission_name}", 
                    mission_id=self.mission_id, status=status)
        
        # Unbind the mission ID
        logger.set_mission_context(None)

def track_mission(name: str):
    """Decorator for tracing functions as missions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with MissionContext(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
