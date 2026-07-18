# ShadowCypher Hardware-Specific Boot Configurations

## Overview

This document defines secure boot profiles and hardware configurations for ShadowCypher deployment across different hardware classes. These configurations ensure consistent security posture, firmware integrity verification, and TPM-based key management across diverse deployment environments.

## Boot Configuration Profiles

### Profile Categories

1. **Enterprise Server** - High-security datacenter deployments with full TPM2.0 support
2. **Workstation** - Secure development and analyst workstations
3. **Edge Device** - Embedded and edge computing deployments with TPM1.2/2.0
4. **Legacy Hardware** - Older systems with minimal firmware security support
5. **Air-Gapped** - Isolated systems with manual boot media verification

## UEFI/BIOS Configuration Requirements

### Secure Boot Settings

#### Enable Secure Boot
- **UEFI Setting**: Security → Secure Boot → Enable
- **Requirement**: Mandatory for profiles: Enterprise Server, Workstation
- **Optional**: Edge Device
- **Not Applicable**: Legacy Hardware, Air-Gapped
- **Purpose**: Prevent unsigned bootloader execution

#### Secure Boot Mode
- **Setting**: Security → Secure Boot Mode → Standard (not Custom)
- **Certificates**: Load UEFI db, KEK, PK defaults
- **Custom Keys**: Only in controlled datacenter environments with key escrow

#### Shim and GRUB Signing
- **Requirement**: Boot via UEFI-signed shim bootloader
- **Digest Algorithm**: SHA-256 minimum
- **Key Rotation**: Annual or per security advisory

### UEFI Firmware Variables (efivarfs)

#### Boot Order Management
```
efivar -d --name BootOrder          # Display current boot order
efivar --name Boot0000              # Display specific boot entry
```

#### Boot Entry Management
- Boot entries numbered Boot0000 through BootFFFF
- BootOrder variable defines startup sequence
- BootCurrent shows currently executing entry
- BootNext specifies single-boot override

#### Common Boot Variables
- `BootOrder`: Sequence of boot entry numbers
- `BootCurrent`: Currently executing boot entry
- `BootNext`: Next boot entry (used once)
- `BootXXXX`: Individual boot entry definitions
- `Timeout`: Boot menu timeout in seconds
- `BootOptionSupport`: Firmware capabilities

### TPM (Trusted Platform Module) Requirements

#### TPM 2.0 (Recommended)
- **Hardware Support**: Intel PTT / AMD fTPM / Discrete TPM 2.0
- **Uefi Setting**: Security → TPM Device → Enable
- **BIOS Setting**: Security → TPM → Enable
- **PCR Strategy**: Use PCRs 0-2 (firmware integrity), 4-7 (boot code)

#### TPM 1.2 (Legacy Support)
- **Specification**: TCG TPM 1.2 Rev 103
- **Firmware Setting**: Security → TPM Device → Enable (if available)
- **Limitations**: Smaller PCR size, fewer algorithms
- **Use Case**: Edge Device profile only

#### TPM Firmware Protection
- **Sealed Secrets**: Use TPM PCRs to protect encryption keys
- **PCR Binding**: Lock secrets to specific firmware/bootloader state
- **PCR Extend**: Software can extend PCRs during boot

### Memory Protection

#### Execute Disable (XD/NX) Bit
- **Setting**: BIOS → Processor → Execute Disable Bit → Enable
- **Linux Parameter**: `status=enable` in kernel command line
- **Purpose**: Prevent code execution from data pages

#### Data Execution Prevention (DEP)
- **Setting**: BIOS → Security → NX → Enable
- **Windows Parameter**: `/NOEXECUTE=OPTIN` (legacy)
- **Linux Parameter**: Already enabled by default

### IOMMU/VT-d Configuration

#### Intel VT-d (Virtualization Technology for Directed I/O)
- **Setting**: BIOS → Chipset → VT-d → Enable
- **Purpose**: DMA protection, nested virtualization
- **Kernel Parameter**: `intel_iommu=on`

#### AMD-Vi (AMD IOMMU)
- **Setting**: BIOS → Chipset → IOMMU → Enable
- **Kernel Parameter**: `amd_iommu=on`

### Secure Boot Keys

#### Platform Key (PK)
- **Owner**: System manufacturer or integrator
- **Signed By**: Owner's private key
- **Purpose**: Root of trust for UEFI firmware security

#### Key Exchange Key (KEK)
- **Signer**: Platform Key holder
- **Purpose**: Signs Database and Exclusion Database entries

#### Signature Database (db)
- **Signer**: KEK
- **Content**: Bootloader, kernel, driver signatures
- **Maintenance**: Updated via firmware updates or manual entry

#### Exclusion Database (dbx)
- **Signer**: KEK
- **Content**: Revoked bootloader/driver hashes
- **Maintenance**: Updated via Microsoft security advisories

## Hardware Classes

### Enterprise Server
- **CPU Architecture**: x86_64 (Intel/AMD)
- **Memory**: 16GB+ ECC RAM
- **Storage**: Enterprise SSD/NVMe with secure erase
- **TPM**: Discrete TPM 2.0 or fTPM
- **Network**: 10GbE+ with PXE boot support
- **Security**: IPMI/Redfish with strong authentication
- **Boot Method**: UEFI, Secure Boot enabled, PXE fallback

### Workstation
- **CPU Architecture**: x86_64 (Intel/AMD)
- **Memory**: 8GB+ RAM
- **Storage**: NVMe with OPAL support
- **TPM**: Intel PTT or AMD fTPM 2.0
- **Display**: HDMI/DP with UEFI graphics
- **Security**: BIOS password, physical port locks
- **Boot Method**: UEFI, Secure Boot enabled

### Edge Device
- **CPU Architecture**: ARM (64-bit) or x86_64
- **Memory**: 2GB+ RAM
- **Storage**: eMMC or microSD with write protection
- **TPM**: TPM1.2 or TPM2.0 (if available)
- **Network**: Ethernet or cellular with fallback
- **Security**: Limited: minimal user interface
- **Boot Method**: U-Boot with minimal validation

### Legacy Hardware
- **CPU Architecture**: x86_64 (older microcode)
- **Memory**: 4GB+ RAM
- **Storage**: SATA SSD
- **TPM**: Usually absent
- **Security**: BIOS password only
- **Boot Method**: BIOS + legacy MBR, or UEFI without Secure Boot

### Air-Gapped
- **CPU Architecture**: x86_64
- **Memory**: 8GB+ RAM
- **Storage**: Internal SSD only, no external interfaces
- **TPM**: Optional (manual key entry if absent)
- **Network**: Disabled at BIOS level
- **Security**: BIOS password, physical security
- **Boot Method**: UEFI with manual verification

## Boot Process Security Flow

### Phase 1: Firmware (UEFI/BIOS)
1. Power-on self-test (POST)
2. Firmware integrity verification (if TPM)
3. Load Setup.efi or MokManager
4. Measure firmware to TPM PCR0
5. Execute bootloader from boot device

### Phase 2: Bootloader (Shim + GRUB)
1. UEFI loads shim (signed by secure boot key)
2. Shim verifies GRUB signature (signed by owner key)
3. GRUB measures itself and kernel to TPM PCR2
4. GRUB loads kernel with verified signature
5. GRUB passes control to kernel with PCR state

### Phase 3: Kernel (Linux)
1. Kernel initializes with PCR state available
2. Kernel extends PCRs with boot parameters (PCR4-7)
3. Initramfs verifies system critical files
4. Kernel mounts filesystem (encrypted, if configured)
5. Kernel executes init process

### Phase 4: Application (ShadowCypher)
1. Init system mounts encrypted volumes using TPM-sealed keys
2. ShadowCypher services start with integrity verification
3. Runtime attestation validates boot chain
4. Application operates with guaranteed boot integrity

## Firmware Update Strategy

### Secure Firmware Updates
1. **Validation**: Verify firmware signature before update
2. **Atomicity**: Use firmware's rollback protection
3. **Recovery**: Maintain previous firmware in safe storage
4. **Attestation**: Measure new firmware state to TPM

### Firmware Rollback Protection
- **Hardware Support**: Monotonic counter in NVM
- **Verification**: Reject firmware older than current version
- **Emergency**: Manual recovery via USB with key authorization

## Performance Considerations

### Secure Boot Overhead
- **Time Impact**: 200-500ms additional boot time
- **Memory Impact**: 50-100MB for verification code
- **CPU Impact**: Minimal (hardware crypto acceleration)

### TPM Operations
- **Seal/Unseal**: 10-50ms per operation
- **Quote Operation**: 5-20ms
- **Extend PCR**: <1ms

## Configuration Deployment

### Automated Configuration
Use `boot-config.sh` to apply profiles:
```bash
sudo ./boot-config.sh apply enterprise-server
sudo ./boot-config.sh validate
sudo ./boot-config.sh report
```

### Manual Configuration
For air-gapped or restricted environments:
1. Power off system
2. Enter UEFI/BIOS setup (DEL, F2, F10, ESC key at boot)
3. Navigate to Security section
4. Enable Secure Boot, TPM, VT-d/IOMMU
5. Set BIOS password
6. Save and exit

### Verification
After applying configuration:
```bash
sudo ./boot-config.sh validate
sudo efibootmgr -v
sudo tpm2_getcap handles-persistent
```

## Security Best Practices

1. **Boot Media Verification**: Always verify boot media cryptographic signature
2. **TPM Attestation**: Collect PCR quotes during boot for audit trail
3. **Key Escrow**: Store encryption keys in secure facility for enterprise
4. **Regular Audits**: Audit firmware, bootloader, and kernel signatures monthly
5. **Firmware Lock**: Physically lock firmware settings with administrator password
6. **No USB Boot**: Disable USB boot in production unless needed
7. **Network Boot Timeout**: Minimize PXE timeout to prevent slow boot
8. **Update Schedule**: Apply firmware updates within 30 days of release

## Troubleshooting

### Secure Boot Boot Failures
- **Symptom**: "Secure Boot Violation" or loop
- **Check**: Bootloader signature, UEFI database, firmware version
- **Recovery**: Boot from unsigned media, disable Secure Boot temporarily

### TPM Attestation Failures
- **Symptom**: PCR mismatch during attestation
- **Check**: Firmware version, bootloader version, kernel parameters
- **Recovery**: Re-extend PCRs or reset TPM (destructive)

### Boot Variable Corruption
- **Symptom**: Unbootable system, cannot modify BootOrder
- **Check**: UEFI variable storage status
- **Recovery**: Reload defaults from UEFI setup

## References

- [UEFI Forum Specifications](https://uefi.org/specifications)
- [TCG TPM 2.0 Specification](https://trustedcomputinggroup.org/resource/tpm-library-specification/)
- [Secure Boot and UEFI](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot)
- [efibootmgr Man Page](https://linux.die.net/man/8/efibootmgr)
- [tpm2-tools Documentation](https://github.com/tpm2-software/tpm2-tools/wiki)
