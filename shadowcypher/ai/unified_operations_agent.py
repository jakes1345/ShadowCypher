"""
UNIFIED CYBER-OPERATIONS & SRE ENGINE
Integrates the core capabilities of trending autonomous systems:
  - debpalash/VoiceStudio  -> Local Linux Audio / Voice Output Engine
  - mksglu/context-mode    -> Token-Sandboxed Output Vault & Memory
  - ifixai-ai/iFixAi       -> Deterministic Safety & Policy Gate (<120ms)
  - vxcontrol/pentagi      -> Autonomous Multi-Agent Recon & Scanner
  - morluto/rea + Ghidra   -> Headless ELF/Binary Decompiler & SRE
  - xtool-org/xtool        -> Cross-Platform Host & Drive Target Engine

Runs directly on any Linux filesystem, drive partition, or mounted storage (e.g. /media/jack/Liunux).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import math
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from shadowcypher.core.logger import logger
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    logger = logging.getLogger("UnifiedAgent")

# Deep Engineering Subsystems
from shadowcypher.audit.ifix_guard import IFixPolicyAuditor
from shadowcypher.context_vault.engine import AdvancedContextVault
from shadowcypher.orchestrator.pentagi_state_machine import AutonomousPentAGISystem, MissionTelemetry
from shadowcypher.sre.elf_parser import ELFParser
from shadowcypher.sre.vulnerability_scanner import BinaryVulnerabilityScanner

# ─────────────────────────────────────────────────────────────────────────────
# 1. Linux Drive Storage & Filesystem Verifier
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class DriveInfo:
    target_path: str
    resolved_mount: str
    total_gb: float
    free_gb: float
    used_percent: float
    is_writable: bool
    fs_type: str


class LinuxDriveEngine:
    """Manages drive targets, partition stats, and data persistence on Linux drives."""

    @staticmethod
    def inspect_drive(path_str: str) -> DriveInfo:
        target_path = Path(path_str).resolve()
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        # Check disk space using statvfs
        stat = os.statvfs(target_path)
        total_bytes = stat.f_blocks * stat.f_frsize
        free_bytes = stat.f_bavail * stat.f_frsize
        total_gb = round(total_bytes / (1024 ** 3), 2)
        free_gb = round(free_bytes / (1024 ** 3), 2)
        used_percent = round((1.0 - (free_bytes / max(total_bytes, 1))) * 100, 1)

        # Check write capability
        test_file = target_path / f".write_test_{int(time.time())}.tmp"
        is_writable = False
        try:
            test_file.write_text("test")
            test_file.unlink()
            is_writable = True
        except Exception:
            is_writable = False

        # Determine mount point
        mount_point = str(target_path)
        try:
            proc = subprocess.run(["df", "-T", str(target_path)], capture_output=True, text=True)
            lines = proc.stdout.strip().splitlines()
            fs_type = lines[1].split()[1] if len(lines) > 1 else "unknown"
            mount_point = lines[1].split()[-1] if len(lines) > 1 else str(target_path)
        except Exception:
            fs_type = "ext4"

        return DriveInfo(
            target_path=str(target_path),
            resolved_mount=mount_point,
            total_gb=total_gb,
            free_gb=free_gb,
            used_percent=used_percent,
            is_writable=is_writable,
            fs_type=fs_type
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Context-Mode Sandboxing Vault (inspired by mksglu/context-mode)
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class SandboxedArtifact:
    storage_id: str
    tool_name: str
    raw_size_bytes: int
    compressed_summary: str
    token_saving_pct: float
    content_hash: str


class ContextModeVault:
    """
    Sandboxes voluminous execution output (disassembly, packet dumps, logs)
    directly onto the Linux drive database and yields condensed semantic digests.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "context_vault.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    tool_name TEXT,
                    raw_content TEXT,
                    summary TEXT,
                    content_hash TEXT,
                    raw_bytes INTEGER
                )
            """)
            conn.commit()

    def store_and_compress(self, tool_name: str, raw_output: str, max_lines: int = 12) -> SandboxedArtifact:
        content_bytes = raw_output.encode("utf-8", errors="replace")
        raw_size = len(content_bytes)
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        storage_id = f"ctx_{int(time.time())}_{content_hash[:8]}"

        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        total_lines = len(lines)

        priority_keywords = [
            "vulnerability", "cve", "critical", "high", "exploit", "password",
            "overflow", "leak", "warning", "error", "entry point", "function"
        ]
        priority_lines = [line for line in lines if any(k in line.lower() for k in priority_keywords)]

        selected_lines = priority_lines[:max_lines] if priority_lines else lines[:max_lines]
        summary_text = (
            f"[CONTEXT-SANDBOX ARTIFACT: {storage_id}]\n"
            f"Tool: {tool_name} | Total Lines: {total_lines} | Raw Size: {raw_size}B\n"
            f"Extracted Highlights:\n" + ("\n".join(f"  • {line}" for line in selected_lines))
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (storage_id, time.time(), tool_name, raw_output, summary_text, content_hash, raw_size)
            )
            conn.commit()

        savings = max(0.0, 1.0 - (len(summary_text) / max(raw_size, 1)))
        return SandboxedArtifact(
            storage_id=storage_id,
            tool_name=tool_name,
            raw_size_bytes=raw_size,
            compressed_summary=summary_text,
            token_saving_pct=round(savings * 100, 2),
            content_hash=content_hash
        )

    def retrieve_raw(self, storage_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT raw_content FROM artifacts WHERE id = ?", (storage_id,)).fetchone()
            return row[0] if row else None

    def search_artifacts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search sandboxed artifacts by keyword across summaries, tool names, or content."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            pattern = f"%{query}%"
            rows = cursor.execute("""
                SELECT id, timestamp, tool_name, summary, content_hash, raw_bytes
                FROM artifacts
                WHERE tool_name LIKE ? OR summary LIKE ? OR raw_content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (pattern, pattern, pattern, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_artifact(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details and raw contents for an artifact by Vault ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM artifacts WHERE id = ?", (storage_id,)).fetchone()
            return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Independent Pre-Execution Policy Gate (inspired by ifixai-ai/iFixAi)
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class PolicyVerdict:
    allowed: bool
    risk: str
    audit_duration_ms: float
    rule_matched: str


class IFixAiSafetyGate:
    """Enforces strict pre-execution guardrails and halts out-of-scope or destructive actions."""

    DESTRUCTIVE_RULES = [
        (re.compile(r"rm\s+-rf\s+/(?!\w)", re.I), "Host-level filesystem wipe forbidden"),
        (re.compile(r"mkfs\.", re.I), "Disk format operation prohibited"),
        (re.compile(r"dd\s+if=/dev/zero", re.I), "Raw block zeroing prohibited"),
        (re.compile(r":\(\)\s*\{", re.I), "Fork-bomb syntax detected"),
    ]

    def __init__(self, allowed_cidrs: Optional[List[str]] = None):
        self.allowed_cidrs = allowed_cidrs or ["127.0.0.1", "localhost", "192.168.*", "10.*"]

    def audit_plan(self, action_name: str, payload: Dict[str, Any]) -> PolicyVerdict:
        t0 = time.perf_counter()
        raw_cmd = str(payload.get("command", ""))

        for regex, desc in self.DESTRUCTIVE_RULES:
            if regex.search(raw_cmd):
                return PolicyVerdict(
                    allowed=False,
                    risk="CRITICAL",
                    audit_duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                    rule_matched=desc
                )

        target = str(payload.get("target", ""))
        if target:
            scoped = any(re.match(re.escape(c).replace(r"\*", ".*"), target) for c in self.allowed_cidrs)
            if not scoped:
                return PolicyVerdict(
                    allowed=False,
                    risk="HIGH",
                    audit_duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                    rule_matched=f"Target '{target}' is outside permitted CIDR scope"
                )

        return PolicyVerdict(
            allowed=True,
            risk="LOW",
            audit_duration_ms=round((time.perf_counter() - t0) * 1000, 3),
            rule_matched="Action passed all audit verification checks"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Binary Reverse Engineering & SRE Engine (inspired by morluto/rea + Ghidra)
# ─────────────────────────────────────────────────────────────────────────────

class BinaryReverseEngineer:
    """
    Deconstructs Linux binaries (ELF), libraries (.so), or raw executables
    found on the target drive using system utilities and signature heuristics.
    """

    @staticmethod
    def is_elf_binary(file_path: Path) -> bool:
        if not file_path.is_file() or file_path.is_symlink():
            return False
        try:
            with open(file_path, "rb") as f:
                magic = f.read(4)
                return magic == b"\x7fELF"
        except Exception:
            return False

    @staticmethod
    def calculate_entropy(data: bytes) -> float:
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        freq: Dict[int, int] = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return round(entropy, 3)

    def analyze_binary(self, binary_path: Path) -> Dict[str, Any]:
        stat = binary_path.stat()
        with open(binary_path, "rb") as f:
            head_bytes = f.read(65536)
            f.seek(0)
            full_sha256 = hashlib.sha256(f.read()).hexdigest()

        entropy = self.calculate_entropy(head_bytes)
        is_packed = entropy > 7.2

        # 1. Run readelf for ELF header analysis
        elf_header: Dict[str, str] = {}
        try:
            proc = subprocess.run(["readelf", "-h", str(binary_path)], capture_output=True, text=True, timeout=5)
            for line in proc.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    elf_header[k.strip()] = v.strip()
        except Exception as e:
            elf_header["error"] = str(e)

        # 2. Run strings to detect hardcoded secrets & command sinks
        dangerous_sinks = []
        suspicious_strings = []
        try:
            str_proc = subprocess.run(["strings", "-a", str(binary_path)], capture_output=True, text=True, timeout=8)
            for s in str_proc.stdout.splitlines():
                s_strip = s.strip()
                if any(w in s_strip.lower() for w in ["password", "secret", "private_key", "bearer ", "token="]):
                    suspicious_strings.append(s_strip[:100])
                if any(w in s_strip for w in ["system", "popen", "execve", "eval", "/bin/sh", "/bin/bash"]):
                    dangerous_sinks.append(s_strip[:100])
        except Exception:
            pass

        # 3. Disassembly text sample via objdump (builds internal state; result not returned)
        try:
            dump_proc = subprocess.run(
                ["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(binary_path)],
                capture_output=True, text=True, timeout=8
            )
            _ = [line for line in dump_proc.stdout.splitlines() if line.strip() and not line.startswith("Disassembly")]
        except Exception:
            pass

        return {
            "binary_name": binary_path.name,
            "path": str(binary_path),
            "size_bytes": stat.st_size,
            "sha256": full_sha256,
            "entropy": entropy,
            "likely_packed_or_encrypted": is_packed,
            "architecture": elf_header.get("Machine", "Unknown"),
            "entry_point": elf_header.get("Entry point address", "Unknown"),
            "dangerous_sinks": list(set(dangerous_sinks))[:15],
            "flagged_strings": list(set(suspicious_strings))[:15],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4b. Headless Ghidra & Native Decompiler Bridge (NSA Ghidra + rea)
# ─────────────────────────────────────────────────────────────────────────────

class GhidraHeadlessDecompilerBridge:
    """
    Automated Headless Binary Decompiler.
    - Primary Engine: NSA Ghidra headless analyzer (analyzeHeadless) via Java post-script.
    - Native SRE Fallback: High-speed native Linux decompiler (radare2 / r2ghidra compatible)
      extracting real C pseudocode, control flow, and symbol cross-references.
    """

    def __init__(self, script_path: Optional[Path] = None):
        self.script_path = script_path or (Path(__file__).parent / "scripts" / "ExportDecompiledCode.java")
        self.ghidra_home = os.environ.get("GHIDRA_HOME") or os.environ.get("GHIDRA_INSTALL_DIR")
        self.analyze_headless_bin = self._find_headless_bin()

    def _find_headless_bin(self) -> Optional[str]:
        if self.ghidra_home and os.path.isdir(self.ghidra_home):
            candidate = Path(self.ghidra_home) / "support" / "analyzeHeadless"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        which_proc = subprocess.run(["which", "analyzeHeadless"], capture_output=True, text=True)
        if which_proc.returncode == 0 and which_proc.stdout.strip():
            return which_proc.stdout.strip()
        return None

    def decompile_binary(self, binary_path: Path, max_functions: int = 5) -> Dict[str, Any]:
        """Decompile the target binary to C pseudocode."""
        if self.analyze_headless_bin and self.script_path.exists():
            return self._decompile_ghidra(binary_path)
        return self._decompile_native_sre(binary_path, max_functions)

    def _decompile_ghidra(self, binary_path: Path) -> Dict[str, Any]:
        temp_dir = Path("/tmp") / f"ghidra_proj_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        out_c = temp_dir / "decompiled_output.c"
        try:
            cmd = [
                self.analyze_headless_bin,
                str(temp_dir), "TempProj",
                "-import", str(binary_path),
                "-scriptPath", str(self.script_path.parent),
                "-postScript", self.script_path.name, str(out_c),
                "-deleteProject"
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            c_code = out_c.read_text(errors="replace") if out_c.exists() else proc.stdout
            return {
                "engine": "NSA Ghidra Headless Analyzer",
                "binary": str(binary_path),
                "c_pseudocode": c_code,
                "lines_count": len(c_code.splitlines())
            }
        except Exception as e:
            fallback = self._decompile_native_sre(binary_path)
            fallback["ghidra_error"] = str(e)
            return fallback
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _decompile_native_sre(self, binary_path: Path, max_functions: int = 5) -> Dict[str, Any]:
        """Fast headless C pseudocode decompilation via Linux native SRE."""
        try:
            f_proc = subprocess.run(
                ["r2", "-q", "-c", "aaa; afl", str(binary_path)],
                capture_output=True, text=True, timeout=15
            )
            func_lines = [line for line in f_proc.stdout.splitlines() if line.strip()]
            candidates = []
            for line in func_lines:
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[3]
                    addr = parts[0]
                    if not name.startswith("sym.imp.") and ("main" in name or "entry" in name or "fcn." in name):
                        candidates.append((addr, name))

            if not candidates:
                candidates = [("entry0", "entry0")]

            decompiled_blocks = []
            for addr, name in candidates[:max_functions]:
                p = subprocess.run(
                    ["r2", "-q", "-c", f"aaa; s {addr}; pdc", str(binary_path)],
                    capture_output=True, text=True, timeout=10
                )
                decompiled_blocks.append(
                    f"// =========================================================================\n"
                    f"// Function: {name} @ {addr}\n"
                    f"// =========================================================================\n"
                    + p.stdout.strip()
                )

            full_c = "\n\n".join(decompiled_blocks)
            return {
                "engine": "Linux Native SRE Decompiler (r2ghidra / pdc)",
                "binary": str(binary_path),
                "c_pseudocode": full_c,
                "functions_decompiled": len(decompiled_blocks),
                "lines_count": len(full_c.splitlines())
            }
        except Exception as e:
            return {"engine": "Native SRE", "error": str(e), "c_pseudocode": f"// Decompilation failed: {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Autonomous Reconnaissance & Scanner (inspired by PentAGI)
# ─────────────────────────────────────────────────────────────────────────────

class AutonomousReconScanner:
    """Performs localized port scanning and network service fingerprinting."""

    COMMON_PORTS = [21, 22, 23, 25, 53, 80, 111, 443, 8080, 8443, 9000]

    @classmethod
    def scan_host(cls, target_host: str, timeout: float = 0.5) -> Dict[str, Any]:
        open_ports: List[Dict[str, Any]] = []
        try:
            target_ip = socket.gethostbyname(target_host)
        except Exception as e:
            return {"error": f"Failed to resolve host '{target_host}': {e}"}

        for port in cls.COMMON_PORTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                res = s.connect_ex((target_ip, port))
                if res == 0:
                    banner = ""
                    try:
                        s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                        banner = s.recv(128).decode("utf-8", errors="ignore").strip().splitlines()[0]
                    except Exception:
                        pass
                    open_ports.append({"port": port, "banner": banner})
            except Exception:
                pass
            finally:
                s.close()

        return {
            "target": target_host,
            "ip": target_ip,
            "open_ports": open_ports,
            "scanned_ports_count": len(cls.COMMON_PORTS)
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Local Linux Voice Interface (inspired by debpalash/VoiceStudio)
# ─────────────────────────────────────────────────────────────────────────────

class LocalLinuxVoiceInterface:
    """Provides non-blocking local tactical speech output without any cloud dependencies."""

    @staticmethod
    def speak(text: str) -> None:
        logger.info(f"[TACTICAL VOICE] {text}")
        speech_cmd = None
        for binary, args in [
            ("spd-say", ["spd-say", "-r", "10", text]),
            ("espeak-ng", ["espeak-ng", text]),
            ("espeak", ["espeak", text])
        ]:
            if subprocess.run(["which", binary], capture_output=True).returncode == 0:
                speech_cmd = args
                break

        if speech_cmd:
            try:
                subprocess.Popen(
                    speech_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 7. Unified Operations Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class UnifiedCyberAgent:
    """The unified orchestrator combining all capabilities onto the Linux drive."""

    def __init__(self, drive_path: str = "/tmp/shadow_drive"):
        self.drive_info = LinuxDriveEngine.inspect_drive(drive_path)
        logger.info(f"Target Linux Drive initialized: {self.drive_info.resolved_mount} ({self.drive_info.fs_type}, {self.drive_info.free_gb}GB free)")

        # Create vault dir on drive or fallback
        vault_dir = Path(self.drive_info.target_path) / ".shadow_context_vault"
        if not self.drive_info.is_writable:
            fallback_dir = Path(os.environ.get("SHADOW_VAULT_DIR", "/tmp/shadow_context_vault"))
            logger.warning(f"Drive {drive_path} is read-only. Setting vault in {fallback_dir}")
            vault_dir = fallback_dir

        self.vault = ContextModeVault(vault_dir)
        self.advanced_vault = AdvancedContextVault(vault_dir)
        self.safety = IFixAiSafetyGate()
        self.auditor = IFixPolicyAuditor(ledger_db_path=vault_dir / "audit_chain.db")
        self.sre = BinaryReverseEngineer()
        self.decompiler = GhidraHeadlessDecompilerBridge()
        self.recon = AutonomousReconScanner()
        self.voice = LocalLinuxVoiceInterface()
        self.pentagi = AutonomousPentAGISystem(drive_path=str(self.drive_info.target_path), vault_dir=str(vault_dir))

    def decompile_binary_target(self, binary_path: str, max_functions: int = 5) -> Dict[str, Any]:
        """Decompile an ELF executable or shared library into C pseudocode."""
        p = Path(binary_path)
        if not p.exists() or not p.is_file():
            return {"error": f"Binary target '{binary_path}' not found"}

        self.voice.speak(f"Decompiling binary target {p.name}")
        decomp_result = self.decompiler.decompile_binary(p, max_functions=max_functions)

        # Sandbox the entire decompiled C source into Advanced Context Vault
        c_code = decomp_result.get("c_pseudocode", "")
        art_id = self.advanced_vault.store_and_sandbox(f"decompile_{p.name}", f"C Decompilation for {p.name}", c_code)
        sliced = self.advanced_vault.slice_context_window(art_id, max_token_budget=600)

        self.voice.speak(f"Decompilation complete for {p.name}. Saved to context vault.")
        return {
            "binary": str(p),
            "engine": decomp_result.get("engine"),
            "functions_decompiled": decomp_result.get("functions_decompiled", 1),
            "lines_decompiled": decomp_result.get("lines_count", 0),
            "vault_id": art_id,
            "token_savings": f"{sliced.token_saving_pct}%",
            "c_pseudocode_preview": "\n".join(c_code.splitlines()[:35]),
            "full_c_pseudocode": c_code
        }

    def audit_drive_binaries(self, search_dir: str, max_binaries: int = 5) -> List[Dict[str, Any]]:
        self.voice.speak(f"Scanning Linux drive at {search_dir} for native binaries")
        root = Path(search_dir)
        results = []
        if not root.exists():
            return [{"error": f"Search directory '{search_dir}' does not exist"}]

        found_count = 0
        for current_dir, _, files in os.walk(root):
            for file_name in files:
                p = Path(current_dir) / file_name
                if self.sre.is_elf_binary(p):
                    # 1. Deep Binary Checksec
                    elf_parser = ELFParser(p)
                    elf_summary = elf_parser.get_summary()

                    # 2. Exploit Surface & ROP Gadgets
                    vuln_scanner = BinaryVulnerabilityScanner(elf_parser)
                    vuln_audit = vuln_scanner.full_audit()

                    full_sre = {
                        "binary": str(p),
                        "elf_summary": elf_summary,
                        "vulnerability_analysis": vuln_audit
                    }

                    # 3. Content-Addressed Storage & Context Slicing
                    art_id = self.advanced_vault.store_and_sandbox(
                        tool_name=f"sre_deep_{p.name}",
                        title=f"Binary SRE & Checksec for {p.name}",
                        raw_content=json.dumps(full_sre, indent=2)
                    )
                    sliced = self.advanced_vault.slice_context_window(art_id, max_token_budget=350)

                    results.append({
                        "binary": str(p),
                        "architecture": elf_summary["architecture"],
                        "checksec_score": elf_summary["checksec"]["security_score"],
                        "canary": elf_summary["checksec"]["canary"],
                        "nx": elf_summary["checksec"]["nx"],
                        "pie": elf_summary["checksec"]["pie"],
                        "relro": elf_summary["checksec"]["relro"],
                        "dangerous_sinks_count": vuln_audit["vulnerable_sinks_count"],
                        "rop_gadgets_count": vuln_audit["rop_gadgets_count"],
                        "vault_artifact_id": art_id,
                        "token_savings": f"{sliced.token_saving_pct}%"
                    })
                    found_count += 1
                    if found_count >= max_binaries:
                        break
            if found_count >= max_binaries:
                break

        self.voice.speak(f"Discovered and reverse engineered {found_count} binaries")
        return results

    def run_autonomous_mission(self, target_host: str = "127.0.0.1", target_binary: Optional[str] = "/bin/id", max_token_budget: int = 500) -> MissionTelemetry:
        """Run end-to-end multi-agent PentAGI mission."""
        self.voice.speak(f"Starting PentAGI autonomous mission on target {target_host}")
        telemetry = self.pentagi.run_mission(target_host=target_host, target_binary=target_binary, max_token_budget=max_token_budget)
        self.voice.speak(f"Mission finished with state {telemetry.current_state.value}")
        return telemetry

    def execute_network_recon(self, target: str) -> Dict[str, Any]:
        # Pre-execution safety audit via iFixAi Policy Auditor (cryptographic ledger)
        record = self.auditor.audit_intent("network_recon", {"target": target})
        if record.verdict != "APPROVED":
            self.voice.speak("Recon operation halted by safety gate")
            return {"status": "BLOCKED", "rule": record.reason, "time_ms": record.duration_ms, "audit_id": record.entry_id}

        self.voice.speak(f"Executing autonomous recon against target {target}")
        scan_raw = self.recon.scan_host(target)
        sandboxed = self.vault.store_and_compress("recon_scan", json.dumps(scan_raw, indent=2))

        return {
            "status": "APPROVED_AND_EXECUTED",
            "audit_ms": record.duration_ms,
            "target": target,
            "mitre_tag": record.mitre_technique,
            "audit_hash": record.current_hash[:16],
            "open_ports": scan_raw.get("open_ports", []),
            "token_savings": f"{sandboxed.token_saving_pct}%",
            "vault_id": sandboxed.storage_id
        }

    def search_vault(self, keyword: str) -> List[Dict[str, Any]]:
        """Search across all sandboxed artifacts stored in the Linux drive vault."""
        res = self.advanced_vault.search_artifacts(keyword)
        if not res:
            res = self.vault.search_artifacts(keyword)
        return res

    def query_vault(self, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full raw decompilation or tool execution payload for an artifact."""
        raw_cas = self.advanced_vault.retrieve_raw(storage_id)
        if not raw_cas:
            # Check default /tmp fallback vault if running with different drive arg
            fallback_v = AdvancedContextVault(vault_dir="/tmp/shadow_context_vault")
            raw_cas = fallback_v.retrieve_raw(storage_id)

        if raw_cas:
            return {
                "id": storage_id,
                "tool_name": "cas_artifact",
                "raw_bytes": len(raw_cas.encode("utf-8")),
                "content_hash": storage_id,
                "raw_content": raw_cas
            }
        return self.vault.get_artifact(storage_id)

    def watch_directory(self, watch_dir: str, poll_interval: float = 2.0, max_iterations: Optional[int] = None) -> None:
        """
        Continuously monitor a directory on the Linux drive for new or modified ELF binaries.
        Automatically triggers SRE, decompiles entrypoints, and records artifacts.
        """
        target_path = Path(watch_dir).resolve()
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        self.voice.speak(f"Daemon watching Linux drive directory {target_path.name}")
        logger.info(f"[WATCHER-DAEMON] Monitoring: {target_path} (polling every {poll_interval}s)")

        seen_files: Dict[str, float] = {}
        for p in target_path.glob("**/*"):
            if p.is_file() and not p.is_symlink():
                seen_files[str(p)] = p.stat().st_mtime

        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                time.sleep(poll_interval)
                iterations += 1
                current_files = [p for p in target_path.glob("**/*") if p.is_file() and not p.is_symlink()]
                for p in current_files:
                    path_str = str(p)
                    mtime = p.stat().st_mtime
                    if path_str not in seen_files or seen_files[path_str] < mtime:
                        seen_files[path_str] = mtime
                        if self.sre.is_elf_binary(p):
                            self.voice.speak(f"New binary detected: {p.name}. Decompiling.")
                            logger.info(f"[WATCHER-DAEMON] New ELF binary detected: {p}. Running automatic SRE...")
                            decomp = self.decompile_binary_target(path_str, max_functions=3)
                            logger.info(f"[WATCHER-DAEMON] Decompiled {p.name} -> Vault ID: {decomp.get('vault_id')}")
        except KeyboardInterrupt:
            logger.info("[WATCHER-DAEMON] Watch loop stopped by operator.")


# ─────────────────────────────────────────────────────────────────────────────
# 8. AgentTool & MCP Tool Registries (for Ollama AgentLoop & MCP Servers)
# ─────────────────────────────────────────────────────────────────────────────

try:
    from shadowcypher.ai.tool_loop import AgentTool
except Exception:
    @dataclasses.dataclass
    class AgentTool:
        name: str
        description: str
        parameters: Dict[str, Any]
        fn: Any
        requires_approval: bool = False


def agent_tool_to_mcp(tool: AgentTool, prefix: str = "shadowcypher_unified_") -> Tuple[str, Dict[str, Any]]:
    """Convert an AgentTool into an MCP server tool registry entry."""
    mcp_name = f"{prefix}{tool.name}" if not tool.name.startswith("shadowcypher_") else tool.name
    mcp_entry = {
        "description": tool.description,
        "inputSchema": tool.parameters,
        "handler": lambda params: tool.fn(**params)
    }
    return mcp_name, mcp_entry


def get_unified_agent_tools(agent: Optional[UnifiedCyberAgent] = None) -> List[AgentTool]:
    """Return AgentTool instances for Ollama AgentLoop integration."""
    u_agent = agent or UnifiedCyberAgent()
    return [
        AgentTool(
            name="unified_decompile",
            description="Decompile an ELF binary target on the Linux drive into C pseudocode using Ghidra or native Linux SRE.",
            parameters={
                "type": "object",
                "properties": {
                    "binary_path": {"type": "string", "description": "Absolute path to ELF executable or shared library"},
                    "max_functions": {"type": "integer", "description": "Maximum number of functions to decompile", "default": 5}
                },
                "required": ["binary_path"]
            },
            fn=lambda binary_path, max_functions=5: u_agent.decompile_binary_target(binary_path, max_functions=max_functions),
            requires_approval=False
        ),
        AgentTool(
            name="unified_drive_audit",
            description="Discover and reverse-engineer native ELF binaries on a target Linux directory or mounted partition.",
            parameters={
                "type": "object",
                "properties": {
                    "search_dir": {"type": "string", "description": "Directory path on Linux drive"},
                    "max_binaries": {"type": "integer", "description": "Max binaries to analyze", "default": 5}
                },
                "required": ["search_dir"]
            },
            fn=lambda search_dir, max_binaries=5: u_agent.audit_drive_binaries(search_dir, max_binaries=max_binaries),
            requires_approval=False
        ),
        AgentTool(
            name="unified_recon",
            description="Perform autonomous network reconnaissance and port scanning subject to safety audit policy.",
            parameters={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target hostname or IP address"}
                },
                "required": ["target"]
            },
            fn=lambda target: u_agent.execute_network_recon(target),
            requires_approval=True
        ),
        AgentTool(
            name="unified_vault_search",
            description="Search for stored decompilations, SRE analyses, and security artifacts in the Linux drive Context Vault.",
            parameters={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Search keyword, function name, or binary name"}
                },
                "required": ["keyword"]
            },
            fn=lambda keyword: u_agent.search_vault(keyword),
            requires_approval=False
        ),
        AgentTool(
            name="unified_vault_query",
            description="Retrieve full raw decompilation or tool execution payload for an artifact by Vault ID.",
            parameters={
                "type": "object",
                "properties": {
                    "storage_id": {"type": "string", "description": "Artifact Vault ID (e.g. ctx_...)"}
                },
                "required": ["storage_id"]
            },
            fn=lambda storage_id: u_agent.query_vault(storage_id),
            requires_approval=False
        ),
        AgentTool(
            name="unified_drive_inspect",
            description="Inspect Linux drive target filesystem, disk capacity, free space, and mount status.",
            parameters={
                "type": "object",
                "properties": {
                    "drive_path": {"type": "string", "description": "Mount path or directory", "default": "/tmp/shadow_drive"}
                }
            },
            fn=lambda drive_path="/tmp/shadow_drive": dataclasses.asdict(LinuxDriveEngine.inspect_drive(drive_path)),
            requires_approval=False
        ),
    ]


def get_unified_mcp_tools(agent: Optional[UnifiedCyberAgent] = None) -> Dict[str, Dict[str, Any]]:
    """Return dictionary of tools formatted for ShadowCypher MCP servers."""
    tools = get_unified_agent_tools(agent)
    mcp_dict: Dict[str, Dict[str, Any]] = {}
    for t in tools:
        name, entry = agent_tool_to_mcp(t, prefix="shadowcypher_")
        mcp_dict[name] = entry
    return mcp_dict


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Unified Cyber-Operations & SRE Engine on Linux Drives")
    parser.add_argument("--drive", default="/tmp/shadow_drive", help="Target Linux drive or mount path")
    parser.add_argument("--scan-binaries", help="Path on Linux drive to scan for ELF binaries")
    parser.add_argument("--decompile", help="Decompile specific ELF binary to C pseudocode")
    parser.add_argument("--functions", type=int, default=5, help="Max functions to decompile (default: 5)")
    parser.add_argument("--recon", help="Target host or IP for autonomous recon scan")
    parser.add_argument("--mission", action="store_true", help="Execute complete PentAGI autonomous mission")
    parser.add_argument("--target", default="127.0.0.1", help="Target host for autonomous mission (default: 127.0.0.1)")
    parser.add_argument("--binary", default="/bin/id", help="Target ELF binary for autonomous mission (default: /bin/id)")
    parser.add_argument("--budget", type=int, default=500, help="Max token budget for context vault slicing (default: 500)")
    parser.add_argument("--watch", help="Continuously monitor directory for new ELF binaries and auto-decompile")
    parser.add_argument("--watch-iterations", type=int, default=None, help="Limit watch iterations (for testing)")
    parser.add_argument("--query-vault", help="Retrieve full raw artifact by Vault ID")
    parser.add_argument("--search-vault", help="Search vault artifacts by keyword")
    parser.add_argument("--json", action="store_true", help="Output full JSON report")

    args = parser.parse_args()

    agent = UnifiedCyberAgent(drive_path=args.drive)

    if args.mission:
        telemetry = agent.run_autonomous_mission(
            target_host=args.target,
            target_binary=args.binary,
            max_token_budget=args.budget
        )
        if args.json:
            print(json.dumps(dataclasses.asdict(telemetry), indent=2))
        else:
            print("\n" + "=" * 65)
            print("       PENTAGI AUTONOMOUS MISSION TELEMETRY")
            print("=" * 65)
            print(f"Mission ID:       {telemetry.mission_id}")
            print(f"Target Host:      {telemetry.target_host}")
            print(f"Target Binary:    {telemetry.target_binary}")
            print(f"Final State:      {telemetry.current_state.value}")
            history_str = " -> ".join([s[1].value for s in telemetry.state_history])
            print(f"State Sequence:   {history_str}")
            print("-" * 65)
            if telemetry.audit_record:
                print(f"Policy Audit:     {telemetry.audit_record.verdict} (Hash: {telemetry.audit_record.current_hash[:16]}...)")
                print(f"Mitre Technique:  {telemetry.audit_record.mitre_technique}")
            if telemetry.recon_data:
                print(f"Open Ports:       {telemetry.recon_data.get('open_ports')}")
            if telemetry.sre_summary:
                checksec = telemetry.sre_summary.get("checksec", {})
                print(f"Binary Checksec:  Score: {checksec.get('security_score')}/100 | Canary: {checksec.get('canary')} | NX: {checksec.get('nx')} | PIE: {checksec.get('pie')} | RELRO: {checksec.get('relro')}")
            if telemetry.vulnerabilities:
                print(f"Vulnerabilities:  {telemetry.vulnerabilities.get('vulnerable_sinks_count', 0)} vulnerable C sinks detected")
                print(f"ROP Gadgets:      {telemetry.vulnerabilities.get('rop_gadgets_count', 0)} executable gadgets indexed")
            if telemetry.sliced_context:
                print(f"Context Slicing:  Raw Tokens: {telemetry.sliced_context.total_raw_tokens} -> Served: {telemetry.sliced_context.served_tokens} ({telemetry.sliced_context.token_saving_pct}% reduction)")
            print(f"CAS Storage ID:   {telemetry.vault_artifact_id}")
            print("=" * 65 + "\n")
        return

    if args.watch:
        agent.watch_directory(args.watch, max_iterations=args.watch_iterations)
        return

    if args.query_vault:
        artifact = agent.query_vault(args.query_vault)
        if not artifact:
            print(f"[-] Artifact '{args.query_vault}' not found in vault {agent.vault.db_path}")
            return
        if args.json:
            print(json.dumps(artifact, indent=2))
        else:
            print("\n" + "=" * 65)
            print(f"VAULT ARTIFACT: {artifact.get('id')}")
            print(f"Tool:       {artifact.get('tool_name')} | Size: {artifact.get('raw_bytes')}B | SHA: {artifact.get('content_hash')[:16]}...")
            print("=" * 65)
            print(artifact.get("raw_content"))
            print("=" * 65 + "\n")
        return

    if args.search_vault:
        matches = agent.search_vault(args.search_vault)
        if args.json:
            print(json.dumps(matches, indent=2))
        else:
            print(f"\n[+] Found {len(matches)} matching artifacts for '{args.search_vault}':")
            for m in matches:
                print(f"  • [{m.get('id')}] {m.get('tool_name')} ({m.get('raw_bytes')}B) - {m.get('content_hash')[:8]}")
            print()
        return

    report: Dict[str, Any] = {
        "drive_info": dataclasses.asdict(agent.drive_info),
        "timestamp": time.time()
    }

    if args.decompile:
        report["decompilation"] = agent.decompile_binary_target(args.decompile, max_functions=args.functions)

    if args.scan_binaries:
        report["binary_sre"] = agent.audit_drive_binaries(args.scan_binaries)

    if args.recon:
        report["reconnaissance"] = agent.execute_network_recon(args.recon)

    if not args.scan_binaries and not args.recon and not args.decompile:
        # Default self-test run
        print(f"\n[+] Unified Agent Initialized on Linux Drive: {agent.drive_info.resolved_mount}")
        print(f"    Filesystem: {agent.drive_info.fs_type} | Capacity: {agent.drive_info.total_gb} GB ({agent.drive_info.free_gb} GB free)")
        print(f"    Vault DB: {agent.vault.db_path}\n")

        # Test binary analysis against system binaries on host drive
        print("[*] Running SRE analysis on local drive binaries (/bin/ls, /bin/bash)...")
        report["binary_sre"] = agent.audit_drive_binaries("/bin", max_binaries=2)

        print("[*] Testing headless decompilation on /bin/id...")
        report["decompilation"] = agent.decompile_binary_target("/bin/id", max_functions=2)

        print("[*] Running audited recon against localhost...")
        report["reconnaissance"] = agent.execute_network_recon("127.0.0.1")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 65)
        print("          UNIFIED LINUX DRIVE AGENT AUDIT REPORT")
        print("=" * 65)
        print(f"Drive Mount:      {agent.drive_info.resolved_mount}")
        print(f"Storage Status:   {agent.drive_info.free_gb} GB Free / {agent.drive_info.total_gb} GB Total ({agent.drive_info.used_percent}% used)")
        if "decompilation" in report:
            dec = report["decompilation"]
            print(f"\n[+] HEADLESS DECOMPILATION: {dec.get('binary')}")
            print(f"    Engine:       {dec.get('engine')}")
            print(f"    Functions:    {dec.get('functions_decompiled')} (Lines: {dec.get('lines_decompiled')})")
            print(f"    Vault ID:     {dec.get('vault_id')} (Token Saving: {dec.get('token_savings')})")
            print("    --- C Pseudocode Sample ---")
            for line in dec.get("c_pseudocode_preview", "").splitlines()[:20]:
                print(f"    {line}")
        if "binary_sre" in report:
            print(f"\nBinaries Audited: {len(report['binary_sre'])}")
            for b in report["binary_sre"]:
                v_id = b.get('vault_artifact_id') or b.get('storage_id') or 'N/A'
                score = b.get('checksec_score', 'N/A')
                sinks = b.get('dangerous_sinks_count', 0)
                gadgets = b.get('rop_gadgets_count', 0)
                print(f"  • {b.get('binary')} [{b.get('architecture')}] | Checksec Score: {score} | Sinks: {sinks} | ROP: {gadgets} (Vault: {v_id}, Savings: {b.get('token_savings')})")
        if "reconnaissance" in report:
            rec = report["reconnaissance"]
            print(f"\nRecon Target:     {rec.get('target')} (Status: {rec.get('status')})")
            print(f"Safety Gate Time: {rec.get('audit_ms')} ms")
            print(f"Open Ports:       {rec.get('open_ports')}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
