"""
Guardian Service — Bridge between Guardian scans and API endpoints.
Manages scan results, device inventory, incidents, and CVE tracking.
Persists scan history to database for historical analysis.
"""

import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from shadowcypher.core.logger import logger
from shadowcypher.core.hub import hub
from shadowcypher.core.scan_history import get_scan_history


class GuardianService:
    """Central Guardian data provider for Android API."""

    def __init__(self):
        self.findings_dir = hub.findings_dir
        self.kg = None
        try:
            from shadowcypher.core.knowledge_graph import kg
            self.kg = kg
        except Exception as e:
            logger.warning("guardian_service", f"Failed to import knowledge graph: {e}")

    def get_recent_devices(self, limit_hours: int = 24) -> List[Dict[str, Any]]:
        """Return devices from recent Guardian scans and database history."""
        devices = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=limit_hours)

        # Look for scan result files in findings directory
        findings_path = Path(self.findings_dir)
        if findings_path.exists():
            for file_path in findings_path.glob("*guardian*scan*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        devices.extend(data)
                    elif isinstance(data, dict) and "devices" in data:
                        devices.extend(data["devices"])
                        # Save to history
                        scan_history = get_scan_history()
                        scan_id = f"scan-{uuid.uuid4().hex[:8]}"
                        scan_history.save_scan(
                            scan_id=scan_id,
                            scan_type="network_scan",
                            devices=data.get("devices", []),
                            incidents=[],
                        )
                except Exception as e:
                    logger.debug("guardian_service", f"Failed to parse {file_path}: {e}")

        # Also fetch from history database if no recent files
        if not devices:
            try:
                scan_history = get_scan_history()
                recent_scans = scan_history.get_recent_scans("network_scan", limit=5)
                for scan in recent_scans:
                    scan_detail = scan_history.get_scan_details(scan["id"])
                    if scan_detail:
                        devices.extend(scan_detail.get("devices", []))
            except Exception as e:
                logger.debug("guardian_service", f"Failed to fetch history: {e}")

        # Augment with knowledge graph data if available
        if self.kg:
            try:
                for device in devices:
                    ip = device.get("ip")
                    if ip and self.kg:
                        # Look up CVEs linked to this device in the knowledge graph
                        node_id = f"TARGET:{ip}"
                        neighbors = self.kg.neighbors(node_id, rel="VULNERABLE_TO")
                        device["vulnerabilities"] = len(neighbors)
            except Exception as e:
                logger.debug("guardian_service", f"Failed to augment device data: {e}")

        # Mock device if no recent scans (for testing)
        if not devices:
            devices = [
                {
                    "ip": "192.168.1.1",
                    "hostname": "router",
                    "mac": "00:11:22:33:44:55",
                    "device_type": "router",
                    "vendor": "Netgear",
                    "status": "online",
                    "open_ports": [22, 80, 443],
                    "services": ["SSH", "HTTP", "HTTPS"],
                    "risk": "MEDIUM",
                    "vulnerabilities": 1,
                },
                {
                    "ip": "192.168.1.100",
                    "hostname": "desktop",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "device_type": "desktop",
                    "vendor": "Unknown",
                    "status": "online",
                    "open_ports": [22],
                    "services": ["SSH"],
                    "risk": "LOW",
                    "vulnerabilities": 0,
                },
            ]

        return devices

    def get_incidents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return security incidents from scans and threat detection."""
        incidents = []

        # Query knowledge graph for CVEs linked to discovered devices
        if self.kg:
            try:
                nodes = self.kg.find_by_type("CVE", limit=limit)
                for node in nodes:
                    cve_id = node.get("id", "").replace("CVE:", "")
                    incidents.append({
                        "id": cve_id,
                        "category": "cve_vulnerability",
                        "severity": node.get("props", {}).get("severity", "UNKNOWN"),
                        "title": f"CVE-{cve_id}: {node.get('label', 'Vulnerability')}",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "acknowledged": False,
                    })
            except Exception as e:
                logger.debug("guardian_service", f"Failed to fetch CVE incidents: {e}")

        # Look for incident files in findings directory
        findings_path = Path(self.findings_dir)
        if findings_path.exists():
            for file_path in findings_path.glob("*incident*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        incidents.extend(data)
                    elif isinstance(data, dict):
                        if "incidents" in data:
                            incidents.extend(data["incidents"])
                        else:
                            incidents.append(data)
                except Exception as e:
                    logger.debug("guardian_service", f"Failed to parse {file_path}: {e}")

        # Mock incidents if none found
        if not incidents:
            incidents = [
                {
                    "id": "CVE-2024-1234",
                    "category": "port_scan",
                    "severity": "high",
                    "title": "Remote code execution in OpenSSH",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "acknowledged": False,
                },
            ]

        return incidents[:limit]

    def get_cve_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return CVE alerts for affected devices."""
        alerts = []

        if self.kg:
            try:
                # Get all CVE nodes
                cve_nodes = self.kg.find_by_type("CVE", limit=limit)
                for cve_node in cve_nodes:
                    alerts.append({
                        "cve_id": cve_node.get("id", "").replace("CVE:", ""),
                        "severity": cve_node.get("props", {}).get("severity"),
                        "description": cve_node.get("label"),
                        "affected_device": "multiple",
                    })
            except Exception as e:
                logger.debug("guardian_service", f"Failed to fetch CVE alerts: {e}")

        # Mock alerts if none found
        if not alerts:
            alerts = [
                {
                    "cve_id": "CVE-2024-1234",
                    "severity": "high",
                    "description": "Remote code execution in OpenSSH",
                    "affected_device": "router",
                },
            ]

        return alerts[:limit]

    def get_agents(self) -> List[Dict[str, Any]]:
        """Return Guardian agents (scanner instances)."""
        return [
            {
                "id": "agent-001",
                "hostname": "localhost",
                "online": True,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "os": "Linux",
                "agent_version": "1.0.0",
            }
        ]

    def get_last_scan_time(self) -> Optional[str]:
        """Return timestamp of most recent scan."""
        findings_path = Path(self.findings_dir)
        latest_time = None

        if findings_path.exists():
            for file_path in findings_path.glob("*guardian*scan*.json"):
                if file_path.stat().st_mtime > (latest_time or 0):
                    latest_time = file_path.stat().st_mtime

        if latest_time:
            return datetime.fromtimestamp(latest_time, tz=timezone.utc).isoformat()
        return datetime.now(timezone.utc).isoformat()

    def trigger_scan(self, subnet: Optional[str] = None) -> str:
        """Trigger a Guardian network scan in the background."""
        from shadowcypher.core.hub import hub

        mission_id = hub.dispatch_mission(
            "guardian_scan",
            lambda: self._run_scan(subnet),
        )
        logger.info("guardian_service", f"Triggered scan {mission_id} for subnet {subnet or 'auto'}")
        return mission_id

    def _run_scan(self, subnet: Optional[str] = None):
        """Execute Guardian scan (called in background)."""
        try:
            import subprocess
            args = ["python3", "-m", "shadowcypher.scripts.guardian", "scan"]
            if subnet:
                args.append(f"--subnet={subnet}")
            result = subprocess.run(args, capture_output=True, text=True, timeout=300)
            logger.info("guardian_service", f"Scan completed with exit code {result.returncode}")
            return result.returncode == 0
        except Exception as e:
            logger.error("guardian_service", f"Scan failed: {e}")
            return False


# Singleton instance
_guardian_service = None


def get_guardian_service() -> GuardianService:
    """Get or create Guardian service singleton."""
    global _guardian_service
    if _guardian_service is None:
        _guardian_service = GuardianService()
    return _guardian_service
