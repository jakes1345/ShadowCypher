"""
Scan Analytics — Advanced querying and trend analysis for scan history.
Provides insights into device discovery patterns, threat trends, scan effectiveness.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from shadowcypher.core.logger import logger
from shadowcypher.core.scan_history import _resolve_db_path


class ScanAnalytics:
    """Analyze scan history for trends and patterns."""

    def __init__(self, db_path: str = _resolve_db_path()):
        self.db_path = db_path

    def get_device_discovery_timeline(
        self, days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get device discovery count by day over past N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()

            rows = conn.execute(
                """
                SELECT
                    date(created_at / 1000, 'unixepoch') as date,
                    COUNT(DISTINCT ip) as unique_devices,
                    COUNT(*) as total_devices
                FROM devices
                WHERE created_at > ?
                GROUP BY date
                ORDER BY date ASC
                """,
                (cutoff,),
            ).fetchall()

            conn.close()

            return {
                "timeline": [
                    {
                        "date": row[0],
                        "unique_devices": row[1],
                        "total_records": row[2],
                    }
                    for row in rows
                ]
            }
        except Exception as e:
            logger.error("scan_analytics", f"Failed to get timeline: {e}")
            return {"timeline": []}

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of devices by risk level."""
        try:
            conn = sqlite3.connect(self.db_path)

            rows = conn.execute(
                """
                SELECT risk_level, COUNT(*) as count
                FROM devices
                WHERE risk_level IS NOT NULL
                GROUP BY risk_level
                ORDER BY count DESC
                """
            ).fetchall()

            conn.close()

            return {
                "distribution": {row[0] or "UNKNOWN": row[1] for row in rows}
            }
        except Exception as e:
            logger.error("scan_analytics", f"Failed to get risk distribution: {e}")
            return {"distribution": {}}

    def get_top_devices_by_incident_count(self, limit: int = 10) -> List[Dict]:
        """Get devices with most incidents."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT
                    affected_device,
                    COUNT(*) as incident_count,
                    GROUP_CONCAT(DISTINCT severity) as severity_types
                FROM incidents
                WHERE affected_device IS NOT NULL
                GROUP BY affected_device
                ORDER BY incident_count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            conn.close()

            return [
                {
                    "device": row["affected_device"],
                    "incident_count": row["incident_count"],
                    "severity_types": (row["severity_types"] or "").split(","),
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("scan_analytics", f"Failed to get top devices: {e}")
            return []

    def get_scan_effectiveness(self) -> Dict[str, Any]:
        """Measure scan effectiveness metrics."""
        try:
            conn = sqlite3.connect(self.db_path)

            total_scans = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
            avg_devices = conn.execute(
                "SELECT AVG(device_count) FROM scans WHERE device_count > 0"
            ).fetchone()[0] or 0
            avg_incidents = conn.execute(
                "SELECT AVG(incident_count) FROM scans WHERE incident_count > 0"
            ).fetchone()[0] or 0
            completed_scans = conn.execute(
                "SELECT COUNT(*) FROM scans WHERE status = 'completed'"
            ).fetchone()[0]

            conn.close()

            return {
                "total_scans": total_scans,
                "completed_scans": completed_scans,
                "completion_rate": (
                    completed_scans / total_scans if total_scans > 0 else 0
                ),
                "avg_devices_per_scan": round(avg_devices, 1),
                "avg_incidents_per_scan": round(avg_incidents, 1),
            }
        except Exception as e:
            logger.error("scan_analytics", f"Failed to get effectiveness: {e}")
            return {}

    def get_threat_summary(self) -> Dict[str, Any]:
        """Get aggregate threat summary."""
        try:
            conn = sqlite3.connect(self.db_path)

            high_risk_devices = conn.execute(
                "SELECT COUNT(DISTINCT ip) FROM devices WHERE risk_level = 'HIGH'"
            ).fetchone()[0]

            critical_incidents = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE severity IN ('critical', 'high')"
            ).fetchone()[0]

            unique_threat_types = conn.execute(
                "SELECT COUNT(DISTINCT category) FROM incidents"
            ).fetchone()[0]

            conn.close()

            return {
                "high_risk_devices": high_risk_devices,
                "critical_incidents": critical_incidents,
                "unique_threat_types": unique_threat_types,
            }
        except Exception as e:
            logger.error("scan_analytics", f"Failed to get threat summary: {e}")
            return {}


# Singleton instance
_scan_analytics = None


def get_scan_analytics() -> ScanAnalytics:
    """Get or create ScanAnalytics singleton."""
    global _scan_analytics
    if _scan_analytics is None:
        _scan_analytics = ScanAnalytics()
    return _scan_analytics
