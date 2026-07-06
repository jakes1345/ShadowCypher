# Secure Boot Configuration

This directory contains boot configuration files for systems using UEFI Secure Boot.

## Overview

UEFI Secure Boot provides cryptographic verification of:

- Bootloader integrity and origin
- Kernel image authenticity
- Protected boot sequence against unauthorized modifications
- Tamper detection through signatures
- Machine Owner Key (MOK) support for custom kernels

## Files

### boot.conf
Secure Boot configuration with kernel signing settings. Includes:
- Machine Owner Key (MOK) certificate paths and details
- Kernel and bootloader signing requirements
- EFI variable locations for Secure Boot databases
- Signature verification enforcement
- Signed kernel image paths

### kernel-params.txt
Enhanced security parameters for Secure Boot systems. Includes:
- IMA (Integrity Measurement Architecture) enforcement
- TPM integration for measured boot
- Kernel module signature enforcement
- Enhanced kernel hardening flags
- UEFI Secure Boot enforcement parameters

## Setting Up Secure Boot

### 1. Generate Machine Owner Key (MOK)

```bash
# Generate private key
openssl genrsa -out /etc/secureboot/shadowos.key 2048

# Generate certificate
openssl req -new -x509 -key /etc/secureboot/shadowos.key \
  -out /etc/secureboot/shadowos.crt -days 3650 \
  -subj "/CN=ShadowOS Local Boot/O=ShadowCypher Security"

# Convert to PEM format
openssl x509 -in /etc/secureboot/shadowos.crt \
  -out /etc/secureboot/shadowos.pem
```

### 2. Sign Kernel and Initramfs

```bash
# Sign kernel
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/efi/EFI/shadowos/vmlinuz.efi.signed \
  /boot/vmlinuz

# Sign initramfs
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/efi/EFI/shadowos/initramfs.img.signed \
  /boot/initramfs.img
```

### 3. Enroll MOK in UEFI Firmware

```bash
# Use mokutil to enroll key
sudo mokutil --import /etc/secureboot/shadowos.crt

# Reboot and follow firmware prompts to complete enrollment
reboot
```

### 4. Enable Secure Boot

- Restart system into UEFI firmware (DEL, F2, or ESC during boot)
- Locate "Secure Boot" setting
- Change from "Setup Mode" to "User Mode"
- Enable Secure Boot
- Save and exit

## Integrity Measurement Architecture (IMA)

IMA provides cryptographic verification of executable and library files:

- All executed files are measured and compared against a whitelist
- Measurements are extended into TPM PCR registers
- Runtime violations are logged and can trigger policy actions
- Requires extended filesystem attributes (xattr)

### IMA Policy

Default IMA policy measures:
- All executed files
- All loaded kernel modules
- All files opened for write
- All appended files

## Trusted Platform Module (TPM)

TPM provides hardware-based cryptographic operations:

- Secure key storage in hardware
- Sealing data to system state via PCR values
- Random number generation
- Measured boot verification

### Checking TPM Status

```bash
# List TPM devices
ls -la /dev/tpm*

# Check TPM version
cat /proc/cmdline | grep tpm

# View TPM measurements
tpm2_pcrread sha256
```

## Troubleshooting

### Secure Boot won't enable
- Check firmware supports Secure Boot (Intel/AMD CPU from 2010+)
- Verify no firmware password is blocking changes
- Check for firmware updates
- Disable Fast Boot temporarily
- Reset UEFI settings to defaults

### Kernel fails signature verification
- Verify MOK is properly enrolled: `efibootmgr -v`
- Check kernel is signed: `sbverify --cert /etc/secureboot/shadowos.pem /boot/vmlinuz`
- Regenerate and re-sign kernel if needed
- Check ESP is FAT32 formatted

### IMA violations
- Review violation logs: `dmesg | grep -i ima`
- Add files to IMA policy if legitimate
- Check filesystem extended attributes (xattr) supported

### TPM not detected
- Verify TPM is enabled in UEFI firmware
- Check TPM version (1.2 or 2.0): `cat /sys/class/tpm/tpm0/tpm_version_major`
- Install tpm2-tools for TPM 2.0

## References

- UEFI Specification: https://uefi.org/specifications
- Secure Boot documentation
- Linux Kernel IMA and EVM subsystem docs
- TPM 2.0 specifications
