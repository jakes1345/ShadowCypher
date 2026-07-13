"""
Knowledge Graph — Tactical Intelligence Database (F-5).

Replaces mem0/Qdrant with a sovereign SQLite-backed relationship graph.
Maps: Targets ↔ Services ↔ CVEs ↔ Exploits ↔ Missions ↔ Credentials.

Query example:
    from shadowcypher.core.knowledge_graph import kg
    kg.add_target("192.168.1.1", tags=["web", "internal"])
    kg.link("192.168.1.1", "CVE-2023-44487", "VULNERABLE_TO", score=9.8)
    attack_path = kg.shortest_path("192.168.1.1", "DOMAIN_ADMIN")
"""

import json
import os
import sqlite3
import threading
import time
from typing import Optional

from shadowcypher.core.logger import logger

DB_PATH = os.path.expanduser("~/.shadowcypher/knowledge_graph.db")


def _resolve_db_path(db_path: str) -> str:
    """Return a writable DB path.

    The default lives under the operator's home. If that resolves to a
    read-only location (e.g. ~ expanding to root-owned /opt on the live ISO),
    fall back to XDG data home and finally the temp dir so the graph — and the
    whole app import chain — never crashes on a permission error.
    """
    import tempfile

    candidates = [db_path]
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    candidates.append(os.path.join(xdg_data, "shadowcypher", "knowledge_graph.db"))
    candidates.append(os.path.join(tempfile.gettempdir(), "shadowcypher", "knowledge_graph.db"))
    for cand in candidates:
        try:
            os.makedirs(os.path.dirname(cand), exist_ok=True)
            probe = os.path.join(os.path.dirname(cand), ".write_test")
            with open(probe, "a"):
                pass
            os.remove(probe)
            return cand
        except OSError:
            continue
    return os.path.join(tempfile.gettempdir(), "shadowcypher_kg.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    label TEXT,
    props TEXT DEFAULT '{}',
    created REAL DEFAULT (unixepoch('now')),
    updated REAL DEFAULT (unixepoch('now'))
);
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    props TEXT DEFAULT '{}',
    created REAL DEFAULT (unixepoch('now')),
    FOREIGN KEY(src) REFERENCES nodes(id),
    FOREIGN KEY(dst) REFERENCES nodes(id)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(rel);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
"""

NODE_TYPES = {
    "TARGET",
    "SERVICE",
    "CVE",
    "EXPLOIT",
    "MISSION",
    "CREDENTIAL",
    "DOMAIN",
    "USER",
    "HOST",
    "NETWORK",
    "PAYLOAD",
    "TECHNIQUE",
}
EDGE_TYPES = {
    "RUNS",
    "VULNERABLE_TO",
    "EXPLOITED_BY",
    "PART_OF",
    "OWNS",
    "LATERAL_TO",
    "MEMBER_OF",
    "CONNECTS_TO",
    "FOUND_ON",
    "USED_IN",
    "MAPS_TO",
}


class KnowledgeGraph:
    """Sovereign tactical intelligence graph. Thread-safe, zero-telemetry."""

    def __init__(self, db_path: str = DB_PATH):
        db_path = _resolve_db_path(db_path)
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        logger.info("kg", f"Knowledge Graph loaded: {db_path}")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ── Node Operations ──────────────────────────────────────────────────────

    def add_node(self, node_id: str, node_type: str, label: str = "", props: Optional[dict] = None) -> bool:
        """Add or update a node in the graph."""
        node_type = node_type.upper()
        props_json = json.dumps(props or {})
        with self._lock, self._conn() as c:
            c.execute(
                """
                INSERT INTO nodes(id, type, label, props, updated)
                VALUES(?,?,?,?,unixepoch('now'))
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type, label=excluded.label,
                    props=excluded.props, updated=unixepoch('now')
            """,
                (node_id, node_type, label or node_id, props_json),
            )
        return True

    # Convenience shortcuts
    def add_target(self, ip: str, tags: Optional[list] = None, **props):
        self.add_node(ip, "TARGET", props={"tags": tags or [], **props})

    def add_cve(self, cve_id: str, score: float = 0.0, severity: str = "", desc: str = "", **props):
        self.add_node(cve_id, "CVE", props={"score": score, "severity": severity, "description": desc[:200], **props})

    def add_service(self, service_id: str, port: int = 0, proto: str = "", version: str = "", **props):
        self.add_node(service_id, "SERVICE", props={"port": port, "proto": proto, "version": version, **props})

    def add_credential(self, cred_id: str, username: str = "", source: str = "", hash_type: str = "", **props):
        self.add_node(
            cred_id, "CREDENTIAL", props={"username": username, "source": source, "hash_type": hash_type, **props}
        )

    def add_mission(self, mission_id: str, target: str = "", stage: str = "", **props):
        self.add_node(mission_id, "MISSION", props={"target": target, "stage": stage, **props})

    # ── Edge Operations ──────────────────────────────────────────────────────

    def link(self, src: str, dst: str, rel: str, weight: float = 1.0, **props) -> int:
        """Create a directed edge between two nodes."""
        with self._lock, self._conn() as c:
            cur = c.execute(
                """
                INSERT INTO edges(src, dst, rel, weight, props)
                VALUES(?,?,?,?,?)
            """,
                (src, dst, rel.upper(), weight, json.dumps(props)),
            )
            return cur.lastrowid or 0

    def unlink(self, src: str, dst: str, rel: Optional[str] = None):
        """Remove edges between src and dst (optionally filtered by rel)."""
        with self._lock, self._conn() as c:
            if rel:
                c.execute("DELETE FROM edges WHERE src=? AND dst=? AND rel=?", (src, dst, rel.upper()))
            else:
                c.execute("DELETE FROM edges WHERE src=? AND dst=?", (src, dst))

    # ── Query Operations ─────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[dict]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["props"] = json.loads(d["props"])
        return d

    def neighbors(self, node_id: str, rel: Optional[str] = None, direction: str = "out") -> list[dict]:
        """Get neighboring nodes. direction: 'out'|'in'|'both'"""
        with self._conn() as c:
            if direction == "out":
                q = "SELECT e.*, n.type, n.label FROM edges e JOIN nodes n ON e.dst=n.id WHERE e.src=?"
                params = [node_id]
            elif direction == "in":
                q = "SELECT e.*, n.type, n.label FROM edges e JOIN nodes n ON e.src=n.id WHERE e.dst=?"
                params = [node_id]
            else:
                if rel:
                    q = """SELECT e.*, n.type, n.label FROM edges e
                           JOIN nodes n ON (e.dst=n.id AND e.src=?) WHERE e.rel=?
                           UNION
                           SELECT e.*, n.type, n.label FROM edges e
                           JOIN nodes n ON (e.src=n.id AND e.dst=?) WHERE e.rel=?"""
                    params = [node_id, rel.upper(), node_id, rel.upper()]
                else:
                    q = """SELECT e.*, n.type, n.label FROM edges e
                           JOIN nodes n ON (e.dst=n.id AND e.src=?)
                           UNION
                           SELECT e.*, n.type, n.label FROM edges e
                           JOIN nodes n ON (e.src=n.id AND e.dst=?)"""
                    params = [node_id, node_id]
            rows = c.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def find_by_type(self, node_type: str, limit: int = 100) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM nodes WHERE type=? ORDER BY updated DESC LIMIT ?", (node_type.upper(), limit)
            ).fetchall()
        return [{**dict(r), "props": json.loads(r["props"])} for r in rows]

    def search(self, keyword: str, node_type: Optional[str] = None) -> list[dict]:
        with self._conn() as c:
            if node_type:
                rows = c.execute(
                    "SELECT * FROM nodes WHERE type=? AND (id LIKE ? OR label LIKE ? OR props LIKE ?)",
                    (node_type.upper(), f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM nodes WHERE id LIKE ? OR label LIKE ? OR props LIKE ?",
                    (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
                ).fetchall()
        return [{**dict(r), "props": json.loads(r["props"])} for r in rows]

    def shortest_path(self, start: str, end: str, max_depth: int = 6) -> list[str]:
        """BFS shortest path between two nodes."""
        from collections import deque

        visited = {start}
        queue = deque([[start]])
        with self._conn() as c:
            while queue:
                path = queue.popleft()
                node = path[-1]
                if node == end:
                    return path
                if len(path) >= max_depth:
                    continue
                rows = c.execute("SELECT dst FROM edges WHERE src=?", (node,)).fetchall()
                for row in rows:
                    nxt = row["dst"]
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(path + [nxt])
        return []

    def get_attack_surface(self, target: str) -> dict:
        """Return full attack surface for a target node."""
        services = self.neighbors(target, rel="RUNS")
        cves = self.neighbors(target, rel="VULNERABLE_TO")
        creds = self.neighbors(target, rel="OWNS")
        return {
            "target": target,
            "services": services,
            "cves": sorted(cves, key=lambda x: x.get("weight", 0), reverse=True),
            "credentials": creds,
            "total_risk_score": sum(e.get("weight", 0) for e in cves),
        }

    def ingest_red_team_mission(self, ctx) -> int:
        """Bulk-ingest a MissionContext from adversary_sim into the graph."""
        from shadowcypher.core.mitre import mitre as _mitre

        count = 0
        self.add_mission(ctx.mission_id, target=ctx.target, stage=ctx.stage)
        self.add_target(ctx.target)
        self.link(ctx.mission_id, ctx.target, "PART_OF")

        for p in ctx.open_ports:
            svc_id = f"{ctx.target}:{p['port']}/{p['proto']}"
            self.add_service(svc_id, port=p["port"], proto=p["proto"], version=p.get("version", ""))
            self.link(ctx.target, svc_id, "RUNS")
            count += 1

        for cve in ctx.cve_matches:
            self.add_cve(cve.cve_id, score=cve.cvss_score, severity=cve.cvss_severity, desc=cve.description)
            self.link(ctx.target, cve.cve_id, "VULNERABLE_TO", weight=cve.cvss_score)
            # Tag CVE with ATT&CK techniques
            for t in _mitre.from_finding(cve.description):
                self.add_node(
                    t["id"], "TECHNIQUE", label=t["name"],
                    props={"tactic": t["tactic"], "tactic_id": t["tactic_id"], "url": t["url"]},
                )
                self.link(cve.cve_id, t["id"], "MAPS_TO")
            count += 1

        # Tag nuclei/nikto findings
        for finding in getattr(ctx, "vuln_findings", []):
            for t in _mitre.from_finding(finding):
                self.add_node(
                    t["id"], "TECHNIQUE", label=t["name"],
                    props={"tactic": t["tactic"], "tactic_id": t["tactic_id"], "url": t["url"]},
                )
                self.link(ctx.target, t["id"], "MAPS_TO")

        # Tag tools exercised during the mission
        tools_used = ["nmap_service", "cve_intel", "http_probe", "nuclei", "nikto"]
        seen_techniques: set[str] = set()
        for tool_key in tools_used:
            for t in _mitre.tag(tool_key):
                if t["id"] not in seen_techniques:
                    self.add_node(
                        t["id"],
                        "TECHNIQUE",
                        label=t["name"],
                        props={"tactic": t["tactic"], "tactic_id": t["tactic_id"], "url": t["url"]},
                    )
                    self.link(ctx.mission_id, t["id"], "MAPS_TO")
                    seen_techniques.add(t["id"])

        logger.info("kg", f"Ingested mission {ctx.mission_id}: {count} nodes/edges added")
        return count

    def ingest_threat_intel(self, result) -> int:
        """Ingest a ThreatResult from threat_intel.py into the graph."""
        count = 0
        node_type = {"ip": "TARGET", "domain": "DOMAIN", "hash": "PAYLOAD"}.get(result.target_type, "TARGET")
        self.add_node(
            result.target,
            node_type,
            label=result.target,
            props={
                "malicious": result.malicious,
                "confidence": result.confidence,
                "abuse_score": result.abuse_score,
                "otx_pulses": result.pulses,
                "country": result.country,
                "isp": result.isp,
                "tags": result.tags[:10],
                "sources": result.sources,
            },
        )
        count += 1
        if result.malicious:
            self.add_node("THREAT_INTEL", "MISSION", label="Threat Intel")
            self.link(result.target, "THREAT_INTEL", "FOUND_ON", weight=result.confidence / 100.0)
            count += 1
        return count

    def stats(self) -> dict:
        with self._conn() as c:
            nodes = c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edges = c.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            types = c.execute("SELECT type, COUNT(*) as n FROM nodes GROUP BY type").fetchall()
        return {"nodes": nodes, "edges": edges, "by_type": {r["type"]: r["n"] for r in types}}

    def export_json(self, path: str):
        with self._conn() as c:
            nodes = [dict(r) for r in c.execute("SELECT * FROM nodes").fetchall()]
            edges = [dict(r) for r in c.execute("SELECT * FROM edges").fetchall()]
        with open(path, "w") as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2)
        logger.info("kg", f"Graph exported: {path}")


kg = KnowledgeGraph()
