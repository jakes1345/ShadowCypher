"""Kairos — Proactive vulnerability and intelligence monitor.

Analyzes every line of tool output in real-time. Detects IPs, CVEs,
credentials, services, and vulnerability patterns. Feeds findings
into the SQLite target registry.
"""

import re
from shadowcypher.core.logger import logger
from shadowcypher.core.database import db


class Kairos:
    """Background intelligence analyzer that watches all tool output."""

    def __init__(self):
        # IP detection
        self._ip_re = re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b')

        # CVE detection (CVE-YYYY-NNNNN)
        self._cve_re = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)

        # Open port detection from nmap output ("22/tcp open ssh")
        self._port_re = re.compile(r'(\d{1,5})/(tcp|udp)\s+open\s+(\S+)')

        # Credential patterns
        self._cred_patterns = [
            re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*(\S+)', re.IGNORECASE),
            re.compile(r'(?:username|user|login)\s*[:=]\s*(\S+)', re.IGNORECASE),
            re.compile(r'([a-f0-9]{32})', re.IGNORECASE),     # MD5 hash
            re.compile(r'([a-f0-9]{40})', re.IGNORECASE),     # SHA1 hash
            re.compile(r'([a-f0-9]{64})', re.IGNORECASE),     # SHA256 hash
        ]

        # Vulnerability keyword patterns (real scanner output strings)
        self._vuln_patterns = [
            re.compile(r'SQL\s*injection', re.IGNORECASE),
            re.compile(r'XSS|cross.site.scripting', re.IGNORECASE),
            re.compile(r'remote\s*code\s*execution|RCE', re.IGNORECASE),
            re.compile(r'directory\s*traversal|path\s*traversal', re.IGNORECASE),
            re.compile(r'local\s*file\s*inclusion|LFI', re.IGNORECASE),
            re.compile(r'remote\s*file\s*inclusion|RFI', re.IGNORECASE),
            re.compile(r'server\s*side\s*request\s*forgery|SSRF', re.IGNORECASE),
            re.compile(r'command\s*injection|OS\s*command', re.IGNORECASE),
            re.compile(r'VULNERABLE|VULN(?:ERABLE)?:', re.IGNORECASE),
            re.compile(r'CRITICAL|HIGH.*(?:risk|severity)', re.IGNORECASE),
            re.compile(r'buffer\s*overflow', re.IGNORECASE),
            re.compile(r'authentication\s*bypass', re.IGNORECASE),
            re.compile(r'privilege\s*escalation', re.IGNORECASE),
            re.compile(r'insecure\s*deserialization', re.IGNORECASE),
            re.compile(r'default\s*credentials?', re.IGNORECASE),
            re.compile(r'weak\s*(?:password|cipher|ssl|tls)', re.IGNORECASE),
            # Nikto output patterns
            re.compile(r'OSVDB-\d+', re.IGNORECASE),
            # Hydra success
            re.compile(r'\[.*\]\s+host:.*login:.*password:', re.IGNORECASE),
        ]

        # High-value service detection
        self._service_patterns = [
            re.compile(r'(?:ssh|ftp|telnet|rdp|smb|mysql|postgres|mssql|oracle|redis|mongo|vnc|rsync)', re.IGNORECASE),
        ]

        # Track what we've already alerted on to avoid spam
        self._seen_cves = set()
        self._seen_vulns = set()
        self._alert_callbacks = []

    def register_alert_callback(self, cb):
        """Register a callback(alert_type, message) for real-time UI alerts."""
        self._alert_callbacks.append(cb)

    def _alert(self, alert_type: str, message: str):
        """Fire an alert to all registered callbacks."""
        logger.info("kairos", f"[{alert_type}] {message}")
        for cb in self._alert_callbacks:
            try:
                cb(alert_type, message)
            except Exception:
                pass

    def analyze(self, line: str):
        """Analyze a single line of tool output. Called by the runner on every line."""
        if not line or not line.strip():
            return

        line = line.strip()

        # 1. Detect and register IPs
        ips = self._ip_re.findall(line)
        for ip in ips:
            if not ip.startswith(("127.", "0.0.", "255.")):
                db.register_target(ip)

        # 2. Detect CVEs
        for cve in self._cve_re.findall(line):
            cve_upper = cve.upper()
            if cve_upper not in self._seen_cves:
                self._seen_cves.add(cve_upper)
                self._alert("CVE", f"Detected: {cve_upper} — {line[:80]}")
                # Store in DB
                potential_ip = ips[0] if ips else "TARGET"
                db.log_vulnerability(potential_ip, 0, "unknown", cve_id=cve_upper, severity="CRITICAL", payload=line)
                
                # DEEP LEVEL: Trigger Autonomous Exploitation Analysis
                try:
                    from shadowcypher.ai.orchestrator import AIOrchestrator
                    orch = AIOrchestrator()
                    orch.queue_mission(f"Analyze exploitation path for {cve_upper} on {potential_ip}")
                except Exception: pass

        # 3. Detect open ports (nmap format)
        for match in self._port_re.finditer(line):
            port, proto, service = match.groups()
            self._alert("PORT", f"{port}/{proto} open ({service})")
            potential_ip = ips[0] if ips else "TARGET"
            db.log_vulnerability(potential_ip, int(port), service, severity="INFO", payload=line)

        # 4. Detect vulnerability patterns (Trigger deep-dive if critical found)
        for pattern in self._vuln_patterns:
            match = pattern.search(line)
            if match:
                key = match.group(0).lower()[:30]
                if key not in self._seen_vulns:
                    self._seen_vulns.add(key)
                    self._alert("VULN", line[:120])
                    potential_ip = ips[0] if ips else "TARGET"
                    db.log_vulnerability(potential_ip, 0, "unknown", severity="MEDIUM", payload=line)
                    
                    # If high-value target, escalate
                    if "critical" in line.lower() or "rce" in line.lower():
                        try:
                            from shadowcypher.ai.orchestrator import AIOrchestrator
                            orch = AIOrchestrator()
                            orch.queue_mission(f"Critical vulnerability identified: {line[:50]}. Initiate escalation audit on {potential_ip}")
                        except Exception: pass
                break  # One alert per line

        # 5. Detect credentials / hashes (Automated Credential Extraction V3)
        for pattern in self._cred_patterns:
            if pattern.search(line):
                self._alert("CRED", f"Potential credential detected in output")
                potential_ip = ips[0] if ips else "TARGET"
                try:
                    # Multi-pattern extraction for professional results
                    user_match = re.search(r'(?:username|user|login)\s*[:=]\s*(\S+)', line, re.IGNORECASE)
                    pass_match = re.search(r'(?:password|passwd|pwd)\s*[:=]\s*(\S+)', line, re.IGNORECASE)
                    hash_match = re.search(r'([a-f0-9]{32,64})', line, re.IGNORECASE)
                    
                    username = user_match.group(1) if user_match else "unknown"
                    password = pass_match.group(1) if pass_match else None
                    cred_hash = hash_match.group(1) if hash_match else None
                    
                    if password or cred_hash:
                        db.cursor.execute(
                            "INSERT INTO credentials_sink (target_ip, service, username, password, hash, cracked) VALUES (?, ?, ?, ?, ?, ?)",
                            (potential_ip, "unknown", username, password, cred_hash, False)
                        )
                        db.conn.commit()
                except Exception: pass
                break

    def reset(self):
        """Clear seen-state for a new engagement."""
        self._seen_cves.clear()
        self._seen_vulns.clear()


kairos = Kairos()
