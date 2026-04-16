"""
ShadowCypher Forensic Registry — The Global Thread-Aware Memory.
Consolidates all culprit data, fingerprints, and hardware LTC signatures
into a unified registry accessible by all offensive and defensive modules.
"""

import json
import os
import time
from typing import Dict, List, Optional
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class ForensicRegistry:
    def __init__(self):
        from shadowcypher.core.config import config
        self._forensic_dir = os.path.join(str(config.project_root), "forensics")
        self._registry_file = os.path.join(self._forensic_dir, "threat_registry.json")
        self._registry: Dict[str, dict] = {}
        os.makedirs(self._forensic_dir, exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self._registry_file):
            try:
                with open(self._registry_file, "r") as f:
                    self._registry = json.load(f)
            except Exception as e:
                logger.error("forensics", f"REGISTRY_LOAD_FAILED: {e}")

    def _save(self):
        try:
            with open(self._registry_file, "w") as f:
                json.dump(self._registry, f, indent=4)
        except Exception as e:
            logger.error("forensics", f"REGISTRY_SAVE_FAILED: {e}")

    def register_threat(self, handle: str, hostmask: str, metadata: dict):
        """Register a new threat across the global Citadel plane."""
        ts = time.time()
        threat_id = f"THREAT_{int(ts)}_{handle}"
        
        entry = {
            "id": threat_id,
            "handle": handle,
            "hostmask": hostmask,
            "timestamp": ts,
            "metadata": metadata,
            "risk_level": self._calculate_risk(metadata),
            "status": "QUARANTINED"
        }
        
        self._registry[hostmask] = entry
        self._save()
        
        # Broadcast to System Bus (Triggers Firewall & UI Alerts)
        bus.publish("forensic_update", entry)
        logger.warning("forensics", f"GLOBAL_THREAT_REGISTERED: {handle} at {hostmask}")

    def is_quarantined(self, hostmask: str) -> bool:
        return hostmask in self._registry

    def register_mission(self, mission_id: str, query: str, results: str, metadata: dict):
        """Archives a mission result into the permanent forensic registry."""
        archive_file = os.path.join(self._forensic_dir, f"mission_{mission_id}.json")
        entry = {
            "mission_id": mission_id,
            "query": query,
            "results": results,
            "timestamp": time.time(),
            "metadata": metadata
        }
        try:
            with open(archive_file, "w") as f:
                json.dump(entry, f, indent=4)
            logger.info("forensics", f"MISSION_ARCHIVED: {mission_id} saved to registry.")
            bus.publish("mission_archived", entry)
        except Exception as e:
            logger.error("forensics", f"MISSION_ARCHIVE_FAILED: {e}")

    def _calculate_risk(self, metadata: dict) -> str:
        # Complex heuristic calculation for mission risk
        score = 0
        if "UNWORTHY" in metadata.get("reason", ""): score += 50
        if "Bot" in metadata.get("fingerprint", ""): score += 30
        return "HIGH" if score > 70 else "MEDIUM"

    def get_all_threats(self) -> List[dict]:
        return list(self._registry.values())

# Global Instance
registry = ForensicRegistry()
