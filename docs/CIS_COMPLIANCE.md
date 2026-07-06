# ShadowOS CIS Arch Linux Benchmark Compliance

## Overview

ShadowOS implements CIS Arch Linux Benchmark Level 1 & 2 controls.

## Kernel Hardening (CIS 1.x)

| Control | Status | Details |
|---------|--------|---------|
| 1.1.1 Filesystem Configuration | ✓ | Partition scheme enforced |
| 1.2.1 Boot Loader | ✓ | GRUB secured with password |
| 1.4.1 Restrict Kernel Modules | ✓ | Blacklist configured |

## Access Control (CIS 2.x)

| Control | Status | Details |
|---------|--------|---------|
| 2.1.1 X Window System | ✓ | Disabled on servers |
| 2.2.1 Time Sync | ✓ | chrony configured |
| 2.3.1 SSH Server | ✓ | Hardened configuration |

## View Current Compliance

```bash
# Check kernel parameters
sysctl -a | grep -E '(kptr_restrict|dmesg_restrict|yama)'

# Verify file permissions
stat /etc/shadow /etc/gshadow

# Check service status
systemctl status auditd
```

## Manual Remediation

If any control fails:

```bash
# Apply security update
sudo pacman -Syu

# Verify compliance
sudo bash -c 'sysctl -a | grep kernel.kptr_restrict'
```
