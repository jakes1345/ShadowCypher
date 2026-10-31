"""
SHADOWCYPHER ORCHESTRATOR — PentAGI Multi-Agent Security State Machine
Inspired by vxcontrol/pentagi.
Implements a finite-state machine coordinating autonomous agents across:
  1. TARGET_INSPECTION (Linux drive & mount discovery)
  2. RECONNAISSANCE (Network socket service fingerprinting)
  3. THREAT_MODELING (MITRE ATT&CK attack surface mapping)
  4. BINARY_SRE (ELF parsing, checksec, ROP gadgets, C decompilation)
  5. POLICY_AUDIT (Deterministic iFixAi guard & immutable hash-chain ledger)
  6. CONTEXT_SANDBOXING (CAS storage, hierarchical chunking & token reduction)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from shadowcypher.sre.elf_parser import ELFParser
from shadowcypher.sre.vulnerability_scanner import BinaryVulnerabilityScanner
from shadowcypher.audit.ifix_guard import IFixPolicyAuditor, AuditRecord
from shadowcypher.context_vault.engine import AdvancedContextVault, SlicedContext

logger = logging.getLogger("PentAGI-StateMachine")


class MissionState(str, enum.Enum):
    IDLE = "IDLE"
    TARGET_INSPECTION = "TARGET_INSPECTION"
    RECONNAISSANCE = "RECONNAISSANCE"
    THREAT_MODELING = "THREAT_MODELING"
    BINARY_SRE = "BINARY_SRE"
    POLICY_AUDIT = "POLICY_AUDIT"
    CONTEXT_SANDBOXING = "CONTEXT_SANDBOXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclasses.dataclass
class MissionTelemetry:
    mission_id: str
    target_host: str
    target_binary: Optional[str]
    drive_mount: str
    current_state: MissionState
    state_history: List[Tuple[float, MissionState]]
    recon_data: Optional[Dict[str, Any]] = None
    sre_summary: Optional[Dict[str, Any]] = None
    vulnerabilities: Optional[Dict[str, Any]] = None
    decompilation: Optional[Dict[str, Any]] = None
    audit_record: Optional[AuditRecord] = None
    vault_artifact_id: Optional[str] = None
    sliced_context: Optional[SlicedContext] = None
    error: Optional[str] = None


class AutonomousPentAGISystem:
    """
    Coordinates multi-agent autonomous security operations, linking
    the SRE decompiler, iFixAi policy ledger, and Context-Mode vault.
    """

    def __init__(self,
                 drive_path: str = "/tmp/shadow_drive",
                 vault_dir: str = "/tmp/shadow_context_vault",
                 allowed_cidrs: Optional[List[str]] = None,
                 on_event: Optional[Callable[[str, Any], None]] = None):
        self.drive_path = drive_path
        self.vault = AdvancedContextVault(vault_dir=vault_dir)
        self.auditor = IFixPolicyAuditor(allowed_networks=allowed_cidrs)
        self.on_event = on_event or (lambda ev, data: None)

    def _transition(self, telemetry: MissionTelemetry, new_state: MissionState, detail: str = "") -> None:
        logger.info(f"[STATE-TRANSITION] {telemetry.current_state.value} -> {new_state.value} ({detail})")
        telemetry.state_history.append((time.time(), new_state))
        telemetry.current_state = new_state
        self.on_event("state_change", {"state": new_state.value, "detail": detail})

    def run_mission(self,
                    target_host: str = "127.0.0.1",
                    target_binary: Optional[str] = "/bin/id",
                    max_token_budget: int = 600) -> MissionTelemetry:
        """
        Execute an end-to-end autonomous cyber operations mission.
        """
        mission_id = f"msn_{int(time.time())}"
        telemetry = MissionTelemetry(
            mission_id=mission_id,
            target_host=target_host,
            target_binary=target_binary,
            drive_mount=self.drive_path,
            current_state=MissionState.IDLE,
            state_history=[(time.time(), MissionState.IDLE)]
        )

        try:
            # ─────────────────────────────────────────────────────────────
            # Phase 1: Policy Audit (iFixAi Guardrail Gate)
            # ─────────────────────────────────────────────────────────────
            self._transition(telemetry, MissionState.POLICY_AUDIT, "Verifying mission boundaries")
            audit_record = self.auditor.audit_intent(
                tool_name="network_recon",
                params={"target": target_host, "command": f"probe {target_host}"}
            )
            telemetry.audit_record = audit_record
            if audit_record.verdict != "APPROVED":
                telemetry.error = f"Mission halted by iFix policy audit: {audit_record.reason}"
                self._transition(telemetry, MissionState.FAILED, telemetry.error)
                return telemetry

            # ─────────────────────────────────────────────────────────────
            # Phase 2: Target & Drive Inspection
            # ─────────────────────────────────────────────────────────────
            self._transition(telemetry, MissionState.TARGET_INSPECTION, f"Inspecting storage drive at {self.drive_path}")
            p_drive = Path(self.drive_path)
            if not p_drive.exists():
                p_drive.mkdir(parents=True, exist_ok=True)

            # ─────────────────────────────────────────────────────────────
            # Phase 3: Reconnaissance
            # ─────────────────────────────────────────────────────────────
            self._transition(telemetry, MissionState.RECONNAISSANCE, f"Scanning common ports on {target_host}")
            import socket
            open_ports = []
            for port in [21, 22, 80, 443, 8080]:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                try:
                    if s.connect_ex((target_host, port)) == 0:
                        open_ports.append(port)
                except Exception:
                    pass
                finally:
                    s.close()
            telemetry.recon_data = {"target": target_host, "open_ports": open_ports}

            # ─────────────────────────────────────────────────────────────
            # Phase 4: Binary Reverse Engineering (ELF + Checksec + ROP)
            # ─────────────────────────────────────────────────────────────
            if target_binary and Path(target_binary).exists():
                self._transition(telemetry, MissionState.BINARY_SRE, f"Deconstructing ELF binary {target_binary}")
                parser = ELFParser(target_binary)
                telemetry.sre_summary = parser.get_summary()

                scanner = BinaryVulnerabilityScanner(parser)
                telemetry.vulnerabilities = scanner.full_audit()

                # Decompile entrypoint via Linux SRE engine
                import subprocess
                cmd = ["r2", "-q", "-c", "af @ entry0; s entry0; pdc", str(target_binary)]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    raw_decomp = proc.stdout.strip()
                    if not raw_decomp or "Cannot" in raw_decomp:
                        cmd_fallback = ["r2", "-q", "-c", "s entry0; pd 25", str(target_binary)]
                        proc_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=10)
                        raw_decomp = proc_fb.stdout.strip() or "// (Entrypoint disassembly)"
                except subprocess.TimeoutExpired:
                    raw_decomp = f"// [TIMEOUT] Heavy binary decompilation deferred for {target_binary}"
                except Exception as e:
                    raw_decomp = f"// [SRE DECOMPILE ERROR] {e}"

                telemetry.decompilation = {
                    "binary": target_binary,
                    "entry_decomp": raw_decomp,
                    "lines": len(raw_decomp.splitlines())
                }

            # ─────────────────────────────────────────────────────────────
            # Phase 5: Context-Mode Sandboxing & Slicing
            # ─────────────────────────────────────────────────────────────
            self._transition(telemetry, MissionState.CONTEXT_SANDBOXING, "Sandboxing artifacts into CAS database")
            
            # Format comprehensive raw mission report
            full_report_text = json.dumps({
                "mission_id": mission_id,
                "audit": dataclasses.asdict(audit_record) if audit_record else None,
                "recon": telemetry.recon_data,
                "sre_checksec": telemetry.sre_summary,
                "sre_vulns": telemetry.vulnerabilities,
                "decompiled_c": telemetry.decompilation.get("entry_decomp") if telemetry.decompilation else ""
            }, indent=2)

            art_id = self.vault.store_and_sandbox(
                tool_name="pentagi_orchestrator",
                title=f"Autonomous Mission Report for {target_host}",
                raw_content=full_report_text
            )
            telemetry.vault_artifact_id = art_id

            # Generate sliced context window (Token-Reduction Engine)
            sliced = self.vault.slice_context_window(
                artifact_id=art_id,
                query="vulnerability checksec entry0",
                max_token_budget=max_token_budget
            )
            telemetry.sliced_context = sliced

            # ─────────────────────────────────────────────────────────────
            # Phase 6: Mission Completed
            # ─────────────────────────────────────────────────────────────
            self._transition(telemetry, MissionState.COMPLETED, f"Mission successfully finished. Artifact: {art_id}")

        except Exception as e:
            telemetry.error = str(e)
            self._transition(telemetry, MissionState.FAILED, f"Exception: {e}")

        return telemetry
