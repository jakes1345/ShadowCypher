"""Vulnerability scanner module — nikto, sqlmap, nmap scripts, CVE lookups."""

import os
import tempfile
import json
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
from shadowcypher.core.sanitize import quote, validate_target, validate_ports, validate_filepath


_NOOP = lambda x: None


class VulnScanner:
    """Professional vulnerability scanning operations."""

    # ──────────────────────────────────────────────────────────────────
    # NIKTO — Web server vulnerability scanner
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def nikto_scan(target: str, port: int = 80, ssl: bool = False,
                   tuning: str = None, output_file: str = None,
                   on_output=None, on_complete=None) -> int:
        """Nikto web vulnerability scan.

        tuning options:
            0 - File Upload
            1 - Interesting File / Seen in logs
            2 - Misconfiguration / Default File
            3 - Information Disclosure
            4 - Injection (XSS/Script/HTML)
            5 - Remote File Retrieval - Inside Web Root
            6 - Denial of Service
            7 - Remote File Retrieval - Server Wide
            8 - Command Execution / Remote Shell
            9 - SQL Injection
            a - Authentication Bypass
            b - Software Identification
            c - Remote source inclusion
        """
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1

        args = ["nikto", "-h", quote(target)]
        if port != 80:
            args.extend(["-p", str(int(port))])
        if ssl:
            args.append("-ssl")
        if tuning:
            args.extend(["-Tuning", quote(tuning)])
        if output_file:
            args.extend(["-o", quote(output_file), "-Format", "json"])

        cmd = " ".join(args)
        logger.info("vuln", f"Nikto scan: {target}:{port}", ssl=ssl)
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    # ──────────────────────────────────────────────────────────────────
    # SQLMAP — SQL Injection testing
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def sqlmap_scan(url: str, data: str = None, method: str = "GET",
                    level: int = 1, risk: int = 1, threads: int = 5,
                    techniques: str = None, tamper: str = None,
                    on_output=None, on_complete=None) -> int:
        """SQLmap SQL injection scan.

        level: 1-5 (test complexity)
        risk: 1-3 (risk of breaking target)
        techniques: B=Boolean, E=Error, U=Union, S=Stacked, T=Time, Q=Inline
        """
        args = [
            "sqlmap", "-u", quote(url),
            "--batch",  # Non-interactive
            f"--level={max(1, min(int(level), 5))}",
            f"--risk={max(1, min(int(risk), 3))}",
            f"--threads={max(1, min(int(threads), 10))}",
        ]

        if data:
            args.extend(["--data", quote(data)])
            if method.upper() == "POST":
                args.append("--method=POST")

        if techniques:
            args.extend(["--technique", quote(techniques)])
        if tamper:
            args.extend(["--tamper", quote(tamper)])

        cmd = " ".join(args)
        logger.info("vuln", f"SQLmap scan: {url}", level=level, risk=risk)
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def sqlmap_enumerate(url: str, action: str = "dbs",
                         on_output=None, on_complete=None) -> int:
        """SQLmap enumeration after finding injection point.

        action: 'dbs', 'tables', 'columns', 'dump', 'current-user', 'current-db', 'passwords'
        """
        action_flags = {
            "dbs": "--dbs",
            "tables": "--tables",
            "columns": "--columns",
            "dump": "--dump",
            "current-user": "--current-user",
            "current-db": "--current-db",
            "passwords": "--passwords",
        }
        flag = action_flags.get(action, "--dbs")
        cmd = f"sqlmap -u {quote(url)} --batch {flag}"
        logger.info("vuln", f"SQLmap enumerate: {action}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    # ──────────────────────────────────────────────────────────────────
    # NMAP NSE — Vulnerability scripts
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def nmap_vuln_scan(target: str, ports: str = None,
                       scripts: str = "vuln",
                       on_output=None, on_complete=None) -> int:
        """Run nmap vulnerability scripts.

        scripts: 'vuln', 'safe', 'exploit', 'auth', or specific script names
        """
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1

        nmap = config.get_tool_path("nmap")
        port_arg = f"-p {ports}" if ports and validate_ports(ports) else ""
        cmd = f"{quote(nmap)} --script {quote(scripts)} {port_arg} -T4 {quote(target)}"
        logger.info("vuln", f"Nmap vuln scan: {target}", scripts=scripts)
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def nmap_smb_vuln(target: str, on_output=None, on_complete=None) -> int:
        """Check for SMB vulnerabilities (EternalBlue, MS08-067, etc)."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1
        nmap = config.get_tool_path("nmap")
        cmd = f"{quote(nmap)} --script smb-vuln* -p 139,445 -T4 {quote(target)}"
        logger.info("vuln", f"SMB vuln check: {target}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def nmap_ssl_scan(target: str, port: int = 443,
                      on_output=None, on_complete=None) -> int:
        """Check SSL/TLS configuration vulnerabilities."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1
        nmap = config.get_tool_path("nmap")
        cmd = f"{quote(nmap)} --script ssl-cert,ssl-enum-ciphers,ssl-heartbleed,ssl-poodle,ssl-dh-params -p {int(port)} {quote(target)}"
        logger.info("vuln", f"SSL scan: {target}:{port}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    # ──────────────────────────────────────────────────────────────────
    # SEARCHSPLOIT — CVE / Exploit-DB lookups
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def searchsploit(query: str, on_output=None, on_complete=None) -> int:
        """Search Exploit-DB for known vulnerabilities."""
        cmd = f"searchsploit --color {quote(query)}"
        logger.info("vuln", f"Searchsploit: {query}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def searchsploit_json(query: str) -> str:
        """Search Exploit-DB and return JSON results."""
        cmd = f"searchsploit -j {quote(query)}"
        output, _ = runner.run_sync(cmd, shell=True, timeout=15)
        return output

    @staticmethod
    def searchsploit_nmap(nmap_xml: str, on_output=None, on_complete=None) -> int:
        """Cross-reference nmap XML output with Exploit-DB."""
        if not validate_filepath(nmap_xml):
            (on_output or _NOOP)(f"[ERROR] Invalid file path: {nmap_xml}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"searchsploit --nmap {quote(nmap_xml)}"
        logger.info("vuln", f"Searchsploit nmap: {nmap_xml}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    # ──────────────────────────────────────────────────────────────────
    # COMPREHENSIVE SCAN — Multi-phase vulnerability assessment
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def full_assessment(target: str, on_output=None, on_complete=None) -> int:
        """Run a comprehensive vulnerability assessment pipeline.

        Phase 1: Port scan + service detection
        Phase 2: NSE vulnerability scripts
        Phase 3: SSL/TLS analysis (if 443 open)
        Phase 4: HTTP vulnerability scan (if 80/443 open)
        """
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1

        nmap = config.get_tool_path("nmap")
        output_base = tempfile.mktemp(prefix="sc_assessment_")
        safe_target = quote(target)

        script = f"""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  SHADOWCYPHER COMPREHENSIVE VULNERABILITY ASSESSMENT        ║"
echo "║  Target: {target}"
echo "║  $(date)"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "═══ PHASE 1: Service Discovery ═══"
{quote(nmap)} -sV -sC -T4 -oX {quote(output_base + '.xml')} {safe_target}
echo ""

echo "═══ PHASE 2: Vulnerability Scripts ═══"
{quote(nmap)} --script vuln -T4 {safe_target} 2>&1
echo ""

echo "═══ PHASE 3: SSL/TLS Analysis ═══"
{quote(nmap)} --script ssl-cert,ssl-enum-ciphers -p 443 {safe_target} 2>&1
echo ""

echo "═══ PHASE 4: HTTP Analysis ═══"
{quote(nmap)} --script http-headers,http-methods,http-title,http-robots.txt -p 80,443,8080,8443 {safe_target} 2>&1
echo ""

echo "═══ PHASE 5: Exploit-DB Cross-Reference ═══"
searchsploit --nmap {quote(output_base + '.xml')} 2>&1 || echo "(searchsploit not available)"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ASSESSMENT COMPLETE                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
"""
        logger.info("vuln", f"Full assessment started: {target}")
        return runner.run(script, on_output or _NOOP, on_complete or _NOOP, shell=True)
