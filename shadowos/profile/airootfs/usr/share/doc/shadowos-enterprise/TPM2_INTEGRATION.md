# TPM 2.0 Integration for ShadowCypher Enterprise

## Overview

This document describes the integration of Trusted Platform Module (TPM) 2.0 with ShadowCypher's encryption infrastructure for hardware-bound key sealing and integrity attestation. TPM 2.0 provides cryptographic capabilities resident on the hardware platform, enabling sealed key storage that cannot be extracted even by root-privileged processes.

## TPM 2.0 Capabilities

### Core Functions

- **Sealing**: Cryptographically bind data (encryption keys) to specific platform states via Platform Configuration Registers (PCRs)
- **Unsealing**: Retrieve sealed data only when PCRs match the sealing configuration
- **Attestation**: Generate cryptographic evidence of platform state for integrity validation
- **Key Derivation**: Generate deterministic keys from TPM seed material
- **Audit**: Hardware-based event logging of cryptographic operations

### Supported Algorithms

- **Hashing**: SHA-256 (standard), SHA-384, SHA-512
- **Asymmetric**: RSA-2048, ECC NIST curves
- **Symmetric**: AES-128, AES-256 (for key wrapping)

## Sealed Key Storage Architecture

### Data Flow

```
┌──────────────────────────────────────────────────────┐
│ ShadowCypher Encryption Key (256-bit)                │
│ (Master key for LUKS volume encryption)              │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ TPM 2.0 Sealing Process                              │
│ ─ Bind to PCR0 (Firmware)                            │
│ ─ Bind to PCR1 (Platform Configuration)              │
│ ─ Bind to PCR7 (Secure Boot State)                   │
│ ─ Encrypt with TPM Primary Key                       │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ Sealed Blob (cryptographically bound to hardware)    │
│ Stored in /var/lib/shadowcypher/tpm-sealed.blob      │
│ (Cannot be unsealed on different hardware/state)     │
└──────────────────────────────────────────────────────┘
```

### Key Management

1. **Primary Key**: TPM-resident, never extracted, created from TPM seed
2. **Sealed Blob**: Data sealed with TPM Public Key, locked to PCR configuration
3. **Unsealing**: Performed within TPM security boundary; key never leaves TPM in plaintext

### Unsealing Conditions

The encryption key is only unsealed when:
- TPM is available and responsive
- PCR0 (firmware) matches sealing configuration (firmware integrity)
- PCR1 (platform config) matches sealing configuration (hardware configuration)
- PCR7 (Secure Boot) matches sealing configuration (secure boot state)

## Hardware Security Binding

### PCR Selection Strategy

| PCR | Description | Binds To | Use Case |
|-----|-------------|----------|----------|
| PCR0 | Core Root of Trust for Measurement (CRTM) | Firmware integrity | Detects firmware modifications |
| PCR1 | Platform Configuration | Hardware components, BIOS settings | Detects hardware changes |
| PCR7 | Secure Boot State | Secure Boot enablement, Boot Manager | Detects secure boot bypass attempts |
| PCR8-15 | Boot Loader & Kernel | OS kernel measurements | Detects OS tampering |

### Recommended Configuration for ShadowCypher

**PCR0, PCR1, PCR7** (conservative binding)
- Detects major tampering (firmware, hardware, secure boot)
- Survives minor OS updates
- Balance between security and usability

**Extended: PCR0, PCR1, PCR2, PCR7** (strict mode)
- Includes bootloader measurements
- Requires bootloader verification after updates
- Maximum tamper detection

## Integration with LUKS Encryption

### Architecture

1. **LUKS Master Key**: Stored in TPM sealed state, never on disk in plaintext
2. **Unsealing at Boot**: systemd service unseals TPM blob before LUKS unlock
3. **Emergency Access**: Backup unsealing key (passphrase) available for recovery

### Boot Flow

```
1. Firmware/BIOS (PCR0 measured)
   ↓
2. Bootloader (PCR1, PCR7 measured)
   ↓
3. Kernel loads (PCR8 measured)
   ↓
4. systemd TPM sealing service starts
   ├─ Check TPM 2.0 availability
   ├─ Read sealed blob from /var/lib/shadowcypher/tpm-sealed.blob
   ├─ Verify PCRs match sealing policy
   ├─ Unseal LUKS master key
   ├─ Pass key to LUKS unlock (cryptsetup)
   └─ Mount encrypted volume
   ↓
5. ShadowCypher runtime operational
```

## Attestation and Integrity Validation

### Attestation Quote

TPM generates attestation quote containing:
- Current PCR values
- TPM clock (monotonic counter)
- Nonce (caller-provided, prevents replay)
- Signature (TPM private key, verifiable via TPM public cert)

### Integrity Validation Steps

1. **Collect Quote**: Request attestation quote from TPM with nonce
2. **Verify Signature**: Check quote signature using TPM public key
3. **Validate PCRs**: Compare current PCRs with expected values
4. **Validate Clock**: Ensure monotonic counter has advanced (detects replay)
5. **Audit Logging**: Record validation result with timestamp

### Audit Log Entry Format

```json
{
  "timestamp": "2026-01-15T10:23:45Z",
  "event_type": "tpm_attestation",
  "result": "success|failure",
  "pcr_values": {
    "pcr0": "abcd1234...",
    "pcr1": "efgh5678...",
    "pcr7": "ijkl9012..."
  },
  "tpm_clock": 12345678,
  "nonce": "random_value_used",
  "signature_valid": true,
  "deviation": null,
  "remediation": null
}
```

## Recovery Without TPM

### Scenarios Requiring Recovery

1. **TPM Hardware Failure**: Module non-responsive or corrupted
2. **TPM Firmware Update**: Clears PCRs, sealing becomes invalid
3. **Motherboard Replacement**: Different TPM, cannot unseal
4. **Secure Boot Modification**: Intentional security policy change

### Recovery Methods

#### Method 1: Backup Unsealing Key (Recommended)

A backup passphrase/key stored in a secure location (password manager, safe):

```bash
# Recovery command
cryptsetup open /dev/encrypted_device shadowcypher --key-file=<backup_key_path>
```

**Security**: Backup key is distinct from TPM seal, provides independent access path.

#### Method 2: Physical Access Recovery

If physical access is available:

1. Boot from recovery media (USB)
2. Run `tpm2-config.sh recovery-unlock`
3. Provide administrative credentials
4. Decrypt with backup key or recovery passphrase
5. Reseal keys after recovery

#### Method 3: Emergency Passphrase

For catastrophic failure, a second-factor passphrase encrypted with a key not dependent on TPM:

```
Emergency Access Protocol:
1. Provide emergency passphrase (stored separately, e.g., written down in vault)
2. Derive emergency key from passphrase + device identifier
3. Unlock LUKS with emergency key
4. Proceed with recovery
```

### Recovery Audit

All recovery attempts logged:
- Timestamp
- Recovery method used
- Operator identification
- Success/failure
- Subsequent re-sealing confirmation

## Threat Model and Assumptions

### Assumptions

1. **Hardware Trust**: TPM 2.0 module is genuine, firmware is not compromised
2. **Secure Boot**: Secure Boot is enabled and enforced
3. **UEFI/BIOS**: Firmware is kept updated
4. **Physical Security**: Device is protected against cold-boot attacks (e.g., via FDE + RAM encryption)
5. **Entropy**: System has sufficient entropy for random number generation

### Threat Coverage

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Encryption key extraction (disk) | Sealed in TPM, never plaintext on disk | Low (requires TPM compromise) |
| Firmware tampering | PCR0 sealing detects modification | Low (depends on boot integrity) |
| Hardware swap attacks | PCR1 sealing detects hardware change | Low (TPM tied to hardware) |
| Secure Boot bypass | PCR7 sealing detects changes | Low (if Secure Boot enforced) |
| Cold-boot attacks | Full-disk encryption + RAM encryption | Medium (depends on implementation) |
| TPM extraction attacks | Hardware-based cryptography, sealed by design | Medium (depends on TPM version/quality) |
| Replay attacks | Nonce + monotonic counter in attestation | Low (time-based protection) |

### Out of Scope

- **Physical attacks on TPM** (e.g., side-channel, hardware reverse engineering)
- **Malicious firmware** (assumes firmware is trustworthy)
- **Compromised OS kernel** (assumes kernel has not been patched post-boot)
- **Malicious hypervisor** (VM attestation requires vTPM and different architecture)

## Implementation Details

### TPM Device

- **Location**: `/dev/tpm0` (standard Linux TPM device)
- **Access**: Requires root privilege or membership in `tpm` group
- **Backend**: tpm2-tools (userspace tools), tpm2-abrmd or tpm2-tss (TPM access daemon)

### Dependencies

- `tpm2-tools` (command-line TPM 2.0 tools)
- `tpm2-abrmd` or `tpm2-tss-abrmd` (TPM access broker daemon)
- `cryptsetup` (LUKS encryption)
- `jq` (JSON processing)
- `openssl` (certificate validation)

### Configuration Files

- `/etc/tpm2-sealing.json` - Sealing policy, PCR selection
- `/var/lib/shadowcypher/tpm-sealed.blob` - Sealed encryption key blob
- `/var/log/shadowcypher-tpm.log` - TPM operation audit log

## Security Best Practices

1. **Secure Boot Always Enabled**: Ensures PCR7 integrity
2. **TPM Firmware Updates**: Install vendor updates to patch vulnerabilities
3. **Backup Key Storage**: Store recovery key securely (separate from device)
4. **Audit Review**: Regularly review TPM audit logs for anomalies
5. **Attestation Verification**: Periodically validate attestation quotes
6. **Recovery Drills**: Test recovery procedures quarterly
7. **Monitoring**: Alert on PCR mismatches, unsealing failures

## Operational Procedures

### Initial Setup

1. Verify TPM 2.0 presence: `tpm2-config.sh check`
2. Initialize TPM environment: `tpm2-config.sh init`
3. Create sealing policy: `tpm2-config.sh seal-create`
4. Seal encryption key: `tpm2-config.sh seal-key`
5. Generate backup key: `tpm2-config.sh backup-key-generate`
6. Verify unsealing: `tpm2-config.sh unseal-test`

### Ongoing Maintenance

- Monitor TPM health: monthly attestation verification
- Review audit logs: weekly summary
- Update recovery keys: annually or after hardware changes
- Firmware updates: apply within 30 days of release

### Emergency Recovery

1. Boot from recovery media
2. Run: `tpm2-config.sh recovery-unlock --backup-key /path/to/backup`
3. Validate system integrity
4. Re-seal keys: `tpm2-config.sh seal-key --resealing`

## References

- [TPM 2.0 Specification](https://trustedcomputinggroup.org/resource/tpm-2-0-library-specification/)
- [tpm2-tools Documentation](https://github.com/tpm2-software/tpm2-tools)
- [Linux Kernel TPM Support](https://www.kernel.org/doc/html/latest/security/tpm/index.html)
- [LUKS and TPM Integration](https://www.freedesktop.org/wiki/Software/systemd/TPMPCRLocking/)
- [TCG Platform Firmware Profile](https://trustedcomputinggroup.org/resource/pc-client-platform-firmware-profile-specification/)

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-15 | ShadowCypher Security | Initial TPM 2.0 integration specification |

---

**Classification**: Enterprise Security Documentation
**Audience**: System Administrators, Security Teams
**Last Updated**: 2026-01-15
