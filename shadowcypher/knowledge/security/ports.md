# Common Network Ports Reference

## Well-Known Ports (0–1023)

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 20 | TCP | FTP Data | Active mode data transfer |
| 21 | TCP | FTP Control | Command channel; plaintext credentials |
| 22 | TCP | SSH | Encrypted remote shell; also SCP/SFTP |
| 23 | TCP | Telnet | Plaintext; never use on modern networks |
| 25 | TCP | SMTP | Mail relay; open relay = spam source |
| 53 | TCP/UDP | DNS | UDP queries; TCP for zone transfers (AXFR) |
| 67/68 | UDP | DHCP | Server/client; rogue DHCP = MITM vector |
| 69 | UDP | TFTP | Unauthenticated file transfer |
| 80 | TCP | HTTP | Plaintext web |
| 110 | TCP | POP3 | Mail retrieval; plaintext |
| 111 | TCP/UDP | RPC portmapper | Pivot point for NFS attacks |
| 119 | TCP | NNTP | Network news |
| 123 | UDP | NTP | Time sync; amplification DDoS vector |
| 135 | TCP | MS-RPC | Windows RPC endpoint mapper |
| 137-139 | TCP/UDP | NetBIOS | Legacy Windows name resolution; disable on modern nets |
| 143 | TCP | IMAP | Mail; plaintext unless STARTTLS |
| 161/162 | UDP | SNMP | v1/v2c = community string auth (weak); use v3 |
| 179 | TCP | BGP | Internet routing; BGP hijack risk |
| 389 | TCP/UDP | LDAP | Directory services; plaintext |
| 443 | TCP | HTTPS | TLS-encrypted HTTP |
| 445 | TCP | SMB | Windows file sharing; EternalBlue, ransomware vector |
| 465 | TCP | SMTPS | SMTP over TLS |
| 514 | UDP | Syslog | Log aggregation; no auth by default |
| 587 | TCP | SMTP submission | Mail from clients; requires auth |
| 636 | TCP | LDAPS | LDAP over TLS |
| 993 | TCP | IMAPS | IMAP over TLS |
| 995 | TCP | POP3S | POP3 over TLS |

## Registered Ports (1024–49151)

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 1080 | TCP | SOCKS proxy | Often used by malware C2 |
| 1433 | TCP | MS SQL Server | Database; external exposure = critical risk |
| 1521 | TCP | Oracle DB | Database |
| 1723 | TCP | PPTP VPN | Deprecated; MS-CHAPv2 broken |
| 2049 | TCP/UDP | NFS | Network filesystem; no auth in v3 |
| 2181 | TCP | Zookeeper | Cluster coord; unauthenticated by default |
| 3306 | TCP | MySQL/MariaDB | Database; never expose externally |
| 3389 | TCP | RDP | Windows remote desktop; BlueKeep, frequent bruteforce target |
| 4444 | TCP | Metasploit default | Common reverse shell port |
| 4899 | TCP | Radmin | Remote admin tool |
| 5432 | TCP | PostgreSQL | Database |
| 5900 | TCP | VNC | Remote desktop; often unencrypted |
| 5985/5986 | TCP | WinRM | Windows remote management; HTTP/HTTPS |
| 6379 | TCP | Redis | In-memory DB; unauthenticated by default in older versions |
| 6667 | TCP | IRC | Legacy C2 channel for botnets |
| 7001 | TCP | WebLogic | Java app server; frequent RCE CVEs |
| 8080 | TCP | HTTP alt | Proxy / dev servers |
| 8443 | TCP | HTTPS alt | Alternative TLS |
| 8888 | TCP | Jupyter Notebook | Often exposed without auth; RCE risk |
| 9200 | TCP | Elasticsearch | REST API; auth optional, data exposure |
| 9090 | TCP | Prometheus | Metrics; internal only |
| 27017 | TCP | MongoDB | Database; historically world-readable |
| 27018 | TCP | MongoDB shard | |
| 47808 | UDP | BACnet | Building automation; ICS target |

## Dynamic/Ephemeral Ports (49152–65535)

Assigned by OS for outbound connections. Useful for NAT traversal analysis.

## High-Risk Port Combinations

- **445 open externally**: Critical — ransomware/worm entry point
- **3389 open externally**: Critical — bruteforce, CVE-2019-0708 (BlueKeep)
- **22 with password auth**: High — switch to key-only
- **23 anywhere**: Critical — replace with SSH
- **6379 external**: Critical — Redis data/code execution
- **9200 external**: High — Elasticsearch data breach risk
- **27017 external**: Critical — MongoDB ransomware campaigns

## Port Scanning Notes

- SYN scan (Nmap -sS): stealthy, doesn't complete TCP handshake
- Connect scan (Nmap -sT): full handshake, more detectable, no root needed
- UDP scan (Nmap -sU): slow, unreliable; important for DNS/SNMP/NTP
- Service fingerprinting (Nmap -sV): banner grabbing to ID software versions
- OS detection (Nmap -O): TTL and TCP window size analysis
