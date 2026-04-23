"""
Ghost mission engine — AI-driven multi-phase engagement runner.
Each phase is a real orchestrator call; findings are persisted and
published on the bus. This is an AI-assisted *planner*, not an
autonomous exploit engine — human approval is still required before
any destructive action taken on a target.
"""

import uuid
from typing import List, Dict, Any
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.ai.orchestrator import orchestrator


class GhostMission:
    def __init__(self, target: str):
        self.mid = f"GHOST-{uuid.uuid4().hex[:6].upper()}"
        self.target = target
        self.state = "INIT"
        self.findings: List[Dict[str, Any]] = []
        self.aborted = False

    def report(self, phase: str, message: str, progress: float):
        self.state = phase
        bus.publish("ghost_update", {
            "mid": self.mid,
            "phase": phase,
            "message": message,
            "progress": progress,
            "target": self.target,
        })
        logger.info("ghost", f"[{self.mid}] {phase}: {message}")

    def _run_phase(self, phase: str, prompt: str, progress: float, label: str) -> str:
        self.report(phase, label, progress)
        try:
            result = orchestrator.execute_query_sync(prompt)
        except Exception as e:
            logger.error("ghost", f"[{self.mid}] {phase} failed: {e}")
            result = f"[error] {e}"
        self.findings.append({"phase": phase, "result": result})
        return result

    def execute(self):
        self.report("START", f"Mission started: target={self.target}", 0.05)
        try:
            recon = self._run_phase(
                "RECON",
                f"Perform non-intrusive reconnaissance on {self.target}. "
                "Enumerate open ports, response headers, and OS fingerprints. "
                "Return a JSON summary with keys: ports, headers, os_guess, risks.",
                0.20,
                "Running reconnaissance",
            )
            analysis = self._run_phase(
                "ANALYSIS",
                f"Given this recon output for {self.target}:\n{recon}\n"
                "Identify the highest-value testable entry vector and explain the "
                "specific CVE or misconfiguration it maps to. Return a concise plan.",
                0.40,
                "Correlating findings",
            )
            self._run_phase(
                "INGRESS_PLAN",
                f"Draft a safe proof-of-concept command sequence that would validate "
                f"the entry vector identified in the analysis for {self.target}. "
                f"Do NOT execute. Return the commands as a numbered list.\n{analysis}",
                0.60,
                "Drafting proof-of-concept",
            )
            self._run_phase(
                "EXFIL_PLAN",
                f"List the data classes that would be in scope for extraction on "
                f"{self.target} under the engagement rules of the earlier analysis. "
                f"Return a bullet list — do not exfiltrate.",
                0.80,
                "Planning exfiltration scope",
            )
            self._run_phase(
                "REPORT",
                "Summarize the engagement so far as a markdown report with "
                "Findings / Evidence / Recommendations sections.",
                1.00,
                "Writing report",
            )
            self.report("COMPLETE", f"Mission {self.mid} complete. Review findings for approval.", 1.0)
        except Exception as e:
            logger.error("ghost", f"MISSION_CRITICAL_FAULT: {e}")
            self._emergency_sever()

    def _emergency_sever(self):
        self.aborted = True
        self.report("ABORTED", "Mission aborted due to critical fault.", 0.0)
        logger.warn("ghost", f"[{self.mid}] Mission severed — review the findings log.")


def ignite_ghost_operation(target: str):
    mission = GhostMission(target)
    import threading
    threading.Thread(
        target=mission.execute, daemon=True, name=f"GhostMission-{mission.mid}"
    ).start()
    return mission.mid
