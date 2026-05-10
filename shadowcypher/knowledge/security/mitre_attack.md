# MITRE ATT&CK Framework Reference

## Overview

MITRE ATT&CK (Adversarial Tactics, Techniques, and Common Knowledge) is a curated knowledge base of real-world attacker behavior. Used for threat modeling, detection engineering, and red team planning.

Current version: ATT&CK v14 (2023)
Matrices: Enterprise, Mobile, ICS

## Enterprise Tactics (14)

| ID | Tactic | Description |
|----|--------|-------------|
| TA0043 | Reconnaissance | Gather information before attacking |
| TA0042 | Resource Development | Acquire infrastructure, tools, accounts |
| TA0001 | Initial Access | Enter the target environment |
| TA0002 | Execution | Run malicious code |
| TA0003 | Persistence | Maintain foothold |
| TA0004 | Privilege Escalation | Gain higher permissions |
| TA0005 | Defense Evasion | Avoid detection |
| TA0006 | Credential Access | Steal credentials |
| TA0007 | Discovery | Explore environment |
| TA0008 | Lateral Movement | Move through network |
| TA0009 | Collection | Gather data of interest |
| TA0011 | Command & Control | Communicate with compromised systems |
| TA0010 | Exfiltration | Steal data |
| TA0040 | Impact | Manipulate, interrupt, or destroy |

## High-Priority Techniques

### Initial Access
- **T1566** Phishing (Spearphishing Attachment / Link / via Service)
- **T1190** Exploit Public-Facing Application (Log4Shell, Exchange ProxyLogon)
- **T1133** External Remote Services (RDP, VPN, Citrix)
- **T1078** Valid Accounts (credential stuffing, purchased creds)
- **T1195** Supply Chain Compromise (SolarWinds, XZ Utils)

### Execution
- **T1059** Command and Scripting Interpreter (PowerShell T1059.001, Bash T1059.004)
- **T1204** User Execution (open malicious attachment/link)
- **T1053** Scheduled Task/Job (cron, Windows Task Scheduler)
- **T1047** Windows Management Instrumentation (WMI)

### Persistence
- **T1547** Boot or Logon Autostart (Registry Run Keys T1547.001)
- **T1543** Create or Modify System Process (Windows Service T1543.003)
- **T1136** Create Account (local or domain admin account)
- **T1505** Server Software Component (web shell T1505.003)
- **T1098** Account Manipulation (add to admin group)

### Privilege Escalation
- **T1548** Abuse Elevation Control Mechanism (sudo T1548.003, UAC bypass T1548.002)
- **T1134** Access Token Manipulation (token impersonation)
- **T1068** Exploitation for Privilege Escalation (kernel exploits: Dirty COW, PrintNightmare)
- **T1484** Domain Policy Modification (GPO modification)

### Defense Evasion
- **T1070** Indicator Removal (clear logs T1070.001, delete files T1070.004)
- **T1027** Obfuscated Files or Information (base64, XOR, packed executables)
- **T1036** Masquerading (rename malware to svchost.exe, etc.)
- **T1562** Impair Defenses (disable AV T1562.001, disable firewall)
- **T1055** Process Injection (DLL injection, process hollowing)
- **T1218** System Binary Proxy Execution (LOLBins: mshta, certutil, regsvr32)

### Credential Access
- **T1110** Brute Force (password spray T1110.003, credential stuffing T1110.004)
- **T1003** OS Credential Dumping (LSASS T1003.001, SAM T1003.002, DCSync T1003.006)
- **T1552** Unsecured Credentials (files T1552.001, env vars T1552.007)
- **T1558** Steal or Forge Kerberos Tickets (Kerberoasting T1558.003, Golden Ticket T1558.001)
- **T1539** Steal Web Session Cookie

### Lateral Movement
- **T1021** Remote Services (RDP T1021.001, SMB/WMI T1021.002, SSH T1021.004)
- **T1550** Use Alternate Authentication Material (pass-the-hash T1550.002, pass-the-ticket T1550.003)
- **T1570** Lateral Tool Transfer (BITS, certutil for download)
- **T1534** Internal Spearphishing

### Collection
- **T1005** Data from Local System
- **T1039** Data from Network Shared Drive
- **T1074** Data Staged (compress before exfil)
- **T1560** Archive Collected Data (zip, 7z, rar)
- **T1113** Screen Capture
- **T1056** Input Capture (keylogger T1056.001)

### Command & Control
- **T1071** Application Layer Protocol (HTTPS T1071.001, DNS T1071.004)
- **T1572** Protocol Tunneling (DNS over HTTPS, ICMP tunnel)
- **T1090** Proxy (Tor T1090.003, domain fronting T1090.004)
- **T1132** Data Encoding (base64 in C2 comms)
- **T1568** Dynamic Resolution (DGA — domain generation algorithms)

### Exfiltration
- **T1041** Exfiltration Over C2 Channel
- **T1048** Exfiltration Over Alternative Protocol (DNS tunneling T1048.001)
- **T1567** Exfiltration to Cloud Storage (OneDrive, Dropbox, Mega)

### Impact
- **T1486** Data Encrypted for Impact (ransomware)
- **T1490** Inhibit System Recovery (delete VSS copies)
- **T1489** Service Stop (stop security services, databases)
- **T1485** Data Destruction
- **T1498** Network Denial of Service

## Detection Opportunities

Map detections to techniques:
- PowerShell script block logging → T1059.001
- Process creation logs with parent-child → T1055 process injection
- LSASS access auditing → T1003.001
- DNS query logging → T1071.004, T1568 (DGA patterns)
- Network traffic to Tor exit nodes → T1090.003
- Shadow copy deletion → T1490 (ransomware precursor)

## Tools by Tactic

| Tool | Primary Use | ATT&CK Techniques |
|------|-------------|-------------------|
| Mimikatz | Credential dumping | T1003.001, T1550.002 |
| BloodHound | AD attack path | T1069, T1087, T1482 |
| Cobalt Strike | C2 framework | T1071, T1055, T1027 |
| Metasploit | Exploitation | T1190, T1068 |
| Impacket | SMB/Kerberos | T1021.002, T1550.002, T1558 |
| PowerSploit | Post-exploitation | T1055, T1082, T1059.001 |
