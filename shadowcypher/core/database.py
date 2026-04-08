"""ShadowCypher Universal Database Engine.
Maps Target Topography securely inside a local SQLite matrix.
"""

import sqlite3
import os
import threading
from datetime import datetime
from shadowcypher.core.config import config
from shadowcypher.core.logger import logger


class TacticalDatabase:
    def __init__(self):
        self.db_path = os.path.join(
            config.project_root, "projects", "shadow_registry.db"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.cursor = self.conn.cursor()
        self._build_schema()

    def _build_schema(self):
        # Target Grid
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS target_grid (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE,
                hostname TEXT,
                mac_address TEXT,
                os_fingerprint TEXT,
                first_seen TEXT,
                last_scanned TEXT
            )
        """)
        # Vulnerability Graph
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS vulnerability_graph (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_ip TEXT,
                port INTEGER,
                service TEXT,
                cve_id TEXT,
                severity TEXT,
                payload_notes TEXT,
                FOREIGN KEY(target_ip) REFERENCES target_grid(ip_address)
            )
        """)
        # Credentials Sink
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials_sink (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_ip TEXT,
                service TEXT,
                username TEXT,
                password TEXT,
                hash TEXT,
                cracked BOOLEAN
            )
        """)
        self.conn.commit()

    def register_target(self, ip, hostname="UNKNOWN", mac="UNKNOWN"):
        now = datetime.now().isoformat()
        with self._lock:
            try:
                self.cursor.execute(
                    "INSERT INTO target_grid (ip_address, hostname, mac_address, first_seen, last_scanned) VALUES (?, ?, ?, ?, ?)",
                    (ip, hostname, mac, now, now),
                )
                self.conn.commit()
                logger.info("database", f"Target {ip} registered.")
            except sqlite3.IntegrityError:
                self.cursor.execute(
                    "UPDATE target_grid SET last_scanned = ? WHERE ip_address = ?",
                    (now, ip),
                )
                self.conn.commit()

    def log_vulnerability(
        self, ip, port, service, cve_id="N/A", severity="MEDIUM", payload=""
    ):
        self.register_target(ip)
        with self._lock:
            self.cursor.execute(
                "INSERT INTO vulnerability_graph (target_ip, port, service, cve_id, severity, payload_notes) VALUES (?, ?, ?, ?, ?, ?)",
                (ip, port, service, cve_id, severity, payload),
            )
            self.conn.commit()

    def export_target_graph(self):
        with self._lock:
            self.cursor.execute("SELECT * FROM target_grid")
            return self.cursor.fetchall()


db = TacticalDatabase()
