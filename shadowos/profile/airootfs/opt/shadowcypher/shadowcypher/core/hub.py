"""
ShadowHub — Central orchestrator for missions, telemetry, and background services.
"""

import asyncio
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Final, List, Optional

import websockets

from shadowcypher.ai.guard import guard
from shadowcypher.ai.orchestrator import AIOrchestrator
from shadowcypher.ai.sisyphus import sisyphus
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine


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
                # Wait for the Go relay to write its session token before connecting
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

                    await websocket.send(json.dumps({
                        "type": "auth_handshake",
                        "auth_token": auth_token
                    }))

                    self.connected = True
                    logger.info("hub", "Relay connected.")
                    retry_delay = 1
                    async for message in websocket:
                        data = json.loads(message)
                        self._handle_signal(data)
            except Exception as e:
                self.connected = False
                self.websocket = None
                logger.debug("hub", f"Relay disconnected: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30) # Exponential backoff

    async def send(self, data: dict):
        """Injects a signal into the native Go-relay swarm."""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(data))
            except Exception as e:
                logger.debug("hub", f"Failed to send relay signal: {e}")

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
            logger.info("hub", f"Discovered remote mission {mid} from swarm")
        elif typ == "intel":
            bus.publish("intel_found", data.get("payload", {}))
        elif typ == "titan_event":
            mid = data.get("mission_id")
            event_type = data.get("text")
            logger.info("hub", f"Titan event: {event_type} (mission {mid})")
            bus.publish("module_log", {
                "module": "titan",
                "text": f"Titan event: {event_type} (mission {mid})",
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
        """Returns elapsed time since mission start."""
        delta = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        return f"{minutes}m {seconds}s"

class ShadowHub:
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

        from shadowcypher.core.identity import identity
        if not identity.is_admin:
            logger.critical("hub", "This machine is not recognized as an admin node.")

        self._wire_bus()
        self._engage_distributed_nodes() # sentinel/irc bridge
        self._start_relay_bridge()
        self._start_honeypot()

        logger.info("hub", "ShadowHub ready.")
        self._start_nexus_relay()
        self._start_sisyphus()
        self._start_ghost_orchestrator()
        self._start_training_range()
        self._start_v2_services()
        self._start_health_monitor()

    def _start_health_monitor(self) -> None:
        """Polls Tor and relay liveness every 10s."""
        import socket as _socket
        import time as _time
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
        import socket as _socket
        import subprocess
        self._training_range_proc = None
        try:
            with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', 5000)) == 0:
                    logger.info("hub", "Training range already running on port 5000.")
                    return
            script_path = os.path.join(str(platform_engine.resolve_path("")), "launch_training_range.sh")
            if os.path.exists(script_path):
                self._training_range_proc = subprocess.Popen(
                    ["bash", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.info("hub", "Training range started.")
        except (OSError, ValueError) as e:
            logger.error("hub", f"Training range failed to start: {e}")

    def _start_ghost_orchestrator(self) -> None:
        """Starts the Ghost Orchestrator for managing remote Shadow Nodes."""
        from shadowcypher.core.ghost import ghost_orchestrator
        ghost_orchestrator.start()

    def _start_v2_services(self) -> None:
        """Start background services: CVE feed, knowledge graph, ShadowGuard."""
        try:
            from shadowcypher.modules.cve_feed import cve_feed
            cve_feed.start_background_poll(
                interval_hours=6,
                on_new_cve=lambda cve: bus.publish("intel_found", {
                    "type": "CVE", "data": cve
                })
            )
            logger.info("hub", "CVE feed polling active (every 6h)")
        except Exception as e:
            logger.warning("hub", f"CVE feed failed to start: {e}")

        try:
            from shadowcypher.core.knowledge_graph import kg
            bus.subscribe("red_team_complete", lambda summary:
                bus.publish("module_log", {
                    "module": "kg", "text": summary, "level": "INFO"
                })
            )
            self._update_telemetry("kg_nodes", kg.stats()["nodes"])
            logger.info("hub", f"Knowledge graph loaded ({kg.stats()['nodes']} nodes)")
        except Exception as e:
            logger.warning("hub", f"Knowledge graph init failed: {e}")

        def _guard_telemetry():
            import time
            while True:
                time.sleep(1800)
                try:
                    stats = guard.get_stats()
                    self._update_telemetry("guard_blocked", stats.get("blocked", 0))
                    self._update_telemetry("guard_scanned", stats.get("scanned", 0))
                except Exception as e:
                    logger.warning("hub", f"Failed to fetch guard stats: {e}")
        threading.Thread(target=_guard_telemetry, daemon=True, name="GuardTelemetry").start()
        logger.info("hub", "ShadowGuard telemetry active")

    def _start_sisyphus(self) -> None:
        """Starts the Sisyphus file integrity monitor."""
        sisyphus.start()

    def _start_honeypot(self) -> None:
        """Starts the SSH honeypot."""
        from shadowcypher.core.security import StealthHoneypot
        self.honeypot = StealthHoneypot()
        def _on_threat(msg):
            self.telemetry["threat_hits"] += 1
            self.telemetry["last_incident"] = datetime.now(timezone.utc).isoformat()
            bus.publish("threat_detected", {"message": msg})
        self.honeypot.start_bait(on_threat=_on_threat)

    def _start_relay_bridge(self) -> None:
        """Connects to the Go WebSocket relay in a background thread."""
        self.relay_bridge = RelayBridge(self)
        def run_bridge():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.relay_bridge.connect())
        threading.Thread(target=run_bridge, name="HubRelayBridge", daemon=True).start()

    def register_arsenal(self):
        """Load the tool registry (called late to avoid circular imports)."""
        logger.info("hub", "Loading tool registry...")

    def is_tor_available(self) -> bool:
        """Checks if Tor SOCKS5 proxy is reachable on standard port."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 9050), timeout=1):
                return True
        except Exception:
            return False

    def dispatch_ghost_mission(self, target: str) -> str:
        """Run a zero-trace mission through Tor. Blocks if Tor is unavailable."""
        if not self.is_tor_available():
            logger.error("hub", "Tor proxy not reachable — ghost mission blocked.")
            return "error: tor_offline"

        from shadowcypher.core.missions import ignite_ghost_operation
        ignite_ghost_operation(target)
        return "ok"

    def _start_nexus_relay(self) -> None:
        """Start the Nexus relay in a background thread."""
        try:
            from shadowcypher.core.nexus import nexus
            threading.Thread(target=nexus.start, name="ShadowNexus", daemon=True).start()
        except Exception as e:
            logger.error("hub", f"Nexus relay failed to start: {e}")

    def _update_telemetry(self, key: str, value: Any) -> None:
        """Update a telemetry value and broadcast the change on the bus."""
        self.telemetry[key] = value
        bus.publish("telemetry_update", {"key": key, "value": value})

    def _engage_distributed_nodes(self) -> None:
        logger.debug("hub", "No remote nodes configured.")

    def _wire_bus(self) -> None:
        bus.subscribe("intel_found", self._on_intel_discovered)
        bus.subscribe("sisyphus_report", self._on_health_report)
        bus.subscribe("pulse_anomaly", self._on_pulse_anomaly)
        bus.subscribe("red_team_complete", self._on_red_team_complete)
        bus.subscribe("module_log", self._forward_to_relay)
        bus.subscribe("ghost_update", self._forward_to_relay)
        bus.subscribe("ghost_node_linked", self._on_ghost_linked)
        bus.subscribe("ghost_node_output", self._on_ghost_output)

    def _forward_to_relay(self, data: Dict[str, Any]) -> None:
        """Forward a bus event to the Go relay for broadcast to connected peers."""
        if hasattr(self, 'relay_bridge') and self.relay_bridge.connected:
            if not hasattr(self.relay_bridge, 'loop'):
                return

            # Don't echo messages that already came from the swarm
            mod = data.get("module", "")
            if mod.startswith("swarm/"):
                return

            # Only forward the text field — don't leak full event objects
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
            except Exception as e:
                logger.debug("hub", f"Failed to send to relay bridge: {e}")

    def _on_intel_discovered(self, intel: Dict[str, Any]) -> None:
        typ = intel.get("type", "unknown")
        ip = intel.get("ip", "local")
        logger.info("hub", f"New intel: {typ} for {ip}")

        if self.autonomous_enabled and typ in ["CVE", "EXPLOITABLE_SERVICE"]:
            self.dispatch_mission(
                f"Validate {typ} finding on {ip} and assess exploitability.",
                agent_role="adversary"
            )

    def _on_red_team_complete(self, summary: str) -> None:
        try:
            from shadowcypher.core.knowledge_graph import kg
            stats = kg.stats()
            self._update_telemetry("kg_nodes", stats["nodes"])
            self._update_telemetry("kg_edges", stats["edges"])
            logger.info("hub", f"Red team complete: {summary}")
        except Exception as e:
            logger.warning("hub", f"Red team summary failed: {e}")

    def _on_pulse_anomaly(self, event: Dict[str, Any]) -> None:
        stream = event.get("stream", "unknown")
        logger.warning("hub", f"High-variance anomaly detected in stream: {stream}")

        if self.autonomous_enabled:
            self.dispatch_mission(
                f"Investigate signal anomaly in stream '{stream}' — assess potential exposure.",
                agent_role="commander"
            )

    def _on_health_report(self, report: Dict[str, Any]) -> None:
        """Update load average from a Sisyphus health report."""
        load = report.get("vitals", {}).get("cpu", 0.0)
        self._update_telemetry("load_avg", load)
        self.system_status = "STRESSED" if load > 90 else self.SYSTEM_READY

    def _on_ghost_linked(self, data: Dict[str, Any]) -> None:
        nick = data.get("nick")
        host = data.get("host")
        logger.info("hub", f"Ghost node '{nick}' connected from {host}")
        bus.publish("module_log", {
            "module": "ghost",
            "text": f"Ghost node '{nick}' connected from {host}.",
            "level": "SUCCESS"
        })

    def _on_ghost_output(self, data: Dict[str, Any]) -> None:
        nick = data.get("nick")
        output = data.get("output")
        bus.publish("module_log", {
            "module": f"ghost/{nick}",
            "text": output,
            "level": "INFO"
        })

    def dispatch_shadow_mission(self, script_path: str) -> str:
        """Run a ShadowScript file as a mission."""
        mission_id = f"GHOST-{uuid.uuid4().hex[:6].upper()}"
        logger.info("hub", f"Running script: {os.path.basename(script_path)}")

        def _run():
            from shadowcypher.compiler.interpreter import ShadowInterpreter
            interp = ShadowInterpreter()
            with open(script_path, 'r') as f:
                interp.run(f.read())
            self._finalize_mission(mission_id, "script complete")

        threading.Thread(target=_run, daemon=True).start()
        return mission_id

    def dispatch_mission(self, query: str, agent_role: str = "commander") -> str:
        """Start a new AI mission and return its ID immediately."""
        from shadowcypher.ai.agents import agent_router

        mission_id = f"MSN-{uuid.uuid4().hex[:8].upper()}"
        mission = Mission(id=mission_id, query=query, role=agent_role)
        self.active_missions[mission_id] = mission
        self.telemetry["missions_total"] += 1

        _role_map = {
            "commander": "commander", "adversary": "security",
            "security": "security", "recon": "recon",
            "analyst": "analyst", "coder": "coder",
        }
        fleet_agent = _role_map.get(agent_role, "commander")

        agent_router.dispatch_async(
            query,
            callback=lambda msg: self._update_mission(mission_id, msg),
            on_complete=lambda res: self._finalize_mission(mission_id, res),
            force_agent=fleet_agent,
            use_ai_routing=False,
        )

        return mission_id

    def dispatch_agentic_mission(self, target: str, goal: str) -> str:
        """
        Launch an autonomous agentic mission.
        The AI will chain tools dynamically to achieve the goal.
        """
        from shadowcypher.ai.agentic_loop import shadow_loop

        mission_id = f"AGENT-{uuid.uuid4().hex[:8].upper()}"
        mission = Mission(id=mission_id, query=goal, role="commander")
        self.active_missions[mission_id] = mission
        self.telemetry["missions_total"] += 1

        logger.info("hub", f"Launching agentic mission {mission_id} -> Goal: {goal}")

        def _run():
            # Stream loop updates to the hub's mission update system
            result = shadow_loop.run(
                target=target,
                goal=goal,
                on_step_update=lambda msg: self._update_mission(mission_id, msg)
            )
            self._finalize_mission(mission_id, result)

        threading.Thread(target=_run, daemon=True, name=f"AgentLoop-{mission_id}").start()
        return mission_id

    def _update_mission(self, mid: str, msg: str) -> None:
        """Stream a mission output line to the bus."""
        if mid in self.active_missions:
            bus.publish("module_log", {
                "module": f"hub/{mid}",
                "text": msg,
                "level": "INFO"
            })

    def _finalize_mission(self, mid: str, result: str) -> None:
        """Mark a mission complete, persist it to the forensics registry."""
        if mid in self.active_missions:
            mission = self.active_missions[mid]
            mission.status = 'COMPLETE'
            mission.progress = 100
            mission.last_update_msg = result

            from shadowcypher.core.forensics import registry
            registry.register_mission(mid, mission.query, result, {
                "role": mission.role,
                "duration": mission.duration,
                "findings_count": len(mission.findings)
            })

            logger.info("hub", f"Mission {mid} complete.")
            del self.active_missions[mid]

    def dispatch_auto_scan(
        self,
        target: str,
        on_output: Callable = None,
        on_complete: Callable = None,
        confirm_fn: Callable = None,
        phases: list = None,
    ) -> str:
        """
        Launch an adaptive full-pipeline scan on target in a background thread.
        Returns a mission ID immediately; streams output via on_output callback.

        Args:
            target:      IP, hostname, or URL
            on_output:   Called with each output line as it's produced
            on_complete: Called with ScanResult when pipeline finishes
            confirm_fn:  fn(tool, target) → bool  — gates destructive tools (sqlmap)
            phases:      List of phase names to run (default: all)
        """
        from shadowcypher.ai.auto_scan import auto_scan

        mission_id = f"ASCAN-{uuid.uuid4().hex[:8].upper()}"
        self.telemetry["missions_total"] += 1
        logger.info("hub", f"Auto scan {mission_id} → {target}")

        def _on_line(line: str):
            bus.publish("module_log", {"module": f"hub/{mission_id}", "text": line, "level": "INFO"})
            if on_output:
                on_output(line)

        def _on_done(result):
            self._update_telemetry("kg_nodes",
                __import__("shadowcypher.core.knowledge_graph", fromlist=["kg"]).kg.stats()["nodes"])
            bus.publish("module_log", {
                "module": f"hub/{mission_id}",
                "text": f"Auto scan complete: {result.summary()}",
                "level": "SUCCESS",
            })
            if on_complete:
                on_complete(result)

        auto_scan.run_async(
            target,
            on_output=_on_line,
            on_complete=_on_done,
            confirm_fn=confirm_fn,
            phases=phases,
        )
        return mission_id

    def is_stealth_ready(self) -> bool:
        """Returns True if identity is secured and relay is connected."""
        from shadowcypher.core.security import hardener
        if not hardener.is_secure:
            return False
        if not hasattr(self, 'relay_bridge') or not self.relay_bridge.connected:
            return False
        return True

    @property
    def uptime_formatted(self) -> str:
        """Time since hub started, formatted as HH:MM:SS."""
        delta = datetime.now(timezone.utc) - self.start_time
        return str(delta).split(".")[0]

    def get_tactical_summary(self) -> Dict[str, Any]:
        """Return a telemetry snapshot for the dashboard."""
        summary = {
            "uptime": self.uptime_formatted,
            "status": self.system_status,
            "active_missions": len(self.active_missions),
        }
        summary.update(self.telemetry)
        return summary


hub = ShadowHub()
