"""
ShadowHub — The Apex Predator Core Director.
Google-grade central orchestration for autonomous security missions and framework-wide telemetry.
"""

import os
import threading
import uuid
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Final
from dataclasses import dataclass, field

from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.ai.orchestrator import AIOrchestrator
from shadowcypher.core.platform import platform_engine
from shadowcypher.core.nexus import nexus

import asyncio
import json
import websockets

class RelayBridge:
    """Bridges the Go-based Swarm Relay to the Python Hub with robust retry logic."""
    def __init__(self, hub_instance):
        self.hub = hub_instance
        self.uri = f"ws://127.0.0.1:{os.getenv('SHADOW_PORT', '8888')}/ws"
        self._running = True
        self.connected = False

    async def connect(self):
        retry_delay = 1
        while self._running:
            try:
                async with websockets.connect(self.uri) as websocket:
                    self.connected = True
                    logger.info("hub", "RELAY_BRIDGE: Native signal link established.")
                    retry_delay = 1 # Reset retry delay on success
                    async for message in websocket:
                        data = json.loads(message)
                        self._handle_signal(data)
            except Exception as e:
                self.connected = False
                logger.debug("hub", f"RELAY_BRIDGE_DISCONNECT: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30) # Exponential backoff

    def _handle_signal(self, data: dict):
        typ = data.get("type")
        if typ == "status":
            peer_count = ord(data.get("target", '\x00'))
            self.hub._update_telemetry("swarm_nodes", peer_count)
            self.hub._update_telemetry("shadow_id", data.get("text"))
        elif typ == "mission_discovery":
            mid = data.get("mission_id")
            logger.info("hub", f"SWARM_INGEST: Discovered remote mission {mid}")
            # Register discovered mission in the Hub
            # (Logic for remote mission tracking)
        elif typ == "intel":
            bus.publish("intel_found", data.get("payload", {}))
        elif typ == "chat":
            # Forward swarm chat to tactical logs
            bus.publish("module_log", {
                "module": f"swarm/{data.get('nick', 'anon')}",
                "text": data.get("text", ""),
                "level": "INFO"
            })

@dataclass
class Mission:
    # Core state for tactical engagement
    id: str
    query: str
    role: str
    status: str = 'ENGAGED'
    progress: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update_msg: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration(self) -> str:
        """Calculates mission duration with high-fidelity formatting."""
        delta = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

class ShadowHub:
    # Directs the Citadel core and autonomous loops.
    SYSTEM_READY: Final[str] = 'OPERATIONAL'
    _instance: Optional['ShadowHub'] = None
    _lock: Final[threading.Lock] = threading.Lock()

    def __new__(cls) -> 'ShadowHub':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ShadowHub, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        
        self.orchestrator: AIOrchestrator = AIOrchestrator()
        self.active_missions: Dict[str, Mission] = {}
        self.system_status: str = self.SYSTEM_READY
        self.start_time: datetime = datetime.now(timezone.utc)
        
        # Butter-Smooth Pathing: Auto-Resolve Findings Directory
        self.findings_dir = platform_engine.resolve_path("findings")
        os.makedirs(self.findings_dir, exist_ok=True)
        
        self.telemetry: Dict[str, Any] = {
            "missions_total": 0,
            "missions_failed": 0,
            "vulns_critical": 0,
            "load_avg": 0.0,
            "last_incident": None
        }
        
        self.autonomous_enabled: bool = False
        self._initialized: bool = True
        self._wire_bus()
        self._engage_distributed_nodes() # sentinel/irc bridge
        self._start_relay_bridge()

        logger.info("hub", "SHADOWHUB_ULTIMA: MISSION_CONTROL_ENGAGED")
        self._start_nexus_relay()

    def _start_relay_bridge(self) -> None:
        """Launches the native Go-relay signal bridge."""
        self.relay_bridge = RelayBridge(self)
        def run_bridge():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.relay_bridge.connect())
        threading.Thread(target=run_bridge, name="HubRelayBridge", daemon=True).start()

    def register_arsenal(self):
        """Late-binding registration of the native tactical arsenal."""
        logger.info("hub", "ARMING_CORE: Initializing native tactical primitives...")
        import shadowcypher.modules.arsenal.base
        
    def is_stealth_ready(self) -> bool:
        """Verifies the Onion Circuit is active and operational."""
        import socket
        try:
            # Check for Tor SOCKS5 proxy on standard port (9050/9051)
            with socket.create_connection(("127.0.0.1", 9050), timeout=1):
                return True
        except:
            return False

    def dispatch_ghost_mission(self, target: str) -> str:
        """Initiates a zero-trace autonomous infiltration mission."""
        if not self.is_stealth_ready():
            logger.error("hub", "STEALTH_LOCK_FAIL: Tor Proxy not detected. Ghost mission blocked for protection.")
            return "ERROR: STEALTH_PLANE_OFFLINE"
        
        from shadowcypher.core.missions import ignite_ghost_operation
        ignite_ghost_operation(target)
        return "SUCCESS: GHOST_MISSION_IGNITED"

    def _start_nexus_relay(self) -> None:
        """Launches the Nexus Relay protocol bridge in the background."""
        try:
            import asyncio
            from shadowcypher.core.nexus import nexus
            
            def run_relay():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(nexus.start())
            
            threading.Thread(target=run_relay, name="ShadowNexus", daemon=True).start()
        except Exception as e:
            logger.error("hub", f"NEXUS_INIT_FAILURE: Handshake relay failed: {e}")

    def _update_telemetry(self, key: str, value: Any) -> None:
        """Updates internal state and broadcasts to the global data-bus."""
        self.telemetry[key] = value
        bus.publish("telemetry_update", {"key": key, "value": value})

    def _engage_distributed_nodes(self) -> None:
        """Initializes auxiliary bridges (IRC, Peer Handshakes)."""
        from shadowcypher.core.config import config as _cfg
        if _cfg.get("irc", "auto_connect", default=False):
            try:
                from shadowcypher.core.irc_bot import sentinel
                sentinel.start()
            except ImportError:
                logger.warning("hub", "SENTINEL_BRIDGE: Module not present in the strike-set.")
            except Exception as e:
                logger.error("hub", f"SENTINEL_FAILURE: Distributed handoff failed: {e}")

    def _wire_bus(self) -> None:
        # Connect to tactical event channels
        bus.subscribe("intel_found", self._on_intel_discovered)
        bus.subscribe("sisyphus_report", self._on_health_report)
        bus.subscribe("pulse_anomaly", self._on_pulse_anomaly)

    def _on_intel_discovered(self, intel: Dict[str, Any]) -> None:
        # Fuses raw intel into the decision engine
        typ = intel.get("type", "UNKNOWN")
        ip = intel.get("ip", "LOCAL")
        logger.info("hub", f"INTEL_FUSION: Correlating {typ} for address {ip}")
        
        if self.autonomous_enabled and typ in ["CVE", "EXPLOITABLE_SERVICE"]:
            self.dispatch_mission(
                f"Perform deep-spectrum exploit validation for discovery {typ} on target {ip}.",
                agent_role="red_team"
            )

    def _on_pulse_anomaly(self, event: Dict[str, Any]) -> None:
        # Handles defensive reactions to spectrum pulse jitter
        stream = event.get("stream", "unknown")
        logger.warning("hub", f"SIGINT_ESCALATION: Temporal variance critical in {stream}")
        
        if self.autonomous_enabled:
            self.dispatch_mission(
                f"SIGNAL_ANOMALY: High-variance detected in stream {stream}. "
                "Mitigate potential exposure and identify channel signatures.",
                agent_role="commander"
            )

    def _on_health_report(self, report: Dict[str, Any]) -> None:
        """Aggregates system health telemetry into the global status plane."""
        load = report.get("vitals", {}).get("cpu", 0.0)
        self._update_telemetry("load_avg", load)
        self.system_status = "STRESSED" if load > 90 else self.SYSTEM_READY

    def dispatch_shadow_mission(self, script_path: str) -> str:
        """Executes a native ShadowCypher mission script."""
        mission_id = f"GHOST-{uuid.uuid4().hex[:6].upper()}"
        logger.info("hub", f"INGESTING_SHADOW_MISSION: {os.path.basename(script_path)}")
        
        def _run():
            from shadowcypher.compiler.interpreter import ShadowInterpreter
            interp = ShadowInterpreter()
            with open(script_path, 'r') as f:
                interp.run(f.read())
            self._finalize_mission(mission_id, "SHADOW_MISSION_TERMINATED")

        threading.Thread(target=_run, daemon=True).start()
        return mission_id

    def dispatch_mission(self, query: str, agent_role: str = "commander") -> str:
        """Initiates a new autonomous mission.
        
        Args:
            query: The mission objective.
            agent_role: The designated strike persona.
            
        Returns:
            The generated unique mission ID.
        """
        mission_id = f"MSN-{uuid.uuid4().hex[:8].upper()}"
        mission = Mission(id=mission_id, query=query, role=agent_role)
        
        self.active_missions[mission_id] = mission
        self.telemetry["missions_total"] += 1
        
        self.orchestrator.execute_query_async(
            query,
            callback=lambda msg: self._update_mission(mission_id, msg),
            on_complete=lambda res: self._finalize_mission(mission_id, res),
            agent_role=agent_role
        )
        
        return mission_id

    def _update_mission(self, mid: str, msg: str) -> None:
        """Pushes real-time mission telemetry to the event bus."""
        if mid in self.active_missions:
            bus.publish("module_log", {
                "module": f"hub/{mid}",
                "text": msg,
                "level": "INFO"
            })

    def _finalize_mission(self, mid: str, result: str) -> None:
        """Archives a mission and logs the final tactical output."""
        if mid in self.active_missions:
            mission = self.active_missions[mid]
            mission.status = 'COMPLETE'
            mission.progress = 100
            mission.last_update_msg = result
            
            # Persist to Forensics Registry
            from shadowcypher.core.forensics import registry
            registry.register_mission(mid, mission.query, result, {
                "role": mission.role,
                "duration": mission.duration,
                "findings_count": len(mission.findings)
            })

            logger.info("hub", f"MISSION_ARCHIVED: {mid} operation terminated.")
            del self.active_missions[mid]

    @property
    def uptime_formatted(self) -> str:
        """Returns the formatted platform uptime."""
        delta = datetime.now(timezone.utc) - self.start_time
        return str(delta).split(".")[0]

    def get_tactical_summary(self) -> Dict[str, Any]:
        """Provides a telemetry snapshot for the Dashboard HUD.
        
        Returns:
            A dictionary containing active mission counts and system vitals.
        """
        return {
            "uptime": self.uptime_formatted,
            "status": self.system_status,
            "active_missions": len(self.active_missions),
            "telemetry": self.telemetry
        }

# Global Singleton Backbone
hub = ShadowHub()
