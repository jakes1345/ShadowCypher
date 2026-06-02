# Network Protocols Security Reference

## Layer 2 (Data Link)

### ARP (Address Resolution Protocol)
- Maps IP → MAC addresses on local network
- **ARP spoofing**: attacker sends gratuitous ARPs claiming their MAC owns a target IP
- Enables MITM, credential interception, DoS
- Mitigation: Dynamic ARP Inspection (DAI) on managed switches; static ARP entries for gateways

### Ethernet / 802.1Q VLAN
- VLAN tagging separates broadcast domains
- **VLAN hopping**: double-tagging attack bypasses VLAN isolation
- Mitigation: disable DTP on access ports; use native VLAN != 1; private VLANs

### 802.1X (Port-based NAC)
- EAP-based authentication before network access
- Prevents rogue device connection
- Requires RADIUS server (FreeRADIUS, Cisco ISE)

## Layer 3 (Network)

### IP
- IPv4 CIDR: 192.168.0.0/24 = 256 addresses, 254 usable
- Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- IPv6: 128-bit; link-local fe80::/10; use privacy extensions (RFC 4941)
- IP spoofing: falsified source IP; defeated by BCP38 egress filtering

### ICMP
- Type 0: Echo Reply | Type 8: Echo Request (ping)
- Type 3: Destination Unreachable | Type 11: TTL Exceeded (traceroute)
- **Smurf attack**: ICMP broadcast amplification (historical)
- Covert channel: data tunneled in ICMP payload (iodine, icmptunnel)

### BGP (Border Gateway Protocol)
- RFC 1771; AS-path routing between autonomous systems
- **BGP hijacking**: announce more-specific prefixes to attract traffic
- Notable incidents: Pakistan Telecom hijacking YouTube (2008)
- Mitigation: RPKI (Route Origin Validation), BGPsec

## Layer 4 (Transport)

### TCP
- Three-way handshake: SYN → SYN-ACK → ACK
- **SYN flood**: exhaust server connection table; mitigation = SYN cookies
- **RST injection**: terminate connections (TCP reset attack)
- **Session hijacking**: predict sequence numbers; mitigated by OS randomization
- Flags: SYN, ACK, FIN, RST, PSH, URG, ECE, CWR

### UDP
- Connectionless; no handshake; used for DNS, DHCP, NTP, VoIP, QUIC
- **UDP amplification DDoS**: small request → large response via DNS/NTP/memcached
- Amplification factors: DNS ~28x, NTP ~556x, memcached ~51,000x

## Layer 7 (Application)

### DNS
- Query types: A (IPv4), AAAA (IPv6), MX (mail), CNAME (alias), PTR (reverse), TXT, NS, SOA
- **DNS cache poisoning**: inject forged records (Kaminsky attack)
- **DNS tunneling**: data exfiltration via TXT/NULL queries (dnscat2, iodine)
- **DNS rebinding**: bypass same-origin policy
- DNSSEC: cryptographic signing of zone data; validates authenticity not privacy
- DoH (DNS over HTTPS) / DoT (DNS over TLS): encrypt queries

### HTTP/HTTPS
- Methods: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, CONNECT, TRACE
- Status: 2xx success, 3xx redirect, 4xx client error, 5xx server error
- Headers: Host, User-Agent, Authorization, Cookie, X-Forwarded-For, Content-Type
- **HTTPS stripping**: downgrade HTTPS to HTTP; mitigated by HSTS
- TLS 1.3: only secure version; disable TLS 1.0/1.1/SSL

### SMB (Server Message Block)
- Windows file/printer sharing; port 445
- SMBv1: vulnerable to EternalBlue (MS17-010); disable immediately
- SMBv3: AES-128-CCM encryption; require signing
- **Pass-the-hash**: authenticate with NTLM hash without cracking

### LDAP / Active Directory
- DC = Domain Controller; Forest > Domain > OU > Object hierarchy
- Kerberoasting: request service tickets for SPNs, crack offline
- AS-REP roasting: accounts without pre-auth, get TGT hash
- DCSync: replicate AD using DRSUAPI; needs replication rights
- BloodHound: attack path visualization in AD environments

### TLS/SSL
- TLS 1.3 (2018): removed RSA key exchange, 0-RTT, forward secrecy mandatory
- Certificate chain: Root CA → Intermediate CA → Leaf cert
- SNI: Server Name Indication reveals hostname in TLS ClientHello (plaintext)
- ESNI/ECH: encrypted SNI; hides target hostname
- Cipher suites (TLS 1.3): TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256

### SMTP / Email
- SPF: lists authorized sending IPs in DNS TXT record
- DKIM: cryptographic signature on email headers/body
- DMARC: policy for SPF/DKIM failures (none/quarantine/reject)
- Email spoofing: forge From header; SPF+DKIM+DMARC prevents delivery

## VPN Protocols

| Protocol | Security | Speed | Notes |
|----------|----------|-------|-------|
| OpenVPN | High | Medium | TLS-based; audited; industry standard |
| WireGuard | High | Fast | Modern; ChaCha20/Poly1305; minimal attack surface |
| IPsec/IKEv2 | High | Fast | Native on iOS/Android; complex config |
| PPTP | None | Fast | Broken MS-CHAPv2; do not use |
| L2TP/IPsec | Medium | Medium | L2TP is tunneling only; IPsec adds crypto |
