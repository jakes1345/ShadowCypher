"""AI ShadowMemory — Persistent tactical memory powered by mem0 logic.
Provides long-term recall of operator preferences, mission history, and 
target-specific intelligence across all ShadowCypher components.
"""

import os

try:
    from mem0 import Memory
except ImportError:
    Memory = None

from shadowcypher.core.config import config
from shadowcypher.core.logger import logger

class ShadowMemory:
    """Enterprise-grade memory layer for ShadowSentinel."""
    
    def __init__(self):
        self.db_path = os.path.join(config.project_root, "data", "shadow_memory")
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            
        # Using a local Qdrant/SQLite hybrid for privacy and offline speed
        self.config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": self.db_path,
                }
            },
            "history_db_path": os.path.join(self.db_path, "history.db")
        }
        
        if Memory is None:
            logger.warning("ai", "MEM_OFFLINE: mem0 not installed — tactical memory disabled. Install with: pip install mem0ai")
            self.memory = None
            return

        try:
            self.memory = Memory.from_config(self.config)
            logger.info("ai", "SHADOW_MEMORY_ENGAGED: Tactical recall active.")
        except Exception as e:
            logger.error("ai", f"MEM_FAILURE: Could not initialize ShadowMemory - {e}")
            self.memory = None

    def store(self, content: str, user_id: str = "shadow_operator", metadata: dict = None):
        """Store a tactical fact or mission learning."""
        if not self.memory: return
        try:
            self.memory.add(content, user_id=user_id, metadata=metadata)
            logger.info("ai", f"MEM_INDEX: Recorded fact for operator {user_id}")
        except Exception as e:
            logger.error("ai", f"MEM_FAULT: Failed to record fact - {e}")

    def recall(self, query: str, user_id: str = "shadow_operator") -> list:
        """Recall relevant tactical historical context."""
        if not self.memory: return []
        try:
            results = self.memory.search(query, user_id=user_id)
            return results
        except Exception as e:
            logger.error("ai", f"MEM_SEARCH_FAULT: {e}")
            return []

    def get_user_profile(self, user_id: str = "shadow_operator"):
        """Fetch the full tactical profile of the operator."""
        if not self.memory: return {}
        try:
            return self.memory.get_all(user_id=user_id)
        except Exception as e:
            logger.error("ai", f"MEM_PROFILE_FAULT: {e}")
            return {}

# Global singleton
shadow_memory = ShadowMemory()
