# UEFI Secure Boot Implementation

## Overview

UEFI Secure Boot is a security standard that ensures only authorized code can be executed during the boot process. This implementation provides enterprise-grade boot firmware security for ShadowCypher systems, preventing boot-level attacks and establishing a cryptographic chain of trust from firmware to kernel.

## UEFI Secure Boot Architecture

### Key Components

1. **Platform Key (PK)**
   - Top-level key in the trust hierarchy
   - Controlled by the platform owner (enterprise administrator)
   - Signs the Key Exchange Key (KEK)
   - Only one PK can be active; changing it resets the Secure Boot state

2. **Key Exchange Key (KEK)**
   - Second-level key signed by PK
   - Manages the Signature Database (db) and Forbidden Database (dbx)
   - Multiple KEKs can coexist
   - Platform can revoke KEKs via new PK signatures

3. **Signature Database (db)**
   - Contains certificates, keys, and hashes of authorized bootloaders and kernels
   - Signed by KEK
   - Critical for allowing legitimate boot components
   - Supports multiple entries for different certificates

4. **Forbidden Database (dbx)**
   - Blacklist of revoked certificates, keys, and hashes
   - Signed by KEK
   - Takes precedence over db entries
   - Used for emergency revocation of compromised components

### Boot Verification Flow

```
+---------------------+
| UEFI Firmware       |
| (ROM Verification)  |
+----------+----------+
           |
           v
+---------------------+
| PK Signature Check   |
| (Verify KEK)       |
+----------+----------+
           |
           v
+---------------------+
| KEK Signature Check  |
| (Verify db/dbx)    |
+----------+----------+
           |
           v
+---------------------+
| Bootloader (GRUB)   |
| Signature Verified  |
+----------+----------+
           |
           v
+---------------------+
| Kernel & Modules    |
| Signature Verified  |
+---------------------+
```

## Key Management Strategy

### Key Generation

- **PK**: RSA-2048 or RSA-4096 (enterprise standard: 4096)
- **KEK**: RSA-2048 or RSA-4096
- **db/dbx**: SHA-256 hashes or certificates

### Key Storage

- **Secure Storage**: `/etc/secure-boot/keys/`
- **Permissions**: 0600 (owner read/write only)
- **Encryption**: Optional at-rest encryption for private keys
- **Backup**: Offsite encrypted backup required

### Key Enrollment

Keys are enrolled into EFI variables:

- `PK` (Platform Key)
- `KEK` (Key Exchange Key)
- `db` (Signature Database)
- `dbx` (Forbidden Database)

Enrollment requires:
- UEFI Setup mode or physical access
- Proper EFI variable permissions
- Atomicity to prevent partial states

## Bootloader Signing and Verification

### GRUB Signing Process

1. Generate GRUB binary signature using DB certificate
2. Create detached signature file (.sig)
3. Update GRUB configuration to verify signature
4. Enroll GRUB binary hash in db or sign with certificate

### Signature Verification

UEFI firmware verifies GRUB bootloader:
- Checks signature against db certificates
- Rejects if signature is invalid
- Rejects if hash is in dbx
- Falls back to boot failure if verification fails

### Rollback Protection

- Implement bootloader versioning
- Track previous versions in secure storage
- Revoke old versions by adding hashes to dbx
- Prevent downgrade attacks

## GRUB Integration

### GRUB Configuration

```
# /etc/default/grub modifications for Secure Boot
GRUB_EARLY_INITRD_LINUX_CUSTOM="/boot/verify-initrd"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash secure_boot=1"
GRUB_DISABLE_RECOVERY="true"
GRUB_TERMINAL_INPUT="console"
GRUB_TERMINAL_OUTPUT="console"
```

### Kernel Module Verification

- Load only signed kernel modules
- Use `module.sig_enforce=1` kernel parameter
- Deny unsigned module loading in Secure Boot mode

### EFI Boot Entry Management

- Create custom EFI boot entries
- Order entries to prefer Secure Boot path
- Implement boot timeout to prevent user bypass
- Audit boot entry modifications

## Shim Bootloader for Linux

### Purpose

Shim is a minimal bootloader that:
- Bridges UEFI Secure Boot and Linux bootloaders (GRUB)
- Is signed by Microsoft (for wide compatibility)
- Can be signed by CA for enterprise deployment
- Implements MokManager for boot-time key management

### Shim Components

1. **shim.efi**: Main bootloader (signed by Microsoft)
2. **MokManager.efi**: Management utility for Secure Boot keys
3. **fallback.efi**: Recovery mechanism

### Implementation Steps

1. Install shim package
2. Copy shim.efi to EFI partition
3. Configure shim to load GRUB
4. Enroll GRUB in Machine Owner Key (MOK)
5. Configure MokManager for recovery

## Chain of Trust Validation

### Trust Chain Establishment

```
Firmware PK
    ↓ (validates)
KEK Certificate
    ↓ (validates)
db Certificates
    ↓ (validates)
Shim.efi (Microsoft signed)
    ↓ (validates via MOK)
GRUB.efi (CA signed)
    ↓ (validates)
Kernel (signed with db certificate)
    ↓ (validates)
Kernel Modules (signed)
```

### Verification Points

- **Firmware Level**: PK and KEK verification
- **Bootloader Level**: db and GRUB signature verification
- **Kernel Level**: Kernel image and module signatures
- **Runtime**: Module signature enforcement

### Audit Points

- Boot attempt logging in EFI firmware
- GRUB verification logs
- Kernel module loading audit (auditd)
- System message buffer (dmesg)

## Disabling Secure Boot Recovery

### Preventing Unauthorized Disabling

1. **UEFI Setup Password**: Prevent Secure Boot toggle without password
2. **PK Protection**: Require PK password to change keys
3. **Firmware Lockdown**: Disable firmware update without credentials
4. **Physical Security**: BIOS battery removal disabled

### Emergency Recovery Process

1. Physical access requirement (TPM challenge)
2. Administrative credential verification
3. Recovery key escrow (split between admins)
4. Audit logging of all recovery attempts
5. Mandatory re-enrollment after recovery

### Secure Boot Disable Prevention

```
# systemd-boot configuration
[Loader]
SecureBootMode=force
DisableFallback=yes
EditorDisabledInSetup=yes
TokenizeDomainNames=no
```

## Threat Model: Boot Firmware Attacks

### Attack Vectors

1. **Bootkit/Rootkit Injection**
   - Attacker replaces bootloader with malicious version
   - Runs before OS, with full system control
   - **Mitigation**: Bootloader signature verification

2. **Firmware Modification**
   - Direct flash of firmware with malicious code
   - Bypasses bootloader security entirely
   - **Mitigation**: Firmware signing, flash protection

3. **Secure Boot Disabling**
   - Attacker disables Secure Boot via Setup menu
   - Loads unsigned malicious bootloader
   - **Mitigation**: Setup password, PK enrollment lock

4. **Key Compromise**
   - Attacker obtains private key material
   - Can sign arbitrary bootloaders
   - **Mitigation**: Strong key storage, DBX revocation, key rotation

5. **EFI Variable Tampering**
   - Attacker modifies db/dbx EFI variables
   - Revokes legitimate boot components
   - **Mitigation**: Access control lists (ACLs), firmware ACL enforcement

6. **Downgrade Attack**
   - Attacker reverts to older vulnerable bootloader
   - Exploits known vulnerabilities
   - **Mitigation**: Version tracking, DBX revocation

7. **Race Conditions**
   - Exploit timing window during boot
   - **Mitigation**: Atomic operations, monotonic counters

### Defense Layers

- **Layer 1**: Firmware integrity (ROM hash verification)
- **Layer 2**: Key hierarchy (PK → KEK → db)
- **Layer 3**: Bootloader signing (GRUB certificate)
- **Layer 4**: Kernel module enforcement (signature validation)
- **Layer 5**: Runtime integrity monitoring (auditd, auditbeat)

## Security Considerations

### Key Rotation Strategy

- **Annual**: Full PK rotation for maximum security
- **Quarterly**: KEK rotation if compromise suspected
- **On-Demand**: Immediate DBX update for zero-days

### Compliance Requirements

- **UEFI Secure Boot**: UEFI 2.1+
- **TPM Integration**: Optional TPM 2.0 for additional protection
- **FIPS 140-2**: Use FIPS-approved algorithms
- **Enterprise Standards**: Align with SOC 2, ISO 27001

### Monitoring and Alerting

- Boot verification failures (syslog)
- Unsigned module load attempts (auditd)
- Secure Boot status changes (systemd-logind)
- Key enrollment modifications (firmware logs)

## Implementation Checklist

- [ ] Verify UEFI firmware support
- [ ] Generate PK, KEK, db certificates
- [ ] Prepare EFI partition
- [ ] Install shim bootloader
- [ ] Sign GRUB bootloader
- [ ] Enroll keys into EFI variables
- [ ] Configure kernel parameters
- [ ] Test boot process
- [ ] Verify signature enforcement
- [ ] Document recovery procedures
- [ ] Set up monitoring
- [ ] Create audit trail

## References

- UEFI Specification 2.10: https://uefi.org/specifications
- Shim Project: https://github.com/rhboot/shim
- Linux Kernel Module Signing: https://www.kernel.org/doc/html/latest/admin-guide/module-signing.html
- GRUB Secure Boot Guide: https://www.gnu.org/software/grub/manual/
- Microsoft Security Baselines: https://microsoft.com/en-us/security/
