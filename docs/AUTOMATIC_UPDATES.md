# ShadowOS Automatic Security Updates

## Overview

ShadowOS can automatically install security updates via:
1. Daily timer-based checks
2. Pacman hook triggers on package changes

## Enabling Auto-Updates

```bash
sudo systemctl enable autoupdate.timer
sudo systemctl start autoupdate.timer
```

## Checking Update Status

```bash
sudo journalctl -u autoupdate.service -f
```

## Manual Update

```bash
sudo pacman -Syu
```

## Security Packages Monitored

- linux-hardened (kernel)
- glibc (C library)
- openssl (encryption)
- shadow (user management)
- sudo (privilege escalation)

## Disabling Auto-Updates

```bash
sudo systemctl disable autoupdate.timer
sudo systemctl stop autoupdate.timer
```

## Update Log

Check `/var/log/shadowos-autoupdate.log` for update history.
