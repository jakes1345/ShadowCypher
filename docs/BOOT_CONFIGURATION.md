# Boot Configuration Documentation

Comprehensive guide to hardware-specific boot configurations for ShadowOS systems.

## Table of Contents

1. [Overview](#overview)
2. [Boot Modes](#boot-modes)
3. [Secure Boot](#secure-boot)
4. [TPM 2.0](#tpm-20)
5. [Kernel Parameters](#kernel-parameters)
6. [Configuration Selection](#configuration-selection)
7. [Setup and Installation](#setup-and-installation)
8. [Troubleshooting](#troubleshooting)

## Overview

ShadowOS provides hardware-specific boot configurations to optimize for different system architectures while maintaining security best practices. The boot configuration affects:

- Firmware/bootloader interaction
- Kernel loading and initialization
- Security feature availability
- Hardware compatibility
- System performance

## Boot Modes

### UEFI Boot (Modern Systems)

Unified Extensible Firmware Interface (UEFI) is the modern firmware standard used on systems built after 2010.

**Characteristics:**
- Direct kernel boot without bootloader wrapper
- EFI System Partition (ESP) for boot files
- UEFI variables for configuration
- Secure Boot capable
- Advanced graphics during boot
- Up to 64-bit address space

**Requirements:**
- UEFI firmware (Intel/AMD 2010+)
- GPT partition table recommended
- FAT32 EFI System Partition
- 512MB+ ESP size
- EFI boot entry in firmware

**Advantages:**
- Modern standard with long-term support
- Secure Boot integration
- Faster boot sequence
- Better hardware compatibility
- Direct UEFI kernel support

**Disadvantages:**
- Not compatible with older systems (pre-2010)
- Requires proper ESP management
- Potential firmware bugs on some systems

### Legacy BIOS Boot (Older Systems)

Legacy BIOS is the traditional firmware interface used before UEFI became standard.

**Characteristics:**
- Master Boot Record (MBR) bootloader
- GRUB2 bootloader for boot sequence
- Traditional partition tables
- Serial console support
- Limited 16-bit execution during boot
- Limited address space (4GB with MBR)

**Requirements:**
- Traditional BIOS firmware
- MBR or GPT partition table with BIOS compatibility mode
- Boot partition with GRUB installed
- Compatible Linux kernel without UEFI

**Advantages:**
- Compatible with older hardware (pre-2010)
- Simpler partition table management
- Wide hardware support
- Lower firmware requirements
- Proven stability

**Disadvantages:**
- Limited to 2TB with MBR partition tables
- Slower boot process
- No Secure Boot support
- Legacy firmware bugs
- Limited to 4 primary partitions (MBR)

## Secure Boot

### Overview

UEFI Secure Boot provides cryptographic verification of the bootloader and kernel to prevent unauthorized modifications at boot time.

### How It Works

1. **UEFI Firmware**: Contains Platform Key (PK) and Key Exchange Key (KEK)
2. **Bootloader**: Signed with Machine Owner Key (MOK)
3. **Kernel**: Signed with same MOK
4. **Verification**: Firmware verifies signatures before execution

### Setup Process

#### Step 1: Generate Machine Owner Key (MOK)

```bash
# Generate private key (2048-bit RSA)
openssl genrsa -out /etc/secureboot/shadowos.key 2048

# Generate self-signed certificate
openssl req -new -x509 -key /etc/secureboot/shadowos.key \
  -out /etc/secureboot/shadowos.crt -days 3650 \
  -subj "/CN=ShadowOS Local Boot/O=ShadowCypher Security"

# Convert to PEM format
openssl x509 -in /etc/secureboot/shadowos.crt \
  -out /etc/secureboot/shadowos.pem
```

#### Step 2: Sign Kernel and Bootloader

```bash
# Sign kernel with sbsign
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/vmlinuz.signed /boot/vmlinuz

# Sign initramfs
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/initramfs.img.signed /boot/initramfs.img

# Sign systemd-boot or other bootloader
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/efi/EFI/shadowos/bootx64.efi.signed \
  /boot/efi/EFI/shadowos/bootx64.efi
```

#### Step 3: Enroll Machine Owner Key

```bash
# Use mokutil to prepare for enrollment
sudo mokutil --import /etc/secureboot/shadowos.crt

# System will prompt for password (remember it!)
# Reboot to complete enrollment
sudo reboot
```

During reboot, you'll see the MOK enrollment screen. Follow these steps:
1. Select "Continue" at MOK enrollment menu
2. Select "Yes" to enroll the key
3. Enter the password you set with mokutil
4. Confirm enrollment
5. Reboot to complete

#### Step 4: Enable Secure Boot in Firmware

1. Reboot and enter UEFI firmware setup (DEL, F2, ESC, or F10 depending on system)
2. Navigate to "Security" or "Boot" section
3. Find "Secure Boot" setting
4. Change from "Setup Mode" to "User Mode" or "Custom Mode"
5. Enable Secure Boot
6. Save and exit

### Verification

```bash
# Check Secure Boot status
cat /sys/firmware/efi/efivars/SecureBoot-* | od -An -tx1

# Verify kernel signature
sbverify --cert /etc/secureboot/shadowos.pem /boot/vmlinuz.signed

# Check enrolled keys
efibootmgr -v

# View MOK status
mokutil --list-enrolled
```

### Security Features

**Integrity Measurement Architecture (IMA):**
- Measures all executed files
- Creates audit trail of file hashes
- Prevents modification of critical files
- Can prevent execution of modified binaries

**Extended Verification Module (EVM):**
- Protects file extended attributes (xattr)
- Prevents xattr modification outside EVM
- Signs metadata for integrity
- Prevents privilege escalation via xattr

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Secure Boot not available" | Firmware doesn't support Secure Boot or it's disabled in firmware |
| "Signature verification failed" | Kernel/bootloader not properly signed or MOK not enrolled |
| "MOK enrollment failed" | Verify password, check mokutil output, retry enrollment |
| "System won't boot with Secure Boot" | Disable temporarily, verify signatures, re-sign if needed |

## TPM 2.0

### Overview

Trusted Platform Module 2.0 (TPM 2.0) is a cryptographic coprocessor that provides:

- Hardware-based key storage
- Measured boot with Platform Configuration Registers (PCRs)
- Remote attestation capabilities
- Sealing secrets to system state
- Hardware random number generation

### Architecture

#### Platform Configuration Registers (PCRs)

PCRs extend measurements through the boot sequence:

| PCR | Component | Measured Data |
|-----|-----------|---------------|
| 0 | BIOS/Firmware | Firmware code and configuration |
| 1 | BIOS Config | Setup options and variables |
| 2 | Bootloader | Second-stage bootloader code |
| 3 | Boot Config | Bootloader configuration |
| 5 | GPT | Partition table contents |
| 7 | Secure Boot State | SB auth status and policies |
| 8 | Linux | Pre-kernel drivers and configs |
| 9 | IMA | Kernel and application files (dynamic) |
| 10 | IMA Event Log | Boot parameters and cmdline |

Each PCR stores a SHA-256 hash that extends (accumulates) measurements:

```
PCR_new = SHA256(PCR_old || new_measurement)
```

### Measured Boot Process

1. **BIOS Phase**: Measures firmware, extends PCR 0
2. **Bootloader Phase**: Bootloader measures kernel, extends PCR 2
3. **Kernel Phase**: Kernel measures drivers, extends PCR 8
4. **IMA Phase**: IMA measures executed files, extends PCR 9
5. **Event Log**: All measurements recorded with hashes

### Key Sealing

Sealing encrypts a key so it can only be decrypted when system state (PCR values) matches.

**Example: Sealing encryption key to boot state:**

```bash
# Create primary key
tpm2_createprimary -C o -g sha256 -G rsa -c primary.ctx

# Seal encryption key to PCR 9,10
tpm2_create -C primary.ctx -g sha256 -G aes \
  -r sealed.priv -u sealed.pub \
  -L pcr:sha256:9,10=policy.pcr \
  -i encryption_key_value

# Later: unseal (only works if PCR 9,10 match)
tpm2_unseal -c sealed_object.ctx -L pcr:sha256:9,10=policy.pcr
```

**Unlocking LUKS with TPM:**

```bash
# During boot, system can automatically unlock LUKS if TPM unseals key
systemd-cryptenroll /dev/sda3 --tpm2-device=auto
```

### Integrity Measurement Architecture (IMA)

IMA provides runtime file integrity checking:

**IMA Policies:**

- **simple**: Basic file execution measurements
- **tcb**: Measures TCB (Trusted Computing Base) files
- **apr**: Measurements + access control
- **appraise**: Prevents execution of modified files

**Checking IMA:**

```bash
# View current policy
cat /sys/kernel/security/ima/policy

# View measured files
cat /sys/kernel/security/ima/ascii_runtime_measurements

# Check for violations
dmesg | grep -i ima
```

### Extended Verification Module (EVM)

EVM protects IMA metadata from tampering:

```bash
# Generate EVM key
openssl genrsa -out evm.key 2048

# Load into kernel keyring
keyctl padd user evm_key @u < evm.key

# Sign file xattr
evmctl sign -k evm.key file.txt
```

### TPM 2.0 Commands

**Common Operations:**

```bash
# Get TPM properties
tpm2_getcap properties-fixed

# Read PCR values
tpm2_pcrread sha256

# Get specific PCR
tpm2_pcrread sha256:9

# Extend PCR (add measurement)
tpm2_pcrextend 9:sha256=<hash_value>

# Clear TPM (requires physical access confirmation)
tpm2_clear -c p
```

### Troubleshooting TPM

| Issue | Solution |
|-------|----------|
| TPM device not found | Enable TPM in firmware, check kernel drivers loaded |
| PCR mismatch | Boot environment changed, regenerate expected values |
| Unseal fails | Measurements don't match PCR values, verify boot sequence |
| IMA denies execution | File modified, re-measure or add to whitelist |

## Kernel Parameters

### Security Parameters

```
# AppArmor mandatory access control
apparmor=1
security=apparmor
enforce=1

# IMA/EVM for measured boot
ima=enforce
ima_audit=1
ima_appraise=enforce
ima_appraise_tcb=1
ima_hash=sha256
evm=enforce

# Kernel lockdown (restrict privileged access)
lockdown=integrity
kernel.unprivileged_bpf_disabled=1
kernel.unprivileged_userns_clone=0

# Kernel pointer restrictions
kernel.kptr_restrict=3
kernel.dmesg_restrict=1

# Module signature enforcement
module.sig_enforce=1
```

### Memory Protection

```
# Randomize memory layout
aslr
kaslr

# Slub allocator hardening
slub_debug=FZP    # F=Freelist poisoning, Z=Zero, P=Red zoning

# Prevent slab merging
slab_nomerge

# Restrict ptrace to parent processes only
kernel.yama.ptrace_scope=3
```

### Console and Debugging

```
# TTY console
console=tty0

# Serial console for remote access
console=ttyS0,115200n8

# Suppress kernel messages to console
kernel.printk=0 0 0 0

# Restrict dmesg access
kernel.dmesg_restrict=1
```

### Hardware Configuration

```
# Intel IOMMU for DMA protection
intel_iommu=force,pt

# AMD IOMMU for DMA protection
amd_iommu=force,pt

# TPM device
tpm_crb=force        # Command Response Buffer interface
tpm_tis=force        # TPM Interface Specification

# ACPI configuration
acpi=force          # Enable ACPI
pci=nomsi           # Disable MSI interrupts if problematic
```

## Configuration Selection

### Automatic Detection

Use the hardware detection script:

```bash
./shadowos/detect-hardware.sh
```

Output includes recommended boot configuration based on:
- Detected boot mode (UEFI/BIOS)
- Secure Boot capability
- TPM version
- CPU and GPU information
- System specifications

### Manual Selection

Choose configuration based on your system:

| Scenario | Configuration |
|----------|---------------|
| Modern UEFI, no security requirements | `uefi/` |
| Pre-2010 system or BIOS-only | `legacy-bios/` |
| UEFI with Secure Boot, no TPM | `secure-boot/` |
| UEFI with TPM 2.0 | `tpm/` |
| Secure Boot + TPM 2.0 | `secure-boot/` with TPM settings |

## Setup and Installation

### Installing UEFI Configuration

```bash
# Mount EFI System Partition
mount -t vfat -o defaults,noatime /dev/nvme0n1p1 /boot/efi

# Install systemd-boot
bootctl --path=/boot/efi install

# Create boot entry
cat boot-configs/uefi/kernel-params.txt > \
  /boot/efi/loader/entries/shadowos.conf

# Update bootloader
bootctl --path=/boot/efi update
```

### Installing Legacy BIOS Configuration

```bash
# Create boot partition
mkfs.ext4 /dev/sda1
mount /dev/sda1 /boot

# Install GRUB
grub-install --target=i386-pc --boot-directory=/boot /dev/sda

# Generate GRUB configuration
grub-mkconfig -o /boot/grub/grub.cfg

# Copy kernel parameters
cp boot-configs/legacy-bios/kernel-params.txt /etc/default/grub.d/
```

### Installing Secure Boot Configuration

```bash
# Generate MOK
./shadowos/boot-configs/secure-boot/setup-secureboot.sh

# Sign kernel
sbsign --key /etc/secureboot/shadowos.key \
  --cert /etc/secureboot/shadowos.crt \
  --output /boot/vmlinuz.signed /boot/vmlinuz

# Enroll and enable in firmware
mokutil --import /etc/secureboot/shadowos.crt
reboot
```

### Installing TPM 2.0 Configuration

```bash
# Enable in firmware and verify
tpm2_getcap properties-fixed

# Install TPM tools
apt install tpm2-tools tpm2-abrmd

# Setup measured boot
systemd-cryptenroll /dev/mapper/shadowos-root --tpm2-device=auto

# Configure IMA
echo "measure" > /sys/kernel/security/ima/policy
```

## Troubleshooting

### Boot Fails Immediately

**Symptoms**: System reboots or hangs at bootloader

**Solutions:**
1. Check bootloader files exist and are correct
2. Verify kernel and initramfs paths in boot configuration
3. Check partition table is recognized by firmware
4. Try booting with minimal kernel parameters
5. Check system logs: `journalctl -b`

### Kernel Panic During Boot

**Symptoms**: Kernel loading but crashes with panic message

**Solutions:**
1. Check kernel parameters for conflicts
2. Try removing security parameters (ima=, evm=, apparmor=)
3. Check for hardware-specific compatibility
4. Verify initramfs includes necessary drivers
5. Review kernel logs: `dmesg`

### Secure Boot Prevents Boot

**Symptoms**: "Signature verification failed" error

**Solutions:**
1. Verify kernel is signed: `sbverify --cert /etc/secureboot/shadowos.pem /boot/vmlinuz`
2. Check MOK enrolled: `mokutil --list-enrolled`
3. Verify Secure Boot enabled in firmware
4. Re-enroll MOK if necessary
5. Temporarily disable Secure Boot to test

### TPM Not Available

**Symptoms**: TPM commands fail or not recognized

**Solutions:**
1. Check TPM enabled in firmware
2. Verify TPM device: `ls -la /dev/tpm*`
3. Check kernel loaded TPM drivers: `lsmod | grep tpm`
4. Update system firmware if available
5. Check for firmware bugs or TPM lockout

### IMA/EVM Enforcement Issues

**Symptoms**: Permission denied when executing files

**Solutions:**
1. Check IMA policy: `cat /sys/kernel/security/ima/policy`
2. Review violations: `dmesg | grep -i ima`
3. Check file xattr: `getfattr -d filename`
4. Re-measure files if modified
5. Disable IMA/EVM temporarily to isolate issue

## References

- UEFI Specification: https://uefi.org/specifications
- Linux Kernel Boot Parameters: https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html
- systemd-boot Documentation: https://www.freedesktop.org/software/systemd/man/bootctl.html
- GRUB2 Manual: https://www.gnu.org/software/grub/manual/
- TPM 2.0 Specification: https://trustedcomputinggroup.org/
- Linux Kernel Security: https://www.kernel.org/doc/html/latest/security/
- IMA/EVM: https://sourceforge.net/p/linux-ima/wiki/Home/

## See Also

- `shadowos/boot-configs/README.md` - Boot configuration directory guide
- `shadowos/boot-configs/uefi/README.md` - UEFI-specific documentation
- `shadowos/boot-configs/legacy-bios/README.md` - Legacy BIOS documentation
- `shadowos/boot-configs/secure-boot/README.md` - Secure Boot documentation
- `shadowos/boot-configs/tpm/README.md` - TPM 2.0 documentation
- `shadowos/detect-hardware.sh` - Hardware detection script
