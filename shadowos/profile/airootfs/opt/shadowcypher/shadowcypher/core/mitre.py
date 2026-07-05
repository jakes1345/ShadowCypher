"""
MITRE ATT&CK technique mapper.

Maps ShadowCypher tool actions and raw finding text to ATT&CK technique IDs.
Kept intentionally offline — no API calls, no network dependency.

Usage:
    from shadowcypher.core.mitre import mitre
    tags = mitre.tag("nmap_service")          # → [{"id": "T1046", ...}, ...]
    line = mitre.format_tags(tags)            # → "[T1046·Network Service Discovery]"
    tags = mitre.from_finding("sql injection") # → technique list
"""
from __future__ import annotations
import re
from typing import Optional

# ── Technique database ───────────────────────────────────────────────────────
# Format: id → (name, tactic, tactic_id)
_TECHNIQUES: dict[str, tuple[str, str, str]] = {
    # Reconnaissance
    "T1595":     ("Active Scanning",                       "Reconnaissance",     "TA0043"),
    "T1595.001": ("Scanning IP Blocks",                    "Reconnaissance",     "TA0043"),
    "T1595.002": ("Vulnerability Scanning",                "Reconnaissance",     "TA0043"),
    "T1590":     ("Gather Victim Network Information",     "Reconnaissance",     "TA0043"),
    "T1590.002": ("DNS",                                   "Reconnaissance",     "TA0043"),
    "T1591":     ("Gather Victim Org Information",         "Reconnaissance",     "TA0043"),
    "T1592":     ("Gather Victim Host Information",        "Reconnaissance",     "TA0043"),
    "T1593":     ("Search Open Websites/Domains",          "Reconnaissance",     "TA0043"),
    "T1596":     ("Search Open Technical Databases",       "Reconnaissance",     "TA0043"),
    # Resource Development
    "T1588":     ("Obtain Capabilities",                   "Resource Development", "TA0042"),
    # Initial Access
    "T1190":     ("Exploit Public-Facing Application",     "Initial Access",     "TA0001"),
    "T1566":     ("Phishing",                              "Initial Access",     "TA0001"),
    "T1566.002": ("Spearphishing Link",                    "Initial Access",     "TA0001"),
    "T1078":     ("Valid Accounts",                        "Initial Access",     "TA0001"),
    # Execution
    "T1059":     ("Command and Scripting Interpreter",     "Execution",          "TA0002"),
    "T1059.004": ("Unix Shell",                            "Execution",          "TA0002"),
    "T1203":     ("Exploitation for Client Execution",     "Execution",          "TA0002"),
    # Privilege Escalation
    "T1068":     ("Exploitation for Privilege Escalation", "Privilege Escalation", "TA0004"),
    # Defense Evasion
    "T1027":     ("Obfuscated Files or Information",       "Defense Evasion",    "TA0005"),
    "T1027.003": ("Steganography",                         "Defense Evasion",    "TA0005"),
    "T1036":     ("Masquerading",                          "Defense Evasion",    "TA0005"),
    "T1070":     ("Indicator Removal",                     "Defense Evasion",    "TA0005"),
    "T1090":     ("Proxy",                                 "Defense Evasion",    "TA0005"),
    "T1090.003": ("Multi-hop Proxy",                       "Defense Evasion",    "TA0005"),
    "T1572":     ("Protocol Tunneling",                    "Command and Control", "TA0011"),
    # Credential Access
    "T1539":     ("Steal Web Session Cookie",              "Credential Access",  "TA0006"),
    "T1557":     ("Adversary-in-the-Middle",               "Credential Access",  "TA0006"),
    "T1110":     ("Brute Force",                           "Credential Access",  "TA0006"),
    "T1040":     ("Network Sniffing",                      "Credential Access",  "TA0006"),
    # Discovery
    "T1046":     ("Network Service Discovery",             "Discovery",          "TA0007"),
    "T1082":     ("System Information Discovery",          "Discovery",          "TA0007"),
    "T1083":     ("File and Directory Discovery",          "Discovery",          "TA0007"),
    "T1087":     ("Account Discovery",                     "Discovery",          "TA0007"),
    "T1069":     ("Permission Groups Discovery",           "Discovery",          "TA0007"),
    "T1120":     ("Peripheral Device Discovery",           "Discovery",          "TA0007"),
    "T1135":     ("Network Share Discovery",               "Discovery",          "TA0007"),
    # Lateral Movement
    "T1021":     ("Remote Services",                       "Lateral Movement",   "TA0008"),
    "T1021.004": ("SSH",                                   "Lateral Movement",   "TA0008"),
    "T1021.002": ("SMB/Windows Admin Shares",              "Lateral Movement",   "TA0008"),
    # Collection
    "T1119":     ("Automated Collection",                  "Collection",         "TA0009"),
    "T1113":     ("Screen Capture",                        "Collection",         "TA0009"),
    # Command and Control
    "T1071":     ("Application Layer Protocol",            "Command and Control", "TA0011"),
    "T1573":     ("Encrypted Channel",                     "Command and Control", "TA0011"),
    # Exfiltration
    "T1048":     ("Exfiltration Over Alternative Protocol","Exfiltration",       "TA0010"),
    "T1041":     ("Exfiltration Over C2 Channel",          "Exfiltration",       "TA0010"),
}

# ── Tool → technique mapping ─────────────────────────────────────────────────
_TOOL_MAP: dict[str, list[str]] = {
    # Recon / scanning
    "nmap_port":        ["T1595", "T1595.001", "T1046"],
    "nmap_service":     ["T1595.002", "T1046", "T1082"],
    "nmap_os":          ["T1082", "T1592"],
    "nmap_vuln":        ["T1595.002", "T1190"],
    "nmap_deep":        ["T1595", "T1595.002", "T1046", "T1082"],
    "masscan":          ["T1595", "T1595.001", "T1046"],
    "subdomain_enum":   ["T1590.002", "T1593"],
    "amass_enum":       ["T1590.002", "T1593", "T1596"],
    "naabu_scan":       ["T1595", "T1595.001", "T1046"],
    "katana_crawl":     ["T1593", "T1595.002"],
    "http_probe":       ["T1595.002", "T1592"],
    # Vulnerability scanners
    "nuclei":           ["T1595.002", "T1190"],
    "sqlmap":           ["T1190", "T1059"],
    "nikto":            ["T1595.002", "T1190"],
    # OSINT
    "osint":            ["T1591", "T1592", "T1593", "T1596"],
    "cve_intel":        ["T1588", "T1596"],
    # Tunneling / evasion
    "ssh_tunnel":       ["T1572", "T1021.004"],
    "hysteria2":        ["T1572", "T1090", "T1090.003"],
    "ghost_mode":       ["T1090", "T1090.003", "T1036"],
    "sovereign_relay":  ["T1573", "T1572"],
    # Intercept / collection
    "https_intercept":  ["T1557", "T1040"],
    "session_monitor":  ["T1539", "T1557"],
    "data_transfer":    ["T1048", "T1041"],
    # Web / exploitation
    "web_forge":        ["T1566.002", "T1059"],
    "web_security":     ["T1595.002", "T1190"],
    # Privilege / AD
    "privilege_audit":  ["T1087", "T1069"],
    "ad_pivot":         ["T1021.002", "T1135"],
    # Misc
    "ble_radar":        ["T1120", "T1046"],
    "wireless":         ["T1040", "T1046"],
    "stego":            ["T1027.003"],
    "static_analyzer":  ["T1082"],
}

# ── Finding pattern → technique IDs ─────────────────────────────────────────
_FINDING_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"sql.?inject|sqli\b",          re.I), ["T1190"]),
    (re.compile(r"\bxss\b|cross.site.script",   re.I), ["T1190"]),
    (re.compile(r"\brce\b|remote.code.exec",    re.I), ["T1190", "T1059"]),
    (re.compile(r"command.inject",              re.I), ["T1190", "T1059.004"]),
    (re.compile(r"auth.?bypass|broken.auth",    re.I), ["T1190", "T1078"]),
    (re.compile(r"default.cred|default.pass",   re.I), ["T1078", "T1110"]),
    (re.compile(r"directory.travers|path.travers|lfi\b|rfi\b", re.I), ["T1190", "T1083"]),
    (re.compile(r"\bssrf\b",                    re.I), ["T1190"]),
    (re.compile(r"\bxxe\b",                     re.I), ["T1190"]),
    (re.compile(r"\bcors\b",                    re.I), ["T1557"]),
    (re.compile(r"\bcsrf\b",                    re.I), ["T1190"]),
    (re.compile(r"open.redirect",               re.I), ["T1190"]),
    (re.compile(r"session.?fixat|cookie",       re.I), ["T1539"]),
    (re.compile(r"deserialization",             re.I), ["T1190", "T1059"]),
    (re.compile(r"prototype.pollu",             re.I), ["T1190"]),
    (re.compile(r"open.port|service.detect",    re.I), ["T1046"]),
    (re.compile(r"ssh\b",                       re.I), ["T1021.004"]),
    (re.compile(r"smb\b|windows.share",         re.I), ["T1021.002", "T1135"]),
    (re.compile(r"CVE-\d{4}-\d+",              re.I), ["T1190"]),
    (re.compile(r"priv.?esc|privilege.esc",     re.I), ["T1068"]),
    (re.compile(r"brute.force|password.spray",  re.I), ["T1110"]),
    (re.compile(r"mitm|man.in.the.middle",      re.I), ["T1557"]),
    (re.compile(r"sniff|packet.cap",            re.I), ["T1040"]),
    (re.compile(r"exfil",                       re.I), ["T1048"]),
    (re.compile(r"steganog|stego",              re.I), ["T1027.003"]),
    (re.compile(r"proxy|tunnel",                re.I), ["T1090", "T1572"]),
]


class MitreMapper:
    """Maps tool actions and raw text findings to ATT&CK technique records."""

    def technique(self, tid: str) -> Optional[dict]:
        """Return full record for a technique ID, or None if unknown."""
        if tid not in _TECHNIQUES:
            return None
        name, tactic, tactic_id = _TECHNIQUES[tid]
        return {"id": tid, "name": name, "tactic": tactic, "tactic_id": tactic_id,
                "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}"}

    def tag(self, tool_key: str) -> list[dict]:
        """Return ATT&CK technique records for a tool action."""
        ids = _TOOL_MAP.get(tool_key, [])
        return [t for t in (self.technique(i) for i in ids) if t]

    def from_finding(self, text: str) -> list[dict]:
        """Pattern-match raw finding text to ATT&CK techniques."""
        matched_ids: list[str] = []
        for pattern, ids in _FINDING_PATTERNS:
            if pattern.search(text):
                for i in ids:
                    if i not in matched_ids:
                        matched_ids.append(i)
        return [t for t in (self.technique(i) for i in matched_ids) if t]

    def format_tags(self, techniques: list[dict], compact: bool = False) -> str:
        """
        Format technique list for display.
        compact=False → "[T1046·Network Service Discovery] [T1082·System Information Discovery]"
        compact=True  → "T1046 T1082"
        """
        if not techniques:
            return ""
        if compact:
            return " ".join(t["id"] for t in techniques)
        return " ".join(f"[{t['id']}·{t['name']}]" for t in techniques)

    def coverage_section(self, tool_keys: list[str]) -> str:
        """
        Render a markdown MITRE ATT&CK Coverage section for a report,
        given a list of tool keys used during the engagement.
        """
        seen: dict[str, dict] = {}
        for key in tool_keys:
            for t in self.tag(key):
                seen[t["id"]] = t

        if not seen:
            return ""

        by_tactic: dict[str, list[dict]] = {}
        for t in seen.values():
            by_tactic.setdefault(t["tactic"], []).append(t)

        lines = ["## MITRE ATT&CK Coverage", ""]
        for tactic, techs in sorted(by_tactic.items()):
            lines.append(f"### {tactic}")
            for t in sorted(techs, key=lambda x: x["id"]):
                lines.append(f"- `{t['id']}` {t['name']}  "
                             f"<{t['url']}>")
            lines.append("")
        return "\n".join(lines)

    def annotate(self, line: str, tool_key: str = None) -> str:
        """
        Return an annotation suffix for a log line.
        Combines tool_key tags (if given) + pattern-matched tags from the text.
        """
        techniques: list[dict] = []
        seen_ids: set[str] = set()

        if tool_key:
            for t in self.tag(tool_key):
                if t["id"] not in seen_ids:
                    techniques.append(t)
                    seen_ids.add(t["id"])

        for t in self.from_finding(line):
            if t["id"] not in seen_ids:
                techniques.append(t)
                seen_ids.add(t["id"])

        if not techniques:
            return ""
        return "  # " + self.format_tags(techniques, compact=True)


mitre = MitreMapper()
