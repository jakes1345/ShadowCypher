"""
ShadowHub — The Apex Predator Core Director.
Google-grade central orchestration for autonomous security missions and framework-wide telemetry.
"""

import os
import threading
import uuid
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.ai.orchestrator import AIOrchestrator

@dataclass
class Mission:
    """Enterprise-grade mission state tracker."""
    id: str
    query: str
    role: str
    status: str = "ENGAGED"
    progress: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update_msg: str = ""
    findings: List[Dict] = field(default_factory=list)
    
    @property
    def duration(self) -> str:
        delta = datetime.now(timezone.utc) - self.start_time
        return str(delta).split(".")[0]

class ShadowHub:
    """
    ShadowHub Singleton — The central directive brain of the ShadowCypher platform.
    Manages mission lifecycles, global telemetry, and autonomous intelligence loops.
    """
    
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
        
        # Core Subsystems
        self.orchestrator = AIOrchestrator()
        self.active_missions: Dict[str, Mission] = {}
        self.system_status = "OPERATIONAL"
        self.start_time = datetime.now(timezone.utc)
        
        # Global Telemetry (Google-grade Metrics)
        self.telemetry = {
            "missions_total": 0,
            "missions_failed": 0,
            "vulns_critical": 0,
            "load_avg": 0.0,
            "last_incident": None
        }
        
        self.autonomous_enabled = False
        
        # Self-Monitoring
        self._initialized = True
        self._subscribe_to_internal_events()
        # Start ShadowSentinel IRC Bridge (only if auto_connect is enabled)
        from shadowcypher.core.config import config as _cfg
        if _cfg.get("irc", "auto_connect", default=False):
            try:
                from shadowcypher.core.irc_bot import sentinel
                sentinel.start()
            except Exception as e:
                logger.error("hub", f"SENTINEL_FAILURE: Could not engage IRC bridge: {e}")

        logger.info("hub", "SHADOWHUB_CORE: ACTIVE [AUTONOMOUS_SPECTRE_V3]")

    def _subscribe_to_internal_events(self):
        """Register for high-level tactical events."""
        bus.subscribe("intel_found", self._on_intel_discovered)
        bus.subscribe("sisyphus_report", self._on_health_report)
        bus.subscribe("pulse_anomaly", self._on_pulse_anomaly)

    def _on_intel_discovered(self, intel: Dict[str, Any]):
        """Autonomous Intel Fusion Engine."""
        typ = intel.get("type", "UNKNOWN")
        ip = intel.get("ip", "LOCAL")
        logger.info("hub", f"INTEL_FUSION: Processing {typ} for {ip}...")
        
        # Proactive autonomous dispatch for critical discoveries (DISABLED BY DEFAULT)
        if self.autonomous_enabled and typ in ["CVE", "EXPLOITABLE_SERVICE"]:
            self.dispatch_mission(
                f"Perform deep-spectrum exploit validation for {typ} on {ip}.",
                role="red_team"
            )

    def _on_pulse_anomaly(self, event: Dict[str, Any]):
        """Reactive protocol for mathematical signal anomalies."""
        stream = event.get("stream", "unknown")
        score = event.get("score", 0.0)
        
        logger.warning("hub", f"REACTIVE_DISPATCH: Spectrum anomaly in {stream}. Escalating to AI Swarm.")
        
        # Dispatch a specialized SIGINT Deep Dive (DISABLED BY DEFAULT)
        if self.autonomous_enabled:
            self.dispatch_mission(
                f"SIGNAL_ANOMALY: High-variance transient detected in {stream}. "
                "Analyze current tactical output for covert channels or payload signatures. "
                "Identify the source and mitigate exposure.",
                role="commander"
            )

    def _on_health_report(self, report: Dict[str, Any]):
        """Sync internal load telemetry with Sisyphus health data."""
        self.telemetry["load_avg"] = report.get("vitals", {}).get("cpu", 0.0)
        if report.get("vitals", {}).get("cpu", 0) > 90:
            self.system_status = "STRESSED"
        else:
            self.system_status = "OPERATIONAL"

    def dispatch_mission(self, query: str, role: str = "commander") -> str:
        """Entry point for mission orchestration."""
        mission_id = f"MSN-{uuid.uuid4().hex[:8].upper()}"
        mission = Mission(id=mission_id, query=query, role=role)
        
        self.active_missions[mission_id] = mission
        self.telemetry["missions_total"] += 1
        
        # Async handoff to the AI Orchestrator
        self.orchestrator.execute_query_async(
            query,
            callback=lambda msg: self._update_mission(mission_id, msg),
            on_complete=lambda res: self._finalize_mission(mission_id, res),
            agent_role=role
        )
        
        return mission_id

    def _update_mission(self, mid: str, msg: str):
        """Real-time mission state synchronization."""
        if mid in self.active_missions:
            mission = self.active_missions[mid]
            mission.last_update_msg = msg
            # Propagate to UI via Bus
            bus.publish("module_log", {
                "module": f"hub/{mid}",
                "text": msg,
                "level": "INFO"
            })

    def _finalize_mission(self, mid: str, result: str):
        """Cleanly archive completed missions."""
        if mid in self.active_missions:
            mission = self.active_missions[mid]
            mission.status = "FALLOUT_PENDING" if "ERROR" in result else "ARCHIVED"
            logger.info("hub", f"MISSION_FINALIZED: {mid} → {mission.status}")
            # Keep in memory for UI until next cycle or handoff
            # (In a real enterprise app, this would hit a Redis/DB)

    @property
    def uptime_formatted(self) -> str:
        delta = datetime.now(timezone.utc) - self.start_time
        return str(delta).split(".")[0]

    def get_tactical_summary(self) -> Dict[str, Any]:
        """Snapshot for the Dashboard HUD."""
        return {
            "uptime": self.uptime_formatted,
            "status": self.system_status,
            "active_missions": len(self.active_missions),
            "active_targets": sum(
                1 for m in self.active_missions.values()
                if m.status == "ENGAGED"
            ),
            "cpu": self.telemetry.get("load_avg", 0),
            "memory_mb": self.telemetry.get("memory_mb", 0),
            "network_load": 0,
            "telemetry": self.telemetry
        }

# Global Singleton Backbone
hub = ShadowHub()
