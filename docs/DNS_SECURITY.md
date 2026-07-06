# ShadowOS DNS Security

## DNSSEC Validation

ShadowOS validates DNSSEC signatures to prevent DNS spoofing.

## DNS Resolver

Configured to use `systemd-resolved` with:
- DNSSEC validation enabled
- TRUST-AD flag for authentication

## Checking DNS Status

```bash
chmod +x shadowos/dns-check.sh
./shadowos/dns-check.sh
```

## Custom DNS Servers

Edit `/etc/systemd/resolved.conf`:

```
DNS=1.1.1.1 8.8.8.8
DNSSEC=yes
```

Restart:
```bash
sudo systemctl restart systemd-resolved
```

## Cloudflare (1.1.1.1)

Fast and privacy-focused with DNSSEC support.

## Google (8.8.8.8)

Large anycast network with DNSSEC support.
