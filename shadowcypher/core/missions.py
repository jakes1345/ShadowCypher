"""
Ghost mission engine — AI-driven multi-phase engagement runner.
Each phase is a real orchestrator call; findings are persisted and
published on the bus. This is an AI-assisted *planner*, not an
autonomous exploit engine — human approval is still required before
any destructive action taken on a target.
"""

import uuid
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.ai.orchestrator import orchestrator


class GhostMission(ABC):
    """Base class for AI-driven multi-phase security missions."""

    def __init__(self, target: str):
        self.target = target
        self.mid = str(uuid.uuid4())[:8]
        self.findings: List[Dict[str, Any]] = []

    def report(self, phase: str, message: str, progress: float = 0.0):
        payload = {"mid": self.mid, "phase": phase, "message": message, "progress": progress}
        bus.publish("mission", payload)
        logger.info("mission", f"[{self.mid}] {phase}: {message}")

    def _run_phase(self, phase: str, prompt: str, progress: float, status_msg: str) -> str:
        self.report(phase, status_msg, progress)
        try:
            result = orchestrator.run(prompt)
            self.findings.append({"phase": phase, "result": result})
            return result
        except Exception as e:
            err = f"{phase}_ERROR: {e}"
            self.findings.append({"phase": phase, "result": err})
            return err

    def _emergency_sever(self):
        self.report("ABORT", "Mission severed — unrecoverable error.", 1.0)

    @abstractmethod
    def execute(self):
        """Execute the mission. Must be implemented by subclasses."""


class SovereignGhostMission(GhostMission):
    """
    Sovereign Apex Build — A truly autonomous mission engine that 
    executes real tools instead of just planning.
    """
    def __init__(self, target: str):
        super().__init__(target)
        from shadowcypher.core.platform import platform_engine
        self.engine = platform_engine

    def _execute_recon_tool(self):
        """Execute real nmap scan for the RECON phase."""
        self.report("RECON", "Executing Nmap Service Discovery...", 0.15)
        nmap = self.engine.get_cmd("nmap")
        try:
            import subprocess
            res = subprocess.check_output([nmap, "-F", "-sV", "--version-light", self.target], text=True, timeout=120)
            return res
        except Exception as e:
            return f"RECON_TOOL_ERROR: {e}"

    def execute(self):
        self.report("START", f"Sovereign Mission Ignite: target={self.target}", 0.05)
        try:
            # Phase 1: REAL RECON
            recon_raw = self._execute_recon_tool()
            self.findings.append({"phase": "RECON_RAW", "result": recon_raw})
            
            # Use AI to summarize the raw recon
            recon_summary = self._run_phase(
                "RECON_AI",
                f"Analyze this raw nmap output for {self.target}:\n{recon_raw}\n"
                "Extract open ports, services, and versions. Identify the most "
                "critical entry vector. Return JSON with 'services' and 'prime_vector'.",
                0.30,
                "AI analyzing tactical recon"
            )

            # Phase 2: Vulnerability Matching
            self._run_phase(
                "ANALYSIS",
                f"Target: {self.target}\nRecon: {recon_summary}\n"
                "Search your internal vulnerability database (CVE/PocEngine-DB) for the "
                "services identified. Determine if any 403/401 bypass or RCE is possible. "
                "Provide a ranked list of exploitability.",
                0.50,
                "Correlating vulnerabilities"
            )

            # Phase 3: Ingress Validation (Safe Probes)
            if "403" in recon_raw or "Forbidden" in recon_raw:
                self.report("BYPASS_403", "Triggering automated 403 bypass sequence...", 0.70)
                from shadowcypher.modules.web_security import WebSecurity
                # We'll run this in parallel but wait for a snippet
                WebSecurity.bypass_403_test(f"http://{self.target}", "/", on_output=lambda m: self.report("BYPASS_403", m, 0.75))

            # Phase 4: Final Report
            self._run_phase(
                "REPORT",
                "Synthesize the raw recon, AI analysis, and bypass results into a "
                "Sovereign Tactical Briefing. Include Next-Step recommendations.",
                1.00,
                "Finalizing Intelligence Briefing"
            )
            
            self.report("COMPLETE", f"Mission {self.mid} terminated. Intelligence Secured.", 1.0)
            
        except Exception as e:
            logger.error("ghost", f"ghost mission error: {e}")
            self._emergency_sever()

def ignite_ghost_operation(target: str):
    mission = SovereignGhostMission(target)
    threading.Thread(
        target=mission.execute, daemon=True, name=f"GhostMission-{mission.mid}"
    ).start()
    return mission.mid
