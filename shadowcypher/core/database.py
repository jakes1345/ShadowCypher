"""ShadowCypher Universal Database Engine.
Maps Target Topography securely inside a local SQLite matrix.

Thread-safety: All public methods acquire the lock and use their own cursor
to prevent cross-thread cursor sharing race conditions.
"""

import sqlite3
import os
import threading
import tempfile
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
        self._build_schema()

    def _execute(self, sql, params=(), fetch=False, fetchall=False):
        """Thread-safe query execution with per-call cursor."""
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute(sql, params)
                if fetch:
                    return cursor.fetchone()
                if fetchall:
                    return cursor.fetchall()
                self.conn.commit()
                return cursor.lastrowid
            except Exception:
                raise
            finally:
                cursor.close()

    def _build_schema(self):
        with self._lock:
            cursor = self.conn.cursor()
            # Target Grid
            cursor.execute("""
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
            cursor.execute("""
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
            cursor.execute("""
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
            cursor.close()

    def register_target(self, ip, hostname="UNKNOWN", mac="UNKNOWN"):
        now = datetime.now().isoformat()
        try:
            self._execute(
                "INSERT INTO target_grid (ip_address, hostname, mac_address, first_seen, last_scanned) VALUES (?, ?, ?, ?, ?)",
                (ip, hostname, mac, now, now),
            )
            logger.info("database", f"Target {ip} registered.")
        except sqlite3.IntegrityError:
            self._execute(
                "UPDATE target_grid SET last_scanned = ? WHERE ip_address = ?",
                (now, ip),
            )

    def log_vulnerability(
        self, ip, port, service, cve_id="N/A", severity="MEDIUM", payload=""
    ):
        self.register_target(ip)
        self._execute(
            "INSERT INTO vulnerability_graph (target_ip, port, service, cve_id, severity, payload_notes) VALUES (?, ?, ?, ?, ?, ?)",
            (ip, port, service, cve_id, severity, payload),
        )

    def log_credential(self, target_ip, service, username, password=None, cred_hash=None, cracked=False):
        """Thread-safe credential logging. Used by Kairos and cred_sprayer."""
        self._execute(
            "INSERT INTO credentials_sink (target_ip, service, username, password, hash, cracked) VALUES (?, ?, ?, ?, ?, ?)",
            (target_ip, service, username, password, cred_hash, cracked),
        )

    def export_target_graph(self):
        return self._execute("SELECT * FROM target_grid", fetchall=True)

    def export_vulnerabilities(self, target_ip=None):
        if target_ip:
            return self._execute(
                "SELECT * FROM vulnerability_graph WHERE target_ip = ?",
                (target_ip,), fetchall=True
            )
        return self._execute("SELECT * FROM vulnerability_graph", fetchall=True)

    def export_credentials(self):
        return self._execute("SELECT * FROM credentials_sink", fetchall=True)

    def get_target_count(self):
        row = self._execute("SELECT COUNT(*) FROM target_grid", fetch=True)
        return row[0] if row else 0

    def get_vuln_count(self):
        row = self._execute("SELECT COUNT(*) FROM vulnerability_graph", fetch=True)
        return row[0] if row else 0


db = TacticalDatabase()
