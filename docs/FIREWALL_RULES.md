# ShadowOS Firewall Configuration

## Default Policy

- **Input:** DROP (reject all unsolicited)
- **Output:** ACCEPT (allow all outgoing)
- **Forward:** DROP (no routing)

## Allowed Inbound

- SSH (port 22) - rate limited to 5/min
- ICMP (ping)
- Related/established connections

## Firewall Backends

ShadowOS supports two firewall backends:

### 1. UFW (Uncomplicated Firewall)

UFW provides a user-friendly interface to iptables/netfilter.

**Configuration file:** `/etc/ufw/ufw.conf`

Enable UFW:
```bash
sudo ufw enable
```

Check status:
```bash
sudo ufw status verbose
```

## 2. nftables

nftables is the modern replacement for iptables with superior performance and flexibility.

**Configuration file:** `/etc/nftables.conf`

Load rules:
```bash
sudo nft -f /etc/nftables.conf
```

View current rules:
```bash
sudo nft list ruleset
```

## Enabling Additional Ports

```bash
# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow specific IP
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Allow application by name
sudo ufw allow Samba

# Remove a rule
sudo ufw delete allow 80/tcp
```

## Viewing Rules

```bash
# List all active rules
sudo ufw show added

# Monitor live with nftables
sudo nft monitor

# View iptables rules
sudo iptables -L -n -v

# View nftables rules
sudo nft list ruleset
```

## Rate Limiting

SSH is rate limited to 5 connections per minute by default to prevent brute force attacks.

To adjust:
```bash
sudo ufw limit 22/tcp
```

## IPv6

IPv6 is enabled by default with the same firewall policies as IPv4.

To disable IPv6 filtering:
```bash
sudo ufw allow in ipv6 from any to any
```

## Firewall Logs

Monitor firewall activity:
```bash
# UFW logs
sudo tail -f /var/log/ufw.log

# System logs
sudo journalctl -u ufw -f

# View denied connections
sudo grep "BLOCK\|REJECT" /var/log/ufw.log
```

## Security Best Practices

1. **Default Deny:** Never allow all traffic by default
2. **Whitelist Approach:** Only open ports you need
3. **Rate Limiting:** Protect SSH with connection limits
4. **Logging:** Monitor all denied connections
5. **IPv6:** Ensure IPv6 rules match IPv4
6. **Regular Audit:** Review rules periodically

```bash
# Audit your firewall rules
sudo ufw show added | sort
```

## Troubleshooting

### Connection refused after enabling firewall

Check if the port is allowed:
```bash
sudo ufw show added | grep <port>
```

Allow the port:
```bash
sudo ufw allow <port>/tcp
sudo ufw reload
```

### Firewall not applying changes

Reload the rules:
```bash
sudo ufw reload
```

Or restart the service:
```bash
sudo systemctl restart ufw
sudo systemctl restart nftables
```

### Performance issues

nftables is faster than UFW for large rulesets. Switch to nftables-only:
```bash
sudo pacman -S nftables
sudo systemctl enable nftables
sudo systemctl disable ufw
```

## Related Configuration

- **CIS Compliance:** See [CIS_COMPLIANCE.md](CIS_COMPLIANCE.md)
- **Kernel Hardening:** See [sysctl parameters](../shadowos/profile/airootfs/etc/sysctl.d/99-shadowos.conf)
- **SSH Hardening:** See [SSH_HARDENING.md](SSH_HARDENING.md)
