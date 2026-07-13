"""
Scan History Database — Persistent tracking of Guardian scans.
Stores device discovery results, incidents, audit results over time.
SQLite-backed with XDG fallback paths.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from shadowcypher.core.logger import logger


def _resolve_db_path() -> str:
    """Resolve writable database path with XDG fallback."""
    candidates = []

    # Try project's shadowcypher directory first
    try:
        from shadowcypher.core.config import config
        project_root = config.project_root
        db_path = os.path.join(project_root, ".shadowcypher", "scan_history.db")
        candidates.append(db_path)
    except Exception:
        pass

    # XDG data home
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    candidates.append(os.path.join(xdg_data, "shadowcypher", "scan_history.db"))

    # Temp fallback
    import tempfile
    candidates.append(os.path.join(tempfile.gettempdir(), "shadowcypher_scan_history.db"))

    for candidate in candidates:
        try:
            os.makedirs(os.path.dirname(candidate), exist_ok=True)
            # Test write permission
            with open(os.path.join(os.path.dirname(candidate), ".test"), "a"):
                pass
            os.remove(os.path.join(os.path.dirname(candidate), ".test"))
            return candidate
        except OSError:
            continue

    return candidates[-1]  # Fallback to temp


DB_PATH = _resolve_db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    scan_type TEXT NOT NULL,
    target TEXT,
    started_at REAL,
    completed_at REAL,
    status TEXT DEFAULT 'pending',
    result_json TEXT,
    device_count INTEGER DEFAULT 0,
    incident_count INTEGER DEFAULT 0,
    created REAL DEFAULT (unixepoch('now'))
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    ip TEXT,
    hostname TEXT,
    mac TEXT,
    device_type TEXT,
    vendor TEXT,
    risk_level TEXT,
    open_ports TEXT,
    services TEXT,
    discovered_at REAL DEFAULT (unixepoch('now')),
    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    scan_id TEXT,
    category TEXT,
    severity TEXT,
    title TEXT,
    description TEXT,
    affected_device TEXT,
    created_at REAL DEFAULT (unixepoch('now'))
);

CREATE INDEX IF NOT EXISTS idx_scans_type ON scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created);
CREATE INDEX IF NOT EXISTS idx_devices_scan ON devices(scan_id);
CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip);
CREATE INDEX IF NOT EXISTS idx_incidents_scan ON incidents(scan_id);
"""


class ScanHistory:
    """Persistent storage for Guardian scan results."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.executescript(SCHEMA)
            conn.commit()
            conn.close()
            logger.info("scan_history", f"Database ready: {self.db_path}")
        except Exception as e:
            logger.error("scan_history", f"Failed to initialize database: {e}")

    def save_scan(
        self,
        scan_id: str,
        scan_type: str,
        target: Optional[str] = None,
        devices: Optional[List[Dict]] = None,
        incidents: Optional[List[Dict]] = None,
    ) -> bool:
        """Save a scan result with its devices and incidents."""
        try:
            conn = sqlite3.connect(self.db_path)
            now = datetime.now(timezone.utc).timestamp()

            # Save scan record
            conn.execute(
                """INSERT OR REPLACE INTO scans
                   (id, scan_type, target, started_at, completed_at, status, device_count, incident_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    scan_id,
                    scan_type,
                    target,
                    now,
                    now,
                    "completed",
                    len(devices or []),
                    len(incidents or []),
                ),
            )

            # Save devices
            for device in devices or []:
                device_id = f"{scan_id}:{device.get('ip', 'unknown')}"
                conn.execute(
                    """INSERT OR REPLACE INTO devices
                       (id, scan_id, ip, hostname, mac, device_type, vendor, risk_level, open_ports, services)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        device_id,
                        scan_id,
                        device.get("ip"),
                        device.get("hostname"),
                        device.get("mac"),
                        device.get("device_type"),
                        device.get("vendor"),
                        device.get("risk"),
                        json.dumps(device.get("open_ports", [])),
                        json.dumps(device.get("services", [])),
                    ),
                )

            # Save incidents
            for incident in incidents or []:
                incident_id = f"{scan_id}:{incident.get('id', 'unknown')}"
                conn.execute(
                    """INSERT OR REPLACE INTO incidents
                       (id, scan_id, category, severity, title, description, affected_device)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        incident_id,
                        scan_id,
                        incident.get("category"),
                        incident.get("severity"),
                        incident.get("title"),
                        incident.get("description", ""),
                        incident.get("affected_device"),
                    ),
                )

            conn.commit()
            conn.close()
            logger.info("scan_history", f"Saved scan {scan_id}: {len(devices or [])} devices, {len(incidents or [])} incidents")
            return True
        except Exception as e:
            logger.error("scan_history", f"Failed to save scan: {e}")
            return False

    def get_recent_scans(self, scan_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Retrieve recent scans."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            if scan_type:
                rows = conn.execute(
                    """SELECT * FROM scans WHERE scan_type = ?
                       ORDER BY created DESC LIMIT ?""",
                    (scan_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM scans ORDER BY created DESC LIMIT ?""",
                    (limit,),
                ).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error("scan_history", f"Failed to retrieve scans: {e}")
            return []

    def get_scan_details(self, scan_id: str) -> Optional[Dict]:
        """Get full details of a scan including devices and incidents."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            scan = conn.execute(
                "SELECT * FROM scans WHERE id = ?", (scan_id,)
            ).fetchone()

            if not scan:
                return None

            devices = [
                dict(row) for row in conn.execute(
                    "SELECT * FROM devices WHERE scan_id = ?", (scan_id,)
                ).fetchall()
            ]

            incidents = [
                dict(row) for row in conn.execute(
                    "SELECT * FROM incidents WHERE scan_id = ?", (scan_id,)
                ).fetchall()
            ]

            conn.close()

            return {
                **dict(scan),
                "devices": devices,
                "incidents": incidents,
            }
        except Exception as e:
            logger.error("scan_history", f"Failed to retrieve scan details: {e}")
            return None

    def get_device_history(self, ip: str, limit: int = 20) -> List[Dict]:
        """Get all scans that discovered a specific device."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """SELECT DISTINCT s.* FROM scans s
                   JOIN devices d ON s.id = d.scan_id
                   WHERE d.ip = ?
                   ORDER BY s.created DESC LIMIT ?""",
                (ip, limit),
            ).fetchall()

            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error("scan_history", f"Failed to retrieve device history: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics about scans."""
        try:
            conn = sqlite3.connect(self.db_path)

            stats = {
                "total_scans": conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0],
                "total_devices": conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0],
                "total_incidents": conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0],
                "scans_by_type": {},
            }

            for scan_type, count in conn.execute(
                "SELECT scan_type, COUNT(*) FROM scans GROUP BY scan_type"
            ).fetchall():
                stats["scans_by_type"][scan_type] = count

            conn.close()
            return stats
        except Exception as e:
            logger.error("scan_history", f"Failed to retrieve statistics: {e}")
            return {}


# Singleton instance
_scan_history = None


def get_scan_history() -> ScanHistory:
    """Get or create ScanHistory singleton."""
    global _scan_history
    if _scan_history is None:
        _scan_history = ScanHistory()
    return _scan_history
