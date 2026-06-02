# Incident Response Reference

## IR Lifecycle (NIST SP 800-61)

1. **Preparation** — policies, tools, playbooks, team training
2. **Detection & Analysis** — identify, scope, classify incident
3. **Containment, Eradication & Recovery** — stop spread, remove threat, restore
4. **Post-Incident Activity** — lessons learned, documentation

## Incident Severity Classification

| Level | Name | Description | SLA |
|-------|------|-------------|-----|
| P1 | Critical | Active breach, ransomware spreading, data exfiltration in progress | 15 min response |
| P2 | High | Compromised account, malware detected, C2 traffic confirmed | 1 hour |
| P3 | Medium | Failed attack attempts, policy violation, suspicious recon | 4 hours |
| P4 | Low | Informational, single failed login, outdated software found | Next business day |

## Initial Triage Checklist

- [ ] What systems are affected? (hostname, IP, OS, role)
- [ ] What is the initial attack vector? (phishing, RDP, supply chain, vuln exploit)
- [ ] Is the attack active or historical?
- [ ] Is data exfiltration occurring? (outbound traffic, DNS tunneling)
- [ ] Are credentials compromised? (check HIBP, Dark Web)
- [ ] Is this isolated or part of a campaign?
- [ ] Regulatory notification requirements? (GDPR 72hr, HIPAA, PCI-DSS)

## Containment Strategies

### Short-term (immediate)
- Isolate affected host: block VLAN, disable switch port, or disconnect
- Revoke/rotate compromised credentials
- Block attacker IPs/domains at perimeter firewall
- Enable enhanced logging on adjacent systems
- Preserve forensic evidence before wiping

### Long-term
- Network segmentation improvements
- Patch exploited vulnerability
- Deploy endpoint detection on affected segment
- Reset all service accounts in compromised OU

## Evidence Collection

Priority order (most volatile first):
1. RAM dump (`winpmem`, `LiME` for Linux)
2. Running processes (`ps aux`, `tasklist /v`)
3. Network connections (`netstat -antp`, `ss -tunlp`)
4. Open files/handles (`lsof`, `handle.exe`)
5. User login history (`last`, `wtmp`, `Security EventLog 4624`)
6. Filesystem timestamps (don't modify — use `dd` or forensic imaging)
7. Log files (`/var/log/auth.log`, `syslog`, Windows Event Logs)
8. Disk image (`dd if=/dev/sda of=/mnt/image.dd bs=64k`)

## Log Analysis (Key Event IDs — Windows)

| Event ID | Description |
|----------|-------------|
| 4624 | Successful logon |
| 4625 | Failed logon |
| 4648 | Logon with explicit credentials (pass-the-hash indicator) |
| 4688 | Process creation (enable command line logging) |
| 4698 | Scheduled task created |
| 4720 | User account created |
| 4732 | User added to security group |
| 4776 | NTLM authentication |
| 7045 | New service installed (malware persistence) |
| 1102 | Audit log cleared (attacker covering tracks) |

## Indicators of Compromise (IoC) Types

- **File-based**: hashes (MD5/SHA256), file names, paths, sizes
- **Network**: IPs, domains, URLs, JA3/JA3S TLS fingerprints
- **Host**: registry keys, scheduled tasks, services, mutexes, named pipes
- **Behavioral**: execution patterns, lateral movement, data staging

## Common Attack Patterns (TTPs)

### Ransomware Kill Chain
1. Initial access: phishing email, RDP bruteforce, or exploit
2. Persistence: scheduled task, registry Run key, WMI subscription
3. Privilege escalation: token impersonation, local exploit
4. Discovery: ADFind, BloodHound, net commands
5. Lateral movement: PsExec, WMI, SMB pass-the-hash
6. Data exfiltration: before encryption (double extortion)
7. Impact: encrypt with AES-256 + RSA key pair

### Business Email Compromise (BEC)
1. Phishing → O365/Gmail credentials
2. Inbox rules to hide alerts
3. Forward all emails to attacker
4. Monitor for invoices/wire transfers
5. Spoof emails requesting payment changes

## Eradication Steps

- Remove malware: scan with multiple engines, check persistence locations
- Verify clean: scheduled tasks, startup items, services, registry Run keys
- Reset all passwords: local admin, domain accounts, service accounts
- Rotate API keys, certificates, and secrets
- Rebuild from known-good image if deeply compromised
- Patch exploited vulnerability before reconnecting

## Communication Templates

### Internal Notification
```
INCIDENT ALERT - [P1/P2/P3]
Affected Systems: [list]
Impact: [describe]
Current Status: [containing/eradicating]
Next Update: [time]
IC: [name/contact]
```

### Executive Summary
Keep to 5 sentences: what happened, how it happened, what was affected, what we did, what we're doing next.
