"""
Module Audit Agent — Automated security scanning and incident response workflow.
Periodically runs Guardian modules, converts findings to incidents, and triggers responses.
"""

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from shadowcypher.core.logger import logger


@dataclass
class AuditSchedule:
    """Configuration for automated module audits."""
    fail2ban_interval: int = 3600  # 1 hour
    host_audit_interval: int = 86400  # 1 day
    tls_audit_interval: int = 86400  # 1 day
    yara_scan_interval: int = 3600  # 1 hour
    auto_incident_response: bool = True  # Trigger responses automatically


class ModuleAuditAgent:
    """Runs automated security audits using Guardian modules."""

    def __init__(self, schedule: Optional[AuditSchedule] = None):
        self.schedule = schedule or AuditSchedule()
        self.running = False
        self.agent_thread: Optional[threading.Thread] = None
        self.last_audit: Dict[str, float] = {}
        self.audit_count: Dict[str, int] = {}

    def start(self):
        """Start the audit agent background thread."""
        if self.running:
            return

        self.running = True
        self.agent_thread = threading.Thread(
            target=self._audit_loop,
            daemon=True,
            name="ModuleAuditAgent",
        )
        self.agent_thread.start()
        logger.info("module_audit_agent", "Audit agent started")

    def stop(self):
        """Stop the audit agent."""
        self.running = False
        if self.agent_thread:
            self.agent_thread.join(timeout=5)
        logger.info("module_audit_agent", "Audit agent stopped")

    def _audit_loop(self):
        """Background loop that runs periodic module audits."""
        while self.running:
            try:
                current_time = time.time()

                # Check if it's time to run fail2ban audit
                if self._should_run("fail2ban", current_time):
                    self._run_fail2ban_audit()
                    self.last_audit["fail2ban"] = current_time
                    self.audit_count["fail2ban"] = self.audit_count.get("fail2ban", 0) + 1

                # Check if it's time to run host audit
                if self._should_run("host_audit", current_time):
                    self._run_host_audit()
                    self.last_audit["host_audit"] = current_time
                    self.audit_count["host_audit"] = self.audit_count.get("host_audit", 0) + 1

                # Check if it's time to run TLS audit
                if self._should_run("tls_audit", current_time):
                    self._run_tls_audit()
                    self.last_audit["tls_audit"] = current_time
                    self.audit_count["tls_audit"] = self.audit_count.get("tls_audit", 0) + 1

                # Check if it's time to run YARA scan
                if self._should_run("yara_scan", current_time):
                    self._run_yara_scan()
                    self.last_audit["yara_scan"] = current_time
                    self.audit_count["yara_scan"] = self.audit_count.get("yara_scan", 0) + 1

            except Exception as e:
                logger.error("module_audit_agent", f"Audit loop error: {e}")

            time.sleep(60)  # Check every minute

    def _should_run(self, module_type: str, current_time: float) -> bool:
        """Check if a module audit should run now."""
        last_run = self.last_audit.get(module_type, 0)
        interval = getattr(self.schedule, f"{module_type}_interval", 3600)
        return (current_time - last_run) >= interval

    def _run_fail2ban_audit(self):
        """Run fail2ban module and process findings."""
        try:
            from shadowcypher.core.guardian_modules import get_guardian_modules

            modules = get_guardian_modules()
            result = modules.run_fail2ban_scan()

            logger.info("module_audit_agent", f"Fail2Ban audit: {len(result.findings)} findings")

            if self.schedule.auto_incident_response:
                self._process_findings(result)

        except Exception as e:
            logger.error("module_audit_agent", f"Fail2Ban audit failed: {e}")

    def _run_host_audit(self):
        """Run host audit module and process findings."""
        try:
            from shadowcypher.core.guardian_modules import get_guardian_modules

            modules = get_guardian_modules()
            result = modules.run_host_audit()

            logger.info("module_audit_agent", f"Host audit: {len(result.findings)} findings")

            if self.schedule.auto_incident_response:
                self._process_findings(result)

        except Exception as e:
            logger.error("module_audit_agent", f"Host audit failed: {e}")

    def _run_tls_audit(self):
        """Run TLS audit module and process findings."""
        try:
            from shadowcypher.core.guardian_modules import get_guardian_modules

            modules = get_guardian_modules()
            result = modules.run_tls_audit()

            logger.info("module_audit_agent", f"TLS audit: {len(result.findings)} findings")

            if self.schedule.auto_incident_response:
                self._process_findings(result)

        except Exception as e:
            logger.error("module_audit_agent", f"TLS audit failed: {e}")

    def _run_yara_scan(self):
        """Run YARA scan module and process findings."""
        try:
            from shadowcypher.core.guardian_modules import get_guardian_modules

            modules = get_guardian_modules()
            result = modules.run_yara_scan()

            logger.info("module_audit_agent", f"YARA scan: {len(result.findings)} findings")

            if self.schedule.auto_incident_response:
                self._process_findings(result)

        except Exception as e:
            logger.error("module_audit_agent", f"YARA scan failed: {e}")

    def _process_findings(self, result):
        """Convert module findings to incidents and trigger responses."""
        try:
            import uuid

            from shadowcypher.core.incident_response import get_incident_response_engine

            engine = get_incident_response_engine()

            for finding in result.findings:
                # Map finding severity to incident severity
                severity = finding.get("severity", "info")

                # Create incident from finding
                incident_id = f"incident-{uuid.uuid4().hex[:8]}"
                incident_details = {
                    "title": finding.get("details", "Unknown"),
                    "module": result.module_type,
                    "type": finding.get("type", "unknown"),
                    "timestamp": result.timestamp,
                    "target": result.target,
                    **finding
                }

                # Process incident (triggers response rules)
                response_id = engine.process_incident(
                    incident_id=incident_id,
                    incident_type=finding.get("type", "unknown"),
                    severity=severity,
                    details=incident_details,
                )

                if response_id:
                    logger.info(
                        "module_audit_agent",
                        f"Incident {incident_id} processed: {finding.get('type')} "
                        f"(severity: {severity})"
                    )

        except Exception as e:
            logger.error("module_audit_agent", f"Failed to process findings: {e}")

    def get_status(self) -> Dict:
        """Get audit agent status."""
        return {
            "running": self.running,
            "schedule": {
                "fail2ban_interval": self.schedule.fail2ban_interval,
                "host_audit_interval": self.schedule.host_audit_interval,
                "tls_audit_interval": self.schedule.tls_audit_interval,
                "yara_scan_interval": self.schedule.yara_scan_interval,
                "auto_incident_response": self.schedule.auto_incident_response,
            },
            "last_audits": self.last_audit,
            "audit_counts": self.audit_count,
        }


# Singleton instance
_module_audit_agent = None


def get_module_audit_agent() -> ModuleAuditAgent:
    """Get or create ModuleAuditAgent singleton."""
    global _module_audit_agent
    if _module_audit_agent is None:
        _module_audit_agent = ModuleAuditAgent()
    return _module_audit_agent
