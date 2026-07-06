# TPM 2.0 Boot Configuration

This directory contains boot configuration files for systems with Trusted Platform Module 2.0 (TPM 2.0).

## Overview

TPM 2.0 provides cryptographic hardware for:

- Measured boot with Platform Configuration Registers (PCRs)
- Secure key storage and sealing
- System attestation and remote verification
- Integrity Measurement Architecture (IMA) integration
- Hardware-based encryption support
- Audit logging and event recording

## Files

### boot.conf
TPM 2.0 configuration for measured boot and attestation. Includes:
- TPM device path and command interface
- PCR (Platform Configuration Register) indices
- Measured boot event log configuration
- TPM key storage and sealing settings
- IMA and EVM (Extended Verification Module) integration
- Attestation server configuration
- TPM NV (Non-Volatile) storage indexes

### kernel-params.txt
Kernel parameters optimized for TPM 2.0 systems. Includes:
- TPM 2.0 device driver settings
- IMA enforcement policy and hash algorithms
- EVM (Extended Verification Module) configuration
- dm-verity for read-only filesystem verification
- Enhanced kernel hardening for TPM systems
- TPM logging and attestation parameters

## TPM 2.0 Architecture

### Platform Configuration Registers (PCRs)

PCRs extend measurements of system components through boot:

| PCR | Component | Use |
|-----|-----------|-----|
| 0 | BIOS/UEFI Firmware | Firmware integrity |
| 1 | BIOS Configuration | Setup options |
| 2 | Bootloader | Second-stage loader |
| 3 | Boot Configuration | Boot parameters |
| 5 | GPT Partition Table | Partition integrity |
| 7 | Secure Boot State | SB auth status |
| 9 | IMA Measurements | Kernel files (dynamic) |
| 10 | IMA Event Log | Boot cmdline (dynamic) |

### Key Storage and Sealing

TPM provides two types of key storage:

1. **Sealed Keys**: Encrypted in TPM, can only be decrypted when system state matches PCR values
2. **Unrestricted Keys**: Stored in TPM but exportable

```bash
# Seal key to PCR 9,10 (kernel + cmdline)
tpm2_createprimary -C o -g sha256 -G rsa -c primary.ctx
tpm2_create -C primary.ctx -g sha256 -G aes \
  -r seal_to_pcr.priv -u seal_to_pcr.pub \
  -L pcr:sha256:9,10=policy.pcr -i key_value
```

## Measured Boot

Measured boot verifies the entire boot chain:

1. BIOS measures firmware code and extends PCR 0
2. Bootloader measures and extends PCR 2
3. Kernel measures and extends PCR 9 (via IMA)
4. Userspace components measured via IMA
5. Event log records all measurements with hashes

### Checking Measurements

```bash
# View PCR values
tpm2_pcrread sha256

# View extended PCRs
tpm2_pcrread -o /dev/stdout sha256:9,10 | xxd

# Parse event log
tpm2_eventlog /sys/kernel/debug/tpm0/eventlog
```

## Integrity Measurement Architecture (IMA)

IMA provides runtime file integrity checking:

- Measures files on execution or access
- Creates cryptographic audit trail
- Can prevent execution of modified files
- Integrates with AppArmor for enforcement

### IMA Policies

```bash
# View current IMA policy
cat /sys/kernel/security/ima/policy

# View IMA measurements
cat /sys/kernel/security/ima/ascii_runtime_measurements
```

## Extended Verification Module (EVM)

EVM protects IMA metadata from tampering:

- Signs file extended attributes (xattr)
- Prevents xattr modification outside EVM
- Requires EVM key enrollment

### EVM Setup

```bash
# Generate EVM key
openssl genrsa -out evm.key 2048
openssl x509 -req -in evm.csr -signkey evm.key -out evm.crt

# Load EVM key
keyctl padd user evm_key @u < evm.key
```

## Attestation

Remote attestation verifies system integrity via TPM:

1. Remote verifier challenges system
2. System generates quote (TPM signature over PCR values)
3. Verifier checks signature and PCR values
4. Determines if system is trusted

### Generating a Quote

```bash
# Create quote with nonce
tpm2_quote -C ak.ctx -g sha256 \
  -l sha256:0,1,2,3,5,7,9,10 \
  -m quote.msg -s quote.sig \
  -n nonce_file
```

## Troubleshooting

### TPM not detected
- Check BIOS/UEFI firmware has TPM enabled
- Verify TPM 2.0 support: `ls -la /dev/tpm0`
- Check kernel recognizes TPM: `dmesg | grep -i tpm`
- Install tpm2-tools: `tpm2_getcap handles-transient`

### IMA measurements missing
- Enable IMA in kernel: `cat /sys/kernel/security/ima/policy`
- Check filesystem extended attributes: `mount | grep xattr`
- Verify kernel params include `ima=enforce`

### EVM verification failing
- Check EVM key enrolled: `keyctl list %keyring:.ima`
- Verify xattr are properly signed
- Review error logs: `dmesg | grep -i evm`

### PCR values don't match expected
- Generate reference measurements on known-good system
- Compare PCR values: `tpm2_pcrread sha256`
- Check event log for unexpected entries
- May indicate modified boot components

## References

- TPM 2.0 Specification: https://trustedcomputinggroup.org/
- Linux IMA/EVM documentation
- tpm2-tools GitHub: https://github.com/tpm2-software/tpm2-tools
- systemd-cryptenroll for TPM integration
