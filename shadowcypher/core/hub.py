"""
ShadowHub — The Apex Predator Core.
Centralized Tactical Mission Control and Framework Unification.
"""

import os
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional
from shadowcypher.core.logger import logger
from shadowcypher.ai.orchestrator import AIOrchestrator

class ShadowHub:
    """The Singleton Brain of the ShadowCypher Suite."""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ShadowHub, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        
        self.orchestrator = AIOrchestrator()
        self.active_missions: Dict[str, dict] = {}
        self.system_status = "IDLE"
        self.start_time = datetime.now()
        
        # Tactical Telemetry
        self.telemetry = {
            "missions_total": 0,
            "vulns_found": 0,
            "shells_active": 0,
            "load_avg": 0.0
        }
        
        self._initialized = True
        
        # Apex Autonomous Intel Subscription
        from shadowcypher.core.bus import bus
        bus.subscribe("intel_found", self._on_intel_discovered)
        
        logger.info("hub", "SHADOWHUB_CORE: ENGAGED [AUTONOMOUS_SPECTRE_ACTIVE]")

    def _on_intel_discovered(self, intel):
        """Autonomous reaction to discovered vulnerabilities/IPs."""
        typ, val, ip = intel.get("type"), intel.get("value"), intel.get("ip")
        logger.info("hub", f"HUB_AUTONOMY: reacting to {typ}:{val} on {ip}")
        # Dispatch autonomous audit if critical
        if typ == "CVE":
            self.register_mission(f"Perform deep-dive audit and exploit validation for {val} on {ip}", agent_role="red_team")

    def register_mission(self, query: str, agent_role: str = "commander") -> str:
        """Centralized Mission Dispatch."""
        mission_id = self.orchestrator.execute_query_async(
            query,
            callback=self._on_mission_update,
            on_complete=self._on_mission_complete,
            agent_role=agent_role
        )
        
        self.active_missions[mission_id] = {
            "query": query,
            "status": "ENGAGED",
            "start_time": datetime.now(),
            "last_update": "",
            "progress": 0
        }
        self.telemetry["missions_total"] += 1
        return mission_id

    def _on_mission_update(self, update_text: str):
        """Global callback for all mission progress."""
        # This could be hooked into a GLib signal for UI updates
        logger.info("hub", f"MISSION_UPDATE: {update_text}")

    def _on_mission_complete(self, final_response: str):
        """Global callback for mission finalization."""
        logger.info("hub", "MISSION_FINALIZED: Results archived.")

    @property
    def uptime(self):
        delta = datetime.now() - self.start_time
        return str(delta).split(".")[0]

    def get_tactical_summary(self):
        """Return a grouped snapshot of the entire suite's state."""
        return {
            "uptime": self.uptime,
            "status": self.system_status,
            "active_missions": len(self.active_missions),
            "telemetry": self.telemetry
        }

# Global Singleton
hub = ShadowHub()
