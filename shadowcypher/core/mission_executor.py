"""
Mission Executor — Runs Guardian scanning missions and tracks results.
Orchestrates nmap, host audits, router scans with real-time status updates.
"""

import os
import json
import uuid
import subprocess
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from shadowcypher.core.logger import logger
from shadowcypher.core.scan_history import get_scan_history


class MissionStatus(str, Enum):
    """Mission execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Mission:
    """Guardian mission record."""
    id: str
    type: str  # "network_scan", "host_audit", "router_scan", "monitor"
    target: Optional[str]
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_output: Optional[str] = None
    devices_found: int = 0
    incidents_found: int = 0
    exit_code: Optional[int] = None


class MissionExecutor:
    """Orchestrates Guardian scanning missions."""

    def __init__(self):
        self.missions: Dict[str, Mission] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()

    def execute_network_scan(self, subnet: Optional[str] = None) -> str:
        """Start a network scanning mission."""
        mission_id = f"mission-{uuid.uuid4().hex[:8]}"
        mission = Mission(
            id=mission_id,
            type="network_scan",
            target=subnet or "auto-detect",
            status=MissionStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self.lock:
            self.missions[mission_id] = mission

        # Run in background
        thread = threading.Thread(
            target=self._run_network_scan,
            args=(mission_id, subnet),
            daemon=True,
            name=f"Mission-{mission_id}",
        )
        thread.start()

        logger.info("mission_executor", f"Started mission {mission_id}: network_scan")
        self._notify_mission_update(mission_id, mission)
        return mission_id

    def execute_host_audit(self, target: str = "localhost") -> str:
        """Start a host audit mission."""
        mission_id = f"mission-{uuid.uuid4().hex[:8]}"
        mission = Mission(
            id=mission_id,
            type="host_audit",
            target=target,
            status=MissionStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self.lock:
            self.missions[mission_id] = mission

        thread = threading.Thread(
            target=self._run_host_audit,
            args=(mission_id, target),
            daemon=True,
            name=f"Mission-{mission_id}",
        )
        thread.start()

        logger.info("mission_executor", f"Started mission {mission_id}: host_audit")
        self._notify_mission_update(mission_id, mission)
        return mission_id

    def _run_network_scan(self, mission_id: str, subnet: Optional[str] = None):
        """Execute network scan (runs in background thread)."""
        mission = self.missions[mission_id]

        try:
            mission.status = MissionStatus.RUNNING
            mission.started_at = datetime.now(timezone.utc).isoformat()
            self._notify_mission_update(mission_id, mission)

            # Auto-detect subnet if not provided
            if not subnet or subnet == "auto-detect":
                subnet = self._detect_subnet()

            if not subnet:
                raise ValueError("Could not auto-detect subnet")

            # Run nmap
            cmd = ["nmap", "-sn", "-n", subnet]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            mission.result_output = result.stdout
            mission.exit_code = result.returncode

            # Parse devices from nmap output
            devices = self._parse_nmap_output(result.stdout, subnet)
            mission.devices_found = len(devices)

            # Save to history
            scan_history = get_scan_history()
            scan_history.save_scan(
                scan_id=mission_id,
                scan_type="network_scan",
                target=subnet,
                devices=devices,
                incidents=[],
            )

            mission.status = MissionStatus.COMPLETED
            mission.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                "mission_executor",
                f"Mission {mission_id} completed: {mission.devices_found} devices found",
            )

        except subprocess.TimeoutExpired:
            mission.status = MissionStatus.FAILED
            mission.result_output = "Timeout: scan took too long"
            mission.exit_code = -1
            logger.error("mission_executor", f"Mission {mission_id} timeout")

        except Exception as e:
            mission.status = MissionStatus.FAILED
            mission.result_output = str(e)
            mission.exit_code = -1
            logger.error("mission_executor", f"Mission {mission_id} failed: {e}")

        finally:
            mission.completed_at = datetime.now(timezone.utc).isoformat()
            self._notify_mission_update(mission_id, mission)

    def _run_host_audit(self, mission_id: str, target: str):
        """Execute host audit (runs in background thread)."""
        mission = self.missions[mission_id]

        try:
            mission.status = MissionStatus.RUNNING
            mission.started_at = datetime.now(timezone.utc).isoformat()
            self._notify_mission_update(mission_id, mission)

            try:
                from shadowcypher.modules.host_audit import HostAudit
                auditor = HostAudit()

                output = auditor.rkhunter_scan()
                mission.result_output = output or "RKHunter not available"
                mission.exit_code = 0

                # Parse for threats
                if output:
                    threat_count = output.count("INFECTED") + output.count("WARNING")
                    mission.incidents_found = threat_count

            except Exception as e:
                mission.result_output = f"Host audit failed: {e}"
                mission.exit_code = -1

            mission.status = MissionStatus.COMPLETED
            mission.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                "mission_executor",
                f"Mission {mission_id} completed: {mission.incidents_found} issues found",
            )

        except Exception as e:
            mission.status = MissionStatus.FAILED
            mission.result_output = str(e)
            mission.exit_code = -1
            logger.error("mission_executor", f"Mission {mission_id} failed: {e}")

        finally:
            mission.completed_at = datetime.now(timezone.utc).isoformat()
            self._notify_mission_update(mission_id, mission)

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Retrieve mission status and results."""
        with self.lock:
            return self.missions.get(mission_id)

    def list_missions(self, status: Optional[str] = None, limit: int = 50) -> List[Mission]:
        """List missions with optional status filter."""
        with self.lock:
            missions = list(self.missions.values())

        if status:
            missions = [m for m in missions if m.status == status]

        return sorted(missions, key=lambda m: m.created_at, reverse=True)[:limit]

    def subscribe_mission_updates(self, mission_id: str, callback: Callable):
        """Subscribe to mission status updates (for WebSocket)."""
        if mission_id not in self.callbacks:
            self.callbacks[mission_id] = []
        self.callbacks[mission_id].append(callback)

    def _notify_mission_update(self, mission_id: str, mission: Mission):
        """Notify all subscribers of mission update."""
        callbacks = self.callbacks.get(mission_id, [])
        for callback in callbacks:
            try:
                callback(asdict(mission))
            except Exception as e:
                logger.error("mission_executor", f"Callback failed: {e}")

    @staticmethod
    def _detect_subnet() -> Optional[str]:
        """Auto-detect local subnet."""
        try:
            result = subprocess.run(
                ["ip", "-o", "-4", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if "127.0.0.1" in line:
                    continue
                if " inet " in line:
                    parts = line.split()
                    for part in parts:
                        if "/" in part:
                            ip_with_mask = part
                            # Convert /24 to /0/24
                            import re
                            match = re.search(r"(\d+\.\d+\.\d+)\.\d+/(\d+)", ip_with_mask)
                            if match:
                                return f"{match.group(1)}.0/{match.group(2)}"

            return None
        except Exception as e:
            logger.debug("mission_executor", f"Failed to detect subnet: {e}")
            return None

    @staticmethod
    def _parse_nmap_output(output: str, subnet: str) -> List[Dict[str, Any]]:
        """Parse nmap output into device records."""
        devices = []

        for line in output.split("\n"):
            if "Nmap scan report for" in line:
                # Extract IP
                parts = line.split()
                if len(parts) >= 5:
                    ip = parts[-1]
                    devices.append({
                        "ip": ip,
                        "hostname": ip,
                        "device_type": "unknown",
                        "status": "online",
                    })

        return devices


# Singleton instance
_mission_executor = None


def get_mission_executor() -> MissionExecutor:
    """Get or create MissionExecutor singleton."""
    global _mission_executor
    if _mission_executor is None:
        _mission_executor = MissionExecutor()
    return _mission_executor
