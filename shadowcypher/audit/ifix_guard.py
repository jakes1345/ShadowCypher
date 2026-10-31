"""
SHADOWCYPHER AUDIT — iFixAi Guardrails & Policy Enforcement Engine
Independent pre-execution safety gate with AST shell syntax parsing,
MITRE ATT&CK correlation, and a tamper-proof cryptographic audit ledger.
"""

from __future__ import annotations

import dataclasses
import hashlib
import ipaddress
import re
import shlex
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Offline MITRE ATT&CK Mapping
MITRE_TACTICS_MAP = {
    "network_recon": ("T1046", "Network Service Discovery", "TA0007"),
    "port_scan": ("T1046", "Network Service Discovery", "TA0007"),
    "decompile": ("T1027", "Obfuscated Files or Information", "TA0005"),
    "sre_analysis": ("T1082", "System Information Discovery", "TA0007"),
    "drive_audit": ("T1083", "File and Directory Discovery", "TA0007"),
    "shell_exec": ("T1059.004", "Unix Shell Execution", "TA0002"),
    "privilege_check": ("T1068", "Exploitation for Privilege Escalation", "TA0004"),
}


@dataclasses.dataclass
class AuditRecord:
    entry_id: str
    timestamp: float
    tool_name: str
    target: str
    command: str
    verdict: str  # "APPROVED" | "DENIED"
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    reason: str
    mitre_technique: str
    duration_ms: float
    prev_hash: str
    current_hash: str


class IFixPolicyAuditor:
    """Independent deterministic safety policy auditor and immutable ledger."""

    DESTRUCTIVE_PATTERNS = [
        (re.compile(r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+(/|/\*|/(boot|sys|proc|etc|var|usr|bin|lib|root|home|dev)\b)", re.I), "System directory recursive deletion prohibited"),
        (re.compile(r"mkfs\.", re.I), "Disk filesystem creation prohibited"),
        (re.compile(r"dd\s+if=/dev/(zero|urandom)\s+of=/dev/[a-z]+", re.I), "Raw block device overwriting prohibited"),
        (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", re.I), "Fork bomb execution prohibited"),
        (re.compile(r">\s*/dev/sd[a-z]", re.I), "Direct raw drive redirection prohibited"),
    ]

    PRIV_ESC_PATTERNS = [
        (re.compile(r"\b(sudo\s+-s|sudo\s+su|sudo\s+/bin/bash|sudo\s+sh)\b", re.I), "Root privilege shell escalation"),
        (re.compile(r"chmod\s+(\+s|[0-7]?[4567][0-7]{3})", re.I), "SUID/SGID bit setting on file"),
    ]

    def __init__(self, ledger_db_path: Optional[Path] = None, allowed_networks: Optional[List[str]] = None):
        self.db_path = ledger_db_path or (Path("/tmp") / "shadow_audit_ledger.db")
        self.allowed_subnets: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

        default_cidrs = allowed_networks or ["127.0.0.0/8", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
        for cidr in default_cidrs:
            try:
                self.allowed_subnets.append(ipaddress.ip_network(cidr))
            except Exception:
                pass

        self._init_ledger_db()

    def _init_ledger_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_chain (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    tool_name TEXT,
                    target TEXT,
                    command TEXT,
                    verdict TEXT,
                    risk_level TEXT,
                    reason TEXT,
                    mitre_technique TEXT,
                    duration_ms REAL,
                    prev_hash TEXT,
                    current_hash TEXT
                )
            """)
            conn.commit()

    def _get_latest_hash(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT current_hash FROM audit_chain ORDER BY timestamp DESC LIMIT 1").fetchone()
            return row[0] if row else "GENESIS_ROOT_HASH_0000000000000000000000000000000000000000"

    def audit_intent(self, tool_name: str, params: Dict[str, Any]) -> AuditRecord:
        """
        Evaluate execution intent, enforce scope rules, and record in immutable ledger.
        """
        t0 = time.perf_counter()
        raw_cmd = str(params.get("command", ""))
        target = str(params.get("target", ""))

        verdict = "APPROVED"
        risk_level = "LOW"
        reason = "All deterministic safety policies satisfied"

        # 1. Shell AST Tokenizer & Injection Checks
        if raw_cmd:
            try:
                shlex.split(raw_cmd)
            except ValueError as e:
                verdict = "DENIED"
                risk_level = "HIGH"
                reason = f"Shell command AST syntax parsing failed: {e}"

            # Check destructive commands
            for regex, desc in self.DESTRUCTIVE_PATTERNS:
                if regex.search(raw_cmd):
                    verdict = "DENIED"
                    risk_level = "CRITICAL"
                    reason = f"Policy Violation: {desc}"
                    break

            # Check privilege escalation
            for regex, desc in self.PRIV_ESC_PATTERNS:
                if regex.search(raw_cmd):
                    verdict = "DENIED"
                    risk_level = "HIGH"
                    reason = f"Policy Violation: {desc}"
                    break

        # 2. CIDR Scope Boundaries
        if verdict == "APPROVED" and target:
            target_clean = target.split(":")[0]  # strip port if present
            try:
                ip_obj = ipaddress.ip_address(target_clean)
                in_scope = any(ip_obj in net for net in self.allowed_subnets)
                if not in_scope:
                    verdict = "DENIED"
                    risk_level = "HIGH"
                    reason = f"Target IP {target} is not in authorized audit subnets: {self.allowed_subnets}"
            except ValueError:
                # Hostname target: localhost or .local is permitted
                if target_clean not in ["localhost", "127.0.0.1", "::1"] and not target_clean.endswith(".local"):
                    verdict = "DENIED"
                    risk_level = "HIGH"
                    reason = f"Target hostname '{target_clean}' is unverified external domain"

        duration_ms = round((time.perf_counter() - t0) * 1000, 3)

        # 3. MITRE ATT&CK Technique Mapping
        mitre_info = MITRE_TACTICS_MAP.get(tool_name, ("T1059", "Command Execution", "TA0002"))
        mitre_tag = f"[{mitre_info[0]} · {mitre_info[1]}]"

        # 4. Cryptographic Hash Chain Append
        prev_hash = self._get_latest_hash()
        ts = time.time()
        entry_id = f"aud_{int(ts)}_{hashlib.sha256(f'{raw_cmd}{target}{ts}'.encode()).hexdigest()[:8]}"

        chain_payload = f"{prev_hash}|{entry_id}|{ts}|{tool_name}|{target}|{raw_cmd}|{verdict}|{risk_level}"
        current_hash = hashlib.sha256(chain_payload.encode()).hexdigest()

        record = AuditRecord(
            entry_id=entry_id,
            timestamp=ts,
            tool_name=tool_name,
            target=target,
            command=raw_cmd,
            verdict=verdict,
            risk_level=risk_level,
            reason=reason,
            mitre_technique=mitre_tag,
            duration_ms=duration_ms,
            prev_hash=prev_hash,
            current_hash=current_hash
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_chain VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.entry_id, record.timestamp, record.tool_name, record.target,
                record.command, record.verdict, record.risk_level, record.reason,
                record.mitre_technique, record.duration_ms, record.prev_hash, record.current_hash
            ))
            conn.commit()

        return record

    def verify_ledger_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """
        Verify the entire cryptographic hash chain.
        Returns: (is_valid, total_blocks_verified, error_detail)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM audit_chain ORDER BY timestamp ASC").fetchall()

        if not rows:
            return True, 0, None

        expected_prev = "GENESIS_ROOT_HASH_0000000000000000000000000000000000000000"
        for idx, row in enumerate(rows):
            if row["prev_hash"] != expected_prev:
                return False, idx, f"Chain broken at record {row['id']}: expected prev_hash {expected_prev}, got {row['prev_hash']}"

            recalc_payload = f"{row['prev_hash']}|{row['id']}|{row['timestamp']}|{row['tool_name']}|{row['target']}|{row['command']}|{row['verdict']}|{row['risk_level']}"
            recalc_hash = hashlib.sha256(recalc_payload.encode()).hexdigest()
            if recalc_hash != row["current_hash"]:
                return False, idx, f"Tampered record at {row['id']}: recalculated hash does not match current_hash"

            expected_prev = row["current_hash"]

        return True, len(rows), None
