# System Hardening Reference

## Linux Hardening

### Kernel Parameters (sysctl)
```bash
# Network hardening
net.ipv4.ip_forward = 0                    # Disable IP forwarding (unless router)
net.ipv4.conf.all.rp_filter = 1           # Reverse path filtering
net.ipv4.conf.all.accept_redirects = 0    # No ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.tcp_syncookies = 1               # SYN flood protection
net.ipv4.icmp_echo_ignore_broadcasts = 1  # Ignore broadcast pings
net.ipv6.conf.all.accept_redirects = 0

# Memory protection
kernel.randomize_va_space = 2             # Full ASLR
kernel.dmesg_restrict = 1                 # Restrict dmesg
kernel.kptr_restrict = 2                  # Hide kernel pointers
kernel.yama.ptrace_scope = 1              # Restrict ptrace
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
```

### File System
- `/tmp` → noexec, nosuid, nodev mount options
- `/var/tmp` → same
- Separate partitions: `/`, `/home`, `/tmp`, `/var`
- Immutable files: `chattr +i /etc/passwd /etc/shadow /etc/sudoers`
- AIDE/Tripwire: file integrity monitoring baseline

### SSH Hardening (/etc/ssh/sshd_config)
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
Protocol 2
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers <specific_users>
Port 2222  # Obscurity only; real security = keys
HostKeyAlgorithms ssh-ed25519,ecdsa-sha2-nistp256
KexAlgorithms curve25519-sha256,ecdh-sha2-nistp256
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com
```

### User Accounts
- Lock unused accounts: `passwd -l username`
- Set password policy: `/etc/security/pwquality.conf` (minlen=12, dcredit=-1, ucredit=-1)
- sudo configuration: `/etc/sudoers.d/` — principle of least privilege
- Disable root login: `passwd -l root`
- `/etc/login.defs`: PASS_MAX_DAYS 90, PASS_MIN_DAYS 1, PASS_WARN_AGE 7

### Auditd Rules
```
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k sudo
-a always,exit -F arch=b64 -S execve -k exec
-w /tmp -p x -k tmp_exec
-w /var/log -p wa -k log_tampering
```

### AppArmor / SELinux
- AppArmor (Ubuntu/Debian): `aa-enforce /etc/apparmor.d/*`
- SELinux (RHEL/CentOS): enforcing mode; don't disable → fix denials instead
- Check status: `getenforce`, `sestatus`, `aa-status`

## Windows Hardening

### Core Policies
- Disable SMBv1: `Set-SmbServerConfiguration -EnableSMB1Protocol $false`
- Require SMB signing: `Set-SmbServerConfiguration -RequireSecuritySignature $true`
- Disable print spooler (servers): `Stop-Service Spooler; Set-Service Spooler -StartupType Disabled`
- Disable LLMNR/NetBIOS (prevents NTLM relay):
  ```
  HKLM\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient: EnableMulticast = 0
  ```
- Enable Credential Guard (Windows 10 Enterprise+)
- Enable LSASS protection: `HKLM\SYSTEM\CurrentControlSet\Control\Lsa: RunAsPPL = 1`

### Windows Defender / AV
- Enable real-time protection, cloud-delivered protection, tamper protection
- Attack Surface Reduction (ASR) rules:
  - Block Office macros from child processes
  - Block credential stealing from LSASS
  - Block process creation from PSExec/WMI
  - Block executable content from email
- Controlled Folder Access: ransomware mitigation

### Local Security Policy
- Audit policy: logon events, object access, process tracking, privilege use
- Account lockout: 5 attempts, 15-minute lockout, 15-minute observation window
- Password: 12+ characters, complexity enabled, history=24, max age=90
- User Rights Assignment: deny network logon for guest, administrator

### Windows Firewall
- Default: block all inbound, allow all outbound
- Log dropped packets: `%systemroot%\system32\LogFiles\Firewall\pfirewall.log`
- Enable for all profiles: Domain, Private, Public

## Network Device Hardening

### Router/Firewall
- Change default credentials immediately
- Disable: Telnet, HTTP (use SSH, HTTPS)
- Disable unnecessary services: SNMP community "public", UPnP, WPS
- Enable: logging to syslog, NTP sync, HTTPS management only
- Firmware: keep updated; subscribe to vendor security advisories
- Segment: management VLAN separate from production

### Switch
- Disable unused ports; assign to dead VLAN (e.g., VLAN 999)
- Port security: max MAC addresses, violation shutdown
- Dynamic ARP Inspection (DAI) on all VLANs except trusted uplinks
- DHCP snooping: define trusted ports (uplinks/DHCP server)
- Spanning Tree: PortFast + BPDU Guard on access ports
- Disable DTP on access ports: `switchport nonegotiate`

## Container Hardening (Docker)

```dockerfile
# Use minimal base: distroless, alpine, scratch
FROM cgr.dev/chainguard/static:latest

# Non-root user
RUN useradd -u 10001 appuser
USER 10001

# Read-only filesystem where possible
```

Runtime flags:
```bash
docker run \
  --read-only \
  --no-new-privileges \
  --security-opt seccomp=default \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \  # only if needed
  --user 10001:10001 \
  myimage
```

## CIS Benchmarks

CIS provides hardening guides for every major OS/platform. Levels:
- Level 1: Practical, minimal performance impact
- Level 2: Defense-in-depth, may impact usability

Available for: Ubuntu, RHEL, Windows Server, Kubernetes, AWS, Azure, Docker, nginx, Apache
Download free: https://www.cisecurity.org/cis-benchmarks/
