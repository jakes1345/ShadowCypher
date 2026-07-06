# ShadowOS Boot Configurations

Hardware-specific boot configurations for different system architectures and security models.

## Directory Structure

```
boot-configs/
├── uefi/              - Modern UEFI firmware (systemd-boot)
├── legacy-bios/       - Traditional BIOS firmware (GRUB2)
├── secure-boot/       - UEFI Secure Boot with kernel signing
├── tpm/               - TPM 2.0 measured boot and attestation
└── README.md          - This file
```

## Configuration Types

Each subdirectory contains three files:

### boot.conf
Bootloader and firmware-specific configuration:
- Bootloader selection and paths
- Firmware interface settings
- Boot partition configuration
- Security features (Secure Boot, TPM)
- Boot timeout and menu settings
- Kernel and initramfs paths

### kernel-params.txt
Linux kernel command-line parameters:
- Root filesystem and mount options
- Console and debug output settings
- Security module configuration (AppArmor)
- Memory protection flags
- IOMMU settings
- Performance tuning parameters
- Hardware-specific compatibility options

### README.md
Detailed documentation for each boot type:
- Architecture overview
- Configuration explanation
- Step-by-step setup instructions
- Troubleshooting guide
- References and specifications

## Quick Start

### For UEFI Systems (Modern)

1. Use `uefi/` configuration
2. Mount EFI System Partition (ESP) at `/boot/efi`
3. Install systemd-boot: `bootctl --path=/boot/efi install`
4. Copy kernel parameters from `kernel-params.txt`

### For BIOS Systems (Legacy)

1. Use `legacy-bios/` configuration
2. Create boot partition: `mkfs.ext4 /dev/sda1`
3. Install GRUB: `grub-install --target=i386-pc /dev/sda`
4. Copy kernel parameters from `kernel-params.txt`

### For Secure Boot Systems

1. Use `secure-boot/` configuration
2. Generate Machine Owner Key (MOK)
3. Sign kernel and bootloader
4. Enroll MOK in UEFI firmware
5. Enable Secure Boot in firmware settings

### For TPM 2.0 Systems

1. Use `tpm/` configuration
2. Enable TPM in UEFI firmware
3. Configure measured boot in bootloader
4. Install tpm2-tools and related packages
5. Load EVM keys for file integrity

## Hardware Detection

To automatically select appropriate boot configuration, use `../detect-hardware.sh`:

```bash
./detect-hardware.sh
# Output includes: UEFI/BIOS, CPU type, GPU presence, TPM status, Secure Boot support
```

## Key Features by Configuration

### UEFI
- ✓ Modern firmware interface
- ✓ EFI System Partition (FAT32)
- ✓ Direct kernel boot without wrapper
- ✓ Secure Boot capable
- ✗ Not compatible with older systems

### Legacy BIOS
- ✓ Compatible with older hardware
- ✓ MBR or GPT partition tables
- ✓ GRUB2 bootloader support
- ✓ Serial console support
- ✗ Limited to 2TB with MBR
- ✗ Slower boot sequence

### Secure Boot
- ✓ Cryptographic verification of bootloader
- ✓ Kernel signature checking
- ✓ IMA (Integrity Measurement Architecture)
- ✓ EVM (Extended Verification Module)
- ✓ Protection against boot-time attacks
- ✗ Requires key generation and enrollment

### TPM 2.0
- ✓ Measured boot with PCR extension
- ✓ Hardware-based key storage
- ✓ Remote attestation capable
- ✓ EVM signature support
- ✓ Sealing to system state
- ✗ Requires TPM 2.0 hardware
- ✗ Adds boot time overhead

## Security Recommendations

1. **For Enterprise**: Use TPM 2.0 with measured boot and attestation
2. **For High Security**: Enable Secure Boot with kernel signing
3. **For Compatibility**: Use UEFI without Secure Boot for older hardware
4. **For Legacy Systems**: Use BIOS configuration for pre-2010 hardware

## Firmware Compatibility Matrix

| Feature | BIOS | UEFI | Secure Boot | TPM 2.0 |
|---------|------|------|-------------|---------|
| MBR partitions | ✓ | ○ | ○ | ✗ |
| GPT partitions | ○ | ✓ | ✓ | ✓ |
| Kernel signing | ✗ | ✗ | ✓ | ○ |
| Measured boot | ✗ | ✗ | ○ | ✓ |
| Serial console | ✓ | ○ | ○ | ✓ |
| Older systems | ✓ | ✗ | ✗ | ✗ |

Legend: ✓ = Native support, ○ = Supported with configuration, ✗ = Not supported

## Common Issues and Solutions

### System won't boot
- Check boot partition is accessible
- Verify bootloader files are present
- Check kernel and initramfs exist
- For Secure Boot: verify signatures
- For TPM: check TPM is enabled in firmware

### Boot menu doesn't appear
- Check TIMEOUT setting in boot.conf
- Press ESC during boot to force menu
- Verify boot entries are configured
- Check for hidden menu setting

### Console output not visible
- Add `console=tty0 console=ttyS0,115200n8` to kernel params
- Check display/graphics initialization
- Verify graphics drivers are loaded

### Performance is slow
- Review kernel parameters
- Disable unnecessary features
- Check for storage issues
- Monitor with `systemd-analyze`

## Related Documentation

- `../enterprise/SECURE_BOOT.md` - Secure Boot implementation
- `../enterprise/TPM2_INTEGRATION.md` - TPM 2.0 integration
- `../../docs/BOOT_CONFIGURATION.md` - Comprehensive boot documentation
- Linux kernel boot parameters: https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html

## Contributing

To add new boot configurations:

1. Create new subdirectory: `mkdir -p boot-configs/config-name/`
2. Add three files: `boot.conf`, `kernel-params.txt`, `README.md`
3. Document in this main README
4. Update hardware detection script if needed
5. Test on target hardware before committing
