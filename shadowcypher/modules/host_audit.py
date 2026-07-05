"""
Host Hardening & Rootkit Audit Module — Enterprise Defensive Build.
Wraps rkhunter (rootkit/backdoor detection) and Lynis (CIS-style system
hardening audit) to scan the OPERATOR'S OWN machine for local compromise
indicators and misconfigurations. Purely defensive/self-scoped — no network
targets, no remote hosts.
"""

import shutil
from typing import Callable, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger


class HostAudit(BaseModule):
    """The 'Sentinel' engine — audits the local host for rootkits and
    hardening gaps using industry-standard tools (rkhunter, Lynis)."""

    def __init__(self):
        super().__init__(module_name="host_audit")

    # ── Rootkit / backdoor detection ──

    def rkhunter_scan(self, on_output: Callable = None) -> Optional[str]:
        """Run rkhunter against the local system — checks for known rootkits,
        backdoors, and local exploit indicators. Requires root for a full
        scan; runs unprivileged checks otherwise."""
        rkhunter = self.get_tool_path("rkhunter")
        if not shutil.which(rkhunter):
            if on_output:
                on_output(
                    "[HOST_AUDIT] rkhunter not found — install: "
                    "pacman -S rkhunter / apt install rkhunter\n"
                )
            return None
        self.log("RKHUNTER_SCAN: local host")
        args = ["sudo", rkhunter, "--check", "--sk", "--nocolors",
                "--rwo"]  # -sk: skip keypress, --rwo: report warnings only
        return self.execute("RKHUNTER_SCAN", args, callback=on_output)

    def rkhunter_update(self, on_output: Callable = None) -> Optional[str]:
        """Update rkhunter's signature database before a scan."""
        rkhunter = self.get_tool_path("rkhunter")
        if not shutil.which(rkhunter):
            return None
        self.log("RKHUNTER_UPDATE")
        return self.execute(
            "RKHUNTER_UPDATE", ["sudo", rkhunter, "--update"], callback=on_output
        )

    # ── System hardening audit ──

    def lynis_audit(self, on_output: Callable = None) -> Optional[str]:
        """Run a Lynis hardening audit against the local system — checks
        auth config, kernel hardening, file permissions, installed
        packages, and produces a hardening index score."""
        lynis = self.get_tool_path("lynis")
        if not shutil.which(lynis):
            if on_output:
                on_output(
                    "[HOST_AUDIT] lynis not found — install: "
                    "pacman -S lynis / apt install lynis\n"
                )
            return None
        self.log("LYNIS_AUDIT: local host")
        args = ["sudo", lynis, "audit", "system", "--quiet", "--no-colors"]
        return self.execute("LYNIS_AUDIT", args, callback=on_output)

    @staticmethod
    def parse_lynis_report(report_path: str = "/var/log/lynis-report.dat") -> dict:
        """Parse Lynis's machine-readable report file into a summary dict
        (hardening_index, warnings, suggestions) after a scan completes."""
        result = {"hardening_index": None, "warnings": [], "suggestions": []}
        try:
            with open(report_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("hardening_index="):
                        result["hardening_index"] = int(line.split("=", 1)[1])
                    elif line.startswith("warning[]="):
                        result["warnings"].append(line.split("=", 1)[1])
                    elif line.startswith("suggestion[]="):
                        result["suggestions"].append(line.split("=", 1)[1])
        except (FileNotFoundError, PermissionError, ValueError) as e:
            logger.warning("host_audit", f"Could not parse Lynis report: {e}")
        return result

    # ── Combined summary ──

    def quick_status(self) -> dict:
        """Fast, non-invasive status check — tool availability + last known
        Lynis hardening index (if a prior scan ran). Safe to call often."""
        rkhunter = self.get_tool_path("rkhunter")
        lynis = self.get_tool_path("lynis")
        status = {
            "rkhunter_available": bool(shutil.which(rkhunter)),
            "lynis_available": bool(shutil.which(lynis)),
            "last_hardening_index": None,
        }
        if status["lynis_available"]:
            parsed = self.parse_lynis_report()
            status["last_hardening_index"] = parsed.get("hardening_index")
        return status


host_audit = HostAudit()
