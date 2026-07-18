"""
Guardian Module Integration — Unified interface for all Guardian scanning modules.
Orchestrates fail2ban_mgr, host_audit, tls_audit, yara_scan with real results.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from shadowcypher.core.logger import logger


class ModuleType(str, Enum):
    """Guardian module types."""
    FAIL2BAN = "fail2ban"
    HOST_AUDIT = "host_audit"
    TLS_AUDIT = "tls_audit"
    YARA_SCAN = "yara_scan"


@dataclass
class ModuleResult:
    """Result from a Guardian module scan."""
    module_type: str
    timestamp: str
    target: str  # host/IP that was scanned
    status: str  # success, partial, failed
    findings: List[Dict]  # [{type, severity, details}]
    error: Optional[str] = None
    execution_time: float = 0.0


class GuardianModules:
    """Orchestrates all Guardian security modules."""

    def __init__(self):
        self.results: Dict[str, List[ModuleResult]] = {}
        self.last_run: Dict[str, str] = {}

    def run_fail2ban_scan(self, host: str = "localhost") -> ModuleResult:
        """Run fail2ban audit and collect banned IPs."""
        try:
            import re
            import time

            from shadowcypher.modules.fail2ban_mgr import fail2ban_manager

            start = time.time()
            findings = []

            # Get overall status
            status_output = fail2ban_manager.status()

            if status_output:
                # Parse output for jail information
                jail_matches = re.findall(r'Jail list:\s*(.+)', status_output)
                if jail_matches:
                    jails = jail_matches[0].split(',')
                    jails = [j.strip() for j in jails if j.strip()]

                    findings.append({
                        "type": "fail2ban_status",
                        "severity": "info",
                        "details": f"Fail2Ban is running with {len(jails)} active jails",
                        "jails_count": len(jails),
                        "jails": jails
                    })

                    # Get status for each jail
                    for jail in jails[:5]:  # Limit to first 5 for performance
                        jail_output = fail2ban_manager.jail_status(jail)
                        if jail_output:
                            # Parse for banned IPs
                            banned_matches = re.findall(r'Currently banned:\s*(\d+)', jail_output)
                            if banned_matches:
                                banned_count = int(banned_matches[0])
                                if banned_count > 0:
                                    findings.append({
                                        "type": "brute_force_detection",
                                        "severity": "high" if banned_count > 10 else "medium",
                                        "details": f"Jail '{jail}' has {banned_count} banned IPs",
                                        "jail": jail,
                                        "banned_count": banned_count
                                    })

            execution_time = time.time() - start

            result = ModuleResult(
                module_type=ModuleType.FAIL2BAN,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=host,
                status="success" if findings else "partial",
                findings=findings,
                execution_time=execution_time
            )

            self._store_result(result)
            logger.info("guardian_modules", f"Fail2Ban scan complete: {len(findings)} findings")
            return result

        except Exception as e:
            logger.error("guardian_modules", f"Fail2Ban scan failed: {e}")
            return ModuleResult(
                module_type=ModuleType.FAIL2BAN,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=host,
                status="failed",
                findings=[],
                error=str(e)
            )

    def run_host_audit(self, host: str = "localhost") -> ModuleResult:
        """Run host audit (rkhunter + lynis) and collect findings."""
        try:
            import time

            from shadowcypher.modules.host_audit import HostAudit

            start = time.time()
            auditor = HostAudit()

            findings = []

            # Run rkhunter
            try:
                rkhunter_output = auditor.rkhunter_scan()
                if rkhunter_output:
                    # Parse for threats
                    if "INFECTED" in rkhunter_output:
                        findings.append({
                            "type": "rootkit_detected",
                            "severity": "critical",
                            "details": "RKHunter detected potential rootkit",
                            "module": "rkhunter"
                        })
                    if "WARNING" in rkhunter_output:
                        findings.append({
                            "type": "security_warning",
                            "severity": "high",
                            "details": "RKHunter reported security warnings",
                            "module": "rkhunter"
                        })
            except Exception as e:
                logger.debug("guardian_modules", f"RKHunter scan failed: {e}")

            # Run lynis
            try:
                lynis_output = auditor.lynis_scan()
                if lynis_output:
                    findings.append({
                        "type": "host_audit_complete",
                        "severity": "info",
                        "details": "Lynis host audit completed",
                        "module": "lynis"
                    })
            except Exception as e:
                logger.debug("guardian_modules", f"Lynis scan failed: {e}")

            execution_time = time.time() - start

            result = ModuleResult(
                module_type=ModuleType.HOST_AUDIT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=host,
                status="success" if findings else "partial",
                findings=findings,
                execution_time=execution_time
            )

            self._store_result(result)
            logger.info("guardian_modules", f"Host audit complete: {len(findings)} findings")
            return result

        except Exception as e:
            logger.error("guardian_modules", f"Host audit failed: {e}")
            return ModuleResult(
                module_type=ModuleType.HOST_AUDIT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=host,
                status="failed",
                findings=[],
                error=str(e)
            )

    def run_tls_audit(self, host: str = "localhost", port: int = 443) -> ModuleResult:
        """Run TLS/SSL audit and check for vulnerabilities."""
        try:
            import time

            from shadowcypher.modules.tls_audit import TLSAudit

            start = time.time()
            auditor = TLSAudit()

            findings = []

            # Scan host
            result_data = auditor.scan(host, port)

            if result_data:
                # Check for vulnerabilities
                vulns = result_data.get("vulnerabilities", [])
                for vuln in vulns:
                    severity = vuln.get("severity", "medium").lower()
                    if severity in ["critical", "high"]:
                        findings.append({
                            "type": "tls_vulnerability",
                            "severity": severity,
                            "details": vuln.get("name", "Unknown vulnerability"),
                            "cve": vuln.get("cve"),
                            "host": host,
                            "port": port
                        })

                # Check certificate
                cert_info = result_data.get("certificate", {})
                if cert_info.get("expired"):
                    findings.append({
                        "type": "expired_certificate",
                        "severity": "high",
                        "details": f"Certificate expired on {cert_info.get('expiry_date')}",
                        "host": host
                    })
                elif cert_info.get("expires_in_days", 999) < 30:
                    findings.append({
                        "type": "certificate_expiring",
                        "severity": "medium",
                        "details": f"Certificate expires in {cert_info.get('expires_in_days')} days",
                        "host": host
                    })

            execution_time = time.time() - start

            result = ModuleResult(
                module_type=ModuleType.TLS_AUDIT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=f"{host}:{port}",
                status="success" if findings else "partial",
                findings=findings,
                execution_time=execution_time
            )

            self._store_result(result)
            logger.info("guardian_modules", f"TLS audit complete: {len(findings)} findings")
            return result

        except Exception as e:
            logger.error("guardian_modules", f"TLS audit failed: {e}")
            return ModuleResult(
                module_type=ModuleType.TLS_AUDIT,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=f"{host}:{port}",
                status="failed",
                findings=[],
                error=str(e)
            )

    def run_yara_scan(self, path: str = "/tmp") -> ModuleResult:  # nosec B108
        """Run YARA malware scanning on filesystem."""
        try:
            import time

            from shadowcypher.modules.yara_scan import YaraScan

            start = time.time()
            scanner = YaraScan()

            findings = []

            # Scan path
            matches = scanner.scan(path)

            for match in matches:
                findings.append({
                    "type": "malware_detected",
                    "severity": "critical",
                    "details": f"YARA rule '{match['rule']}' matched",
                    "file": match.get("file"),
                    "rule": match.get("rule"),
                    "tags": match.get("tags", [])
                })

            execution_time = time.time() - start

            result = ModuleResult(
                module_type=ModuleType.YARA_SCAN,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=path,
                status="success" if findings else "partial",
                findings=findings,
                execution_time=execution_time
            )

            self._store_result(result)
            logger.info("guardian_modules", f"YARA scan complete: {len(findings)} detections")
            return result

        except Exception as e:
            logger.error("guardian_modules", f"YARA scan failed: {e}")
            return ModuleResult(
                module_type=ModuleType.YARA_SCAN,
                timestamp=datetime.now(timezone.utc).isoformat(),
                target=path,
                status="failed",
                findings=[],
                error=str(e)
            )

    def run_all_modules(self, host: str = "localhost") -> List[ModuleResult]:
        """Run all Guardian modules and return results."""
        results = []

        logger.info("guardian_modules", "Starting all module scans")

        # Run each module
        results.append(self.run_fail2ban_scan(host))
        results.append(self.run_host_audit(host))
        results.append(self.run_tls_audit(host))
        results.append(self.run_yara_scan())

        # Convert findings to incidents for incident response processing
        total_findings = sum(len(r.findings) for r in results)
        logger.info("guardian_modules", f"All modules complete: {total_findings} total findings")

        return results

    def get_recent_findings(self, module_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent findings from module scans."""
        findings = []

        for results in self.results.values():
            for result in results:
                if module_type and result.module_type != module_type:
                    continue

                for finding in result.findings:
                    findings.append({
                        "module": result.module_type,
                        "timestamp": result.timestamp,
                        "target": result.target,
                        **finding
                    })

        # Sort by timestamp descending
        findings.sort(key=lambda f: f["timestamp"], reverse=True)
        return findings[:limit]

    def get_module_summary(self) -> Dict:
        """Get summary of all module scans."""
        summary = {
            "total_scans": sum(len(r) for r in self.results.values()),
            "total_findings": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "by_module": {},
        }

        for results in self.results.values():
            for result in results:
                module = result.module_type
                if module not in summary["by_module"]:
                    summary["by_module"][module] = {"scans": 0, "findings": 0}

                summary["by_module"][module]["scans"] += 1
                summary["by_module"][module]["findings"] += len(result.findings)
                summary["total_findings"] += len(result.findings)

                for finding in result.findings:
                    severity = finding.get("severity", "info")
                    if severity in summary["by_severity"]:
                        summary["by_severity"][severity] += 1

        return summary

    def _store_result(self, result: ModuleResult):
        """Store module result for history."""
        if result.module_type not in self.results:
            self.results[result.module_type] = []

        self.results[result.module_type].append(result)
        self.last_run[result.module_type] = result.timestamp

        # Keep only last 100 results per module
        if len(self.results[result.module_type]) > 100:
            self.results[result.module_type] = self.results[result.module_type][-100:]


# Singleton instance
_guardian_modules = None


def get_guardian_modules() -> GuardianModules:
    """Get or create GuardianModules singleton."""
    global _guardian_modules
    if _guardian_modules is None:
        _guardian_modules = GuardianModules()
    return _guardian_modules
