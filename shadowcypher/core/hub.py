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
from shadowcypher.core.platform import platform_engine
from shadowcypher.ai.orchestrator import AIOrchestrator

try:
    from shadowcypher.core.nexus import nexus
except Exception:
    nexus = None  # type: ignore

try:
    from shadowcypher.ai.sisyphus import sisyphus
except Exception:
    sisyphus = None  # type: ignore

try:
    from shadowcypher.ai.guard import guard
except Exception:
    guard = None  # type: ignore

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
        self.loop = asyncio.get_event_loop()
        self.websocket = None
        retry_delay = 1
        while self._running:
            try:
                # APEX_HARDENING: Wait for the relay to generate a session token in the project root
                from shadowcypher.core.config import config
                token_path = os.path.join(str(config.project_root), ".relay_token")
                auth_token = ""
                
                # Poll for token file (Go relay creates this on startup)
                for _ in range(15):
                    if os.path.exists(token_path):
                        with open(token_path, "r") as f:
                            auth_token = f.read().strip()
                        break
                    await asyncio.sleep(0.5)

                async with websockets.connect(self.uri) as websocket:
                    self.websocket = websocket
                    
                    # APEX_HARDENING: Execute secure handshake
                    await websocket.send(json.dumps({
                        "type": "auth_handshake",
                        "auth_token": auth_token
                    }))
                    
                    self.connected = True
                    logger.info("hub", "RELAY_BRIDGE: Secure signal link established.")
                    retry_delay = 1 # Reset retry delay on success
                    async for message in websocket:
                        data = json.loads(message)
                        self._handle_signal(data)
            except Exception as e:
                self.connected = False
                self.websocket = None
                logger.debug("hub", f"RELAY_BRIDGE_DISCONNECT: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30) # Exponential backoff

    async def send(self, data: dict):
        """Injects a signal into the native Go-relay swarm."""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(data))
            except Exception:
                pass

    def _handle_signal(self, data: dict):
        typ = data.get("type")
        if typ == "status":
            peer_count = data.get("peer_count", 0)
            self.hub._update_telemetry("swarm_nodes", peer_count)
            # APEX_HARDENING: Truncate shadow_id to prevent leak of full handshake keys
            raw_id = data.get("text", "???")
            masked_id = f"{raw_id[:12]}..." if len(raw_id) > 16 else raw_id
            self.hub._update_telemetry("shadow_id", masked_id)
        elif typ == "mission_discovery":
            mid = data.get("mission_id")
            logger.info("hub", f"SWARM_INGEST: Discovered remote mission {mid}")
            # Register discovered mission in the Hub
            # (Logic for remote mission tracking)
        elif typ == "intel":
            bus.publish("intel_found", data.get("payload", {}))
        elif typ == "titan_event":
            mid = data.get("mission_id")
            event_type = data.get("text")
            logger.info("hub", f"TITAN_INGEST: [{event_type}] MissionID={mid}")
            bus.publish("module_log", {
                "module": "titan",
                "text": f"Sovereign Titan Event: {event_type} (MSN:{mid})",
                "level": "WARNING"
            })
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
            "threat_hits": 0,
            "last_incident": None,
            "swarm_nodes": 0,
            "shadow_id": "UNLINKED",
            "tor_up": False,
            "relay_up": False,
            "kg_nodes": 0,
            "guard_blocked": 0,
            "guard_scanned": 0,
        }
        
        self.autonomous_enabled: bool = False
        self._initialized: bool = True
        
        try:
            from shadowcypher.core.identity import identity
            if not identity.is_admin:
                logger.warning("hub", "SOVEREIGN_REJECTION: Machine not authorized as MASTER_NODE.")
        except Exception as e:
            logger.debug("hub", f"IDENTITY_CHECK_SKIP: {e}")

        self._wire_bus()
        self._engage_distributed_nodes()

        for name, fn in [
            ("relay_bridge",       self._start_relay_bridge),
            ("honeypot",           self._start_honeypot),
            ("nexus_relay",        self._start_nexus_relay),
            ("sisyphus",           self._start_sisyphus),
            ("ghost_orchestrator", self._start_ghost_orchestrator),
            ("training_range",     self._start_training_range),
            ("v2_services",        self._start_v2_services),
            ("health_monitor",     self._start_health_monitor),
        ]:
            try:
                fn()
            except Exception as e:
                logger.warning("hub", f"{name.upper()}_SKIP: {e}")

        logger.info("hub", "SHADOWHUB_ULTIMA: MISSION_CONTROL_ENGAGED")

    def _start_health_monitor(self) -> None:
        """Background health sentinel — polls Tor and relay liveness every 10 s."""
        import socket as _socket, time as _time
        def _monitor():
            while True:
                try:
                    with _socket.create_connection(("127.0.0.1", 9050), timeout=0.5):
                        self._update_telemetry("tor_up", True)
                except Exception:
                    self._update_telemetry("tor_up", False)
                relay_live = hasattr(self, "relay_bridge") and self.relay_bridge.connected
                self._update_telemetry("relay_up", relay_live)
                _time.sleep(10)
        threading.Thread(target=_monitor, daemon=True, name="HubHealthMonitor").start()

    def _start_training_range(self) -> None:
        import subprocess
        import socket as _socket
        self._training_range_proc = None
        try:
            with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', 5000)) == 0:
                    logger.info("hub", "TRAINING_RANGE: Already active on port 5000.")
                    return
            script_path = os.path.join(str(platform_engine.resolve_path("")), "launch_training_range.sh")
            if os.path.exists(script_path):
                self._training_range_proc = subprocess.Popen(
                    ["bash", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.info("hub", "TRAINING_RANGE: Auto-launching Citadel Lab...")
        except (OSError, ValueError) as e:
            logger.error("hub", f"TRAINING_RANGE_FAIL: {e}")

    def _start_ghost_orchestrator(self) -> None:
        """Launches the Ghost Orchestrator to manage remote Shadow Nodes."""
        from shadowcypher.core.ghost import ghost_orchestrator
        ghost_orchestrator.start()

    def _start_v2_services(self) -> None:
        """Boot all ShadowCypher v2.0 background services."""
        # CVE Feed — background NVD poll every 6h
        try:
            from shadowcypher.modules.cve_feed import cve_feed
            cve_feed.start_background_poll(
                interval_hours=6,
                on_new_cve=lambda cve: bus.publish("intel_found", {
                    "type": "CVE", "data": cve
                })
            )
            logger.info("hub", "CVE_FEED: Background NVD poll active (6h interval)")
        except Exception as e:
            logger.warning("hub", f"CVE_FEED_START_FAIL: {e}")

        # Knowledge Graph — subscribe to red team completions
        try:
            from shadowcypher.core.knowledge_graph import kg
            bus.subscribe("red_team_complete", lambda summary:
                bus.publish("module_log", {
                    "module": "kg", "text": summary, "level": "INFO"
                })
            )
            # Update telemetry with graph stats on any change
            self._update_telemetry("kg_nodes", kg.stats()["nodes"])
            logger.info("hub", f"KNOWLEDGE_GRAPH: {kg.stats()['nodes']} nodes loaded")
        except Exception as e:
            logger.warning("hub", f"KG_INIT_FAIL: {e}")

        # ShadowGuard — log stats to telemetry every 30 min
        if guard is not None:
            def _guard_telemetry():
                import time
                while True:
                    time.sleep(1800)
                    try:
                        stats = guard.get_stats()
                        self._update_telemetry("guard_blocked", stats.get("blocked", 0))
                        self._update_telemetry("guard_scanned", stats.get("scanned", 0))
                    except Exception:
                        pass
            threading.Thread(target=_guard_telemetry, daemon=True, name="GuardTelemetry").start()
            logger.info("hub", "SHADOWGUARD: Telemetry loop active")

    def _start_sisyphus(self) -> None:
        """Launches the Sisyphus integrity sentinel."""
        if sisyphus is not None:
            sisyphus.start()

    def _start_honeypot(self) -> None:
        """Launches the active defense honeypot."""
        from shadowcypher.core.security import StealthHoneypot
        self.honeypot = StealthHoneypot()
        def _on_threat(msg):
            self.telemetry["threat_hits"] += 1
            self.telemetry["last_incident"] = datetime.now(timezone.utc).isoformat()
            bus.publish("threat_detected", {"message": msg})
        self.honeypot.start_bait(on_threat=_on_threat)

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
        
    def is_tor_available(self) -> bool:
        """Checks if Tor SOCKS5 proxy is reachable on standard port."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 9050), timeout=1):
                return True
        except Exception:
            return False

    def dispatch_ghost_mission(self, target: str) -> str:
        """Initiates a zero-trace autonomous infiltration mission."""
        if not self.is_tor_available():
            logger.error("hub", "STEALTH_LOCK_FAIL: Tor Proxy not detected. Ghost mission blocked for protection.")
            return "ERROR: STEALTH_PLANE_OFFLINE"
        
        from shadowcypher.core.missions import ignite_ghost_operation
        ignite_ghost_operation(target)
        return "SUCCESS: GHOST_MISSION_IGNITED"

    def _start_nexus_relay(self) -> None:
        """Launches the Nexus Relay protocol bridge in the background."""
        try:
            from shadowcypher.core.nexus import nexus
            threading.Thread(target=nexus.start, name="ShadowNexus", daemon=True).start()
        except Exception as e:
            logger.error("hub", f"NEXUS_INIT_FAILURE: Handshake relay failed: {e}")

    def _update_telemetry(self, key: str, value: Any) -> None:
        """Updates internal state and broadcasts to the global data-bus."""
        self.telemetry[key] = value
        bus.publish("telemetry_update", {"key": key, "value": value})

    def _engage_distributed_nodes(self) -> None:
        logger.debug("hub", "DISTRIBUTED_NODES: No remote nodes configured at this time.")

    def _wire_bus(self) -> None:
        # Connect to tactical event channels
        bus.subscribe("intel_found", self._on_intel_discovered)
        bus.subscribe("sisyphus_report", self._on_health_report)
        bus.subscribe("pulse_anomaly", self._on_pulse_anomaly)
        bus.subscribe("red_team_complete", self._on_red_team_complete)

        # Bridge tactical events to the native Relay
        bus.subscribe("module_log", self._forward_to_relay)
        bus.subscribe("ghost_update", self._forward_to_relay)
        bus.subscribe("ghost_node_linked", self._on_ghost_linked)
        bus.subscribe("ghost_node_output", self._on_ghost_output)

    def _forward_to_relay(self, data: Dict[str, Any]) -> None:
        """Proxies internal bus events to the native Go-relay signal swarm."""
        if hasattr(self, 'relay_bridge') and self.relay_bridge.connected:
            if not hasattr(self.relay_bridge, 'loop'): return
            
            # PREVENT_ECHO: Don't forward messages that already came from the swarm
            mod = data.get("module", "")
            if mod.startswith("swarm/"):
                return

            # We wrap the bus data into a 'chat' type for the relay to broadcast
            # APEX_HARDENING: Only forward the 'text' to prevent full object/secret leak
            msg_text = data.get("text", "")
            if len(msg_text) > 512:
                msg_text = msg_text[:512] + "..."
                
            msg = {
                "type": "chat",
                "nick": "core",
                "text": msg_text
            }
            try:
                asyncio.run_coroutine_threadsafe(
                    self.relay_bridge.send(msg), 
                    self.relay_bridge.loop
                )
            except Exception: pass

    async def _on_intel_discovered(self, intel: Dict[str, Any]) -> None:
        # Fuses raw intel into the decision engine
        typ = intel.get("type", "UNKNOWN")
        ip = intel.get("ip", "LOCAL")
        logger.info("hub", f"INTEL_FUSION: Correlating {typ} for address {ip}")

        if self.autonomous_enabled and typ in ["CVE", "EXPLOITABLE_SERVICE"]:
            self.dispatch_mission(
                f"Perform deep-spectrum exploit validation for discovery {typ} on target {ip}.",
                agent_role="adversary"
            )

    def _on_red_team_complete(self, summary: str) -> None:
        """Handles red team mission completion — update KG telemetry."""
        try:
            from shadowcypher.core.knowledge_graph import kg
            stats = kg.stats()
            self._update_telemetry("kg_nodes", stats["nodes"])
            self._update_telemetry("kg_edges", stats["edges"])
            logger.info("hub", f"RED_TEAM_COMPLETE: {summary}")
        except Exception:
            pass

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

    def _on_ghost_linked(self, data: Dict[str, Any]) -> None:
        """Handles new Shadow Node check-ins."""
        nick = data.get("nick")
        host = data.get("host")
        logger.info("hub", f"GHOST_NODE_ACTIVE: {nick} has linked via signal plane {host}")
        bus.publish("module_log", {
            "module": "ghost",
            "text": f"Shadow Node '{nick}' established persistent link.",
            "level": "SUCCESS"
        })

    def _on_ghost_output(self, data: Dict[str, Any]) -> None:
        """Handles asynchronous output from remote Shadow Nodes."""
        nick = data.get("nick")
        output = data.get("output")
        # Route output to the telemetry stream
        bus.publish("module_log", {
            "module": f"ghost/{nick}",
            "text": output,
            "level": "INFO"
        })

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

    def is_stealth_ready(self) -> bool:
        """Verifies if the platform's stealth signatures are properly masked."""
        from shadowcypher.core.security import hardener
        # Check Identity + Proxy Status
        if not hardener.is_secure: return False
        # Check if we have an active relay link
        if not hasattr(self, 'relay_bridge') or not self.relay_bridge.connected:
            return False
        return True

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
        summary = {
            "uptime": self.uptime_formatted,
            "status": self.system_status,
            "active_missions": len(self.active_missions),
        }
        # Flatten telemetry for UI consumption
        summary.update(self.telemetry)
        return summary

# Global Singleton — instantiated lazily on first attribute access
# so importing hub.py in tests/CI doesn't spin up background threads.
class _LazyHub:
    _hub: Optional['ShadowHub'] = None

    def _get(self) -> 'ShadowHub':
        if self._hub is None:
            self._hub = ShadowHub()
        return self._hub

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

    def __repr__(self) -> str:
        return repr(self._get())

hub: Any = _LazyHub()
