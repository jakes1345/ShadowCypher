"""ShadowCypher Vulnerability Pulsing Engine — Pure Functional Build (V22.1)."""

import subprocess
import os
import re
import shlex
from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_target, validate_ports, validate_port


class VulnScanner:
    """The 'Radar' of the suite. Integrates Nmap/Vulners/NSE for real-time sightings."""

    @staticmethod
    def get_scan_types():
        return ["Quick Pulse", "Full Service Scan", "Vulnerability Search (Vulners)", "UDP Scan", "Stealth Recon"]

    @staticmethod
    def pulse_target(target, scan_type="Quick Pulse", on_output=None, on_complete=None):
        """Perform a deep-pulse vulnerability scan on a target."""
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        logger.info("vuln", f"INITIATING_PULSE: {target} [TYPE={scan_type}]")

        flag_map = {
            "Quick Pulse": ["-F"],
            "Full Service Scan": ["-sV", "-p-"],
            "Vulnerability Search (Vulners)": ["-sV", "--script=vulners"],
            "UDP Scan": ["-sU", "-F"],
            "Stealth Recon": ["-sS", "-O"],
        }

        flags = flag_map.get(scan_type, ["-F"])
        return runner.execute_task(f"VULN_SCAN_{target}", ["nmap"] + flags + [target], callback=on_output)

    @staticmethod
    def extract_cves(text):
        """Parse Nmap/Vulners output for critical CVE sightings."""
        cves = re.findall(r"CVE-\d{4}-\d+", text)
        return list(set(cves))

    @staticmethod
    def generate_report(target, text):
        """Save a tactical report to the reports directory."""
        # Sanitize target for filename
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', target)
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/vuln_report_{safe_name}.txt"
        with open(report_path, "w") as f:
            f.write(text)
        return report_path

    # UI Backwards Compatibility Hooks
    @staticmethod
    def nikto_scan(target, port=80, ssl=False, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        args = ["nikto", "-h", target, "-p", str(int(port))]
        if ssl:
            args.append("-ssl")
        return runner.execute_task(f"NIKTO_{target}", args, callback=on_output)

    @staticmethod
    def sqlmap_scan(target, data=None, level=1, risk=1, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        args = ["sqlmap", "-u", target, "--batch", "--level", str(level), "--risk", str(risk)]
        if data:
            args += ["--data", data]
        return runner.execute_task(f"SQLMAP_{target}", args, callback=on_output)

    @staticmethod
    def sqlmap_enumerate(target, action="dbs", on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        flag = f"--{action}"
        return runner.execute_task(f"SQLMAP_ENUM_{target}", ["sqlmap", "-u", target, "--batch", flag], callback=on_output)

    @staticmethod
    def nmap_vuln_scan(target, ports=None, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        args = ["nmap", "--script", "vuln"]
        if ports:
            if not validate_ports(ports):
                if on_output: on_output(f"[ERROR] Invalid port spec: {ports}")
                return
            args += ["-p", ports]
        args.append(target)
        return runner.execute_task(f"NMAP_VULN_{target}", args, callback=on_output)

    @staticmethod
    def nmap_smb_vuln(target, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        return runner.execute_task(f"NMAP_SMB_{target}", ["nmap", "-p", "139,445", "--script", "smb-vuln*", "-T4", target], callback=on_output)

    @staticmethod
    def nmap_ssl_scan(target, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        return runner.execute_task(f"NMAP_SSL_{target}", ["nmap", "-p", "443", "--script", "ssl-enum-ciphers", "-T4", target], callback=on_output)

    @staticmethod
    def searchsploit(query, on_output=None, on_complete=None):
        # Professional Depth: Check local tools first to avoid sudo dependency
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_ss = os.path.join(project_root, "tools", "exploitdb", "searchsploit")
        
        cmd_base = "searchsploit"
        if os.path.exists(local_ss):
            cmd_base = local_ss
            
        return runner.execute_task("SEARCHSPLOIT", [cmd_base, query], callback=on_output)

    @staticmethod
    def full_assessment(target, on_output=None, on_complete=None):
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        # A truly legit full assessment
        return runner.execute_task(f"FULL_ASSESSMENT_{target}", ["nmap", "-A", "-v", "-T4", target], callback=on_output)

    @staticmethod
    def ai_audit(target, on_output=None):
        """AI-Augmented Vulnerability Auditing and CVE Correlation."""
        from shadowcypher.ai.orchestrator import AIOrchestrator
        logger.info("ai", f"INITIATING_AI_VULN_AUDIT: {target}")
        
        if on_output: 
            on_output(f"[AI] ANALYZING_ATTACK_SURFACE_FOR: {target}")
            on_output("[AI] CROSS_REFERENCING_CVE_DATABASE_LOCALLY...")
        
        orch = AIOrchestrator()
        # Trigger the masterclass audit but focus on the 'VULN' result
        query = f"Perform a deep vulnerability audit for {target}. Correlate with CVE databases locally and suggest high-priority targets. Start with stealth check."
        response = orch.execute_query(query, callback=on_output)
        
        if on_output:
            on_output(f"[AI] VULN_AUDIT_COMPLETE: {response[:200]}...")
        return response
