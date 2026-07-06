# UEFI Boot Configuration

This directory contains boot configuration files for systems using Unified Extensible Firmware Interface (UEFI).

## Overview

UEFI is the modern firmware standard used on most systems built after 2010. It provides:

- Direct kernel booting without bootloader wrapper
- Secure Boot capability
- EFI System Partition (ESP) support
- UEFI variables for boot parameters
- Advanced graphics and font support during boot

## Files

### boot.conf
Systemd-boot configuration for UEFI systems. Includes:
- EFI System Partition mount settings
- Systemd-boot loader configuration
- Kernel image paths for EFI
- Boot timeout and graphics settings

### kernel-params.txt
Kernel command-line parameters optimized for UEFI. Includes:
- Security parameters (AppArmor, TPM)
- Console settings for serial and TTY
- Memory protection flags
- IOMMU configurations
- Performance tuning

## Usage

1. Mount EFI System Partition:
```bash
mount -t vfat -o defaults,noatime /dev/efi_partition /boot/efi
```

2. Copy systemd-boot binaries:
```bash
bootctl --path=/boot/efi install
```

3. Create boot entry:
```bash
cp kernel-params.txt /boot/efi/loader/entries/shadowos.conf
```

4. Update bootloader:
```bash
bootctl --path=/boot/efi update
```

## EFI System Partition

The ESP should be:
- At least 512 MB
- FAT32 formatted
- Readable by firmware during boot
- Mounted at /boot/efi or /boot/EFI

## Secure Boot

For Secure Boot-capable systems:
1. Sign kernel with MOK (Machine Owner Key)
2. Enroll MOK in UEFI firmware
3. Enable Secure Boot in UEFI settings
4. Verify signature check with: `efibootmgr -v`

## Troubleshooting

### System won't boot from UEFI
- Check EFI System Partition is present and mounted
- Verify kernel image exists at specified path
- Use `efibootmgr` to check boot entries
- Access UEFI setup to verify boot order

### ESP mounting fails
- Verify partition is marked as EFI System Partition type (EF00)
- Check for filesystem corruption: `fsck.vfat /dev/efi_partition`
- Ensure GPT partition table exists: `gdisk -l /dev/disk`

## References

- UEFI Specification: https://uefi.org/specifications
- systemd-boot documentation
- Arch Linux UEFI boot wiki
