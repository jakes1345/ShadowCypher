# FIPS 140-2 Mode Toggle for ShadowCypher Enterprise

## Overview

This document details FIPS 140-2 Level 1 compliance implementation for ShadowCypher, providing a cryptographically hardened mode suitable for enterprise and government deployments. FIPS 140-2 (Federal Information Processing Standards) mandates the use of validated cryptographic modules and approved algorithms.

## FIPS 140-2 Level 1 Compliance

**Level 1** is the basic assurance level, requiring the use of approved algorithms and modules, but without additional physical security measures.

### Requirements Met
- Use of NIST-approved cryptographic algorithms
- OpenSSL FIPS module (FIPS Object Module v2.0.18)
- Kernel crypto API for hardware acceleration
- Self-testing on module initialization
- Restricted key material generation to approved mechanisms

### Approved Algorithms

**Symmetric Encryption (AES only)**
- AES-128-CBC
- AES-192-CBC
- AES-256-CBC
- AES-128-GCM
- AES-192-GCM
- AES-256-GCM

**Asymmetric Encryption (RSA only)**
- RSA with minimum 2048-bit keys
- PKCS#1 v2.0 padding (OAEP)

**Elliptic Curve Cryptography (ECC)**
- ECDSA with NIST P-256 (secp256r1)
- ECDSA with NIST P-384 (secp384r1)
- ECDSA with NIST P-521 (secp521r1)
- ECDH for key agreement

**Hash Algorithms**
- SHA-1 (legacy, only for signatures and key derivation)
- SHA-224, SHA-256, SHA-384, SHA-512
- SHA-512/224, SHA-512/256

**Key Derivation**
- PBKDF2 with SHA-256 (minimum 10,000 iterations)
- HKDF with approved hash functions

**Random Number Generation**
- /dev/urandom for seed material
- SP 800-90A approved DRBG

### Explicitly Forbidden Algorithms

When FIPS mode is enabled:
- MD5, MD4, MD2
- DES, 3DES, RC2, RC4
- SHA-0 (original SHA)
- RSA with keys < 2048 bits
- ECC with non-NIST curves (secp256k1, ed25519, chacha20, etc.)
- Custom or unvalidated algorithms

## OpenSSL FIPS Module Integration

### Version and Verification
- OpenSSL 3.x with FIPS provider (openssl-3.x-fips)
- OpenSSL 1.1.1 FIPS Object Module (legacy, for compatibility)
- Load FIPS provider explicitly in application initialization

### OpenSSL Configuration

Create/modify `/etc/ssl/fips.conf` for FIPS mode:

```
openssl_conf = openssl_init

[openssl_init]
fips = fips_sect
providers = provider_sect

[fips_sect]
activate = 1

[provider_sect]
fips = fips_provider
base = base_provider

[fips_provider]
module = /usr/lib64/openssl/modules/fips.so
activate = 1

[base_provider]
module = /usr/lib64/openssl/modules/base.so
activate = 1
```

### Self-Tests
The FIPS module performs self-tests automatically on:
- Module initialization
- Every cryptographic operation (integrity check)
- Key generation
- Signature verification

Self-tests validate:
- Module integrity (HMAC self-check)
- Algorithm correctness
- Critical cryptographic functions
- Key derivation functions

Tests must complete within 30 seconds; failure triggers operational error.

## Kernel Crypto API Configuration

### Linux Kernel Crypto API
Enable kernel-level cryptographic acceleration for better performance:

```bash
# Enable kernel crypto modules
modprobe aes-generic
modprobe sha256_generic
modprobe ecdsa

# For Intel AES-NI (hardware acceleration)
modprobe aesni_intel
modprobe ghash_clmul_intel

# For AMD (if applicable)
modprobe aesni_intel
```

### System Crypto Policy

Use system-wide crypto policies (RHEL/Fedora/CentOS):

```bash
# Set to FIPS-compliant policy
update-crypto-policies --set FIPS

# Or for stricter enforcement
update-crypto-policies --set FIPS:SHA1
```

This configures:
- OpenSSL cipher suites
- GnuTLS defaults
- NSS cryptographic defaults
- Libssh crypto settings

## Compliance Validation

### Pre-Deployment Checklist
- [ ] OpenSSL FIPS module installed and verified
- [ ] Kernel modules loaded (aesni_intel if available)
- [ ] System crypto policies configured
- [ ] All approved algorithms in use
- [ ] No forbidden algorithms in codebase
- [ ] Minimum key sizes enforced (2048-bit RSA, 256-bit ECC)
- [ ] Random number generation sourced from /dev/urandom
- [ ] Self-tests pass without errors
- [ ] Compliance validation script runs successfully
- [ ] Audit logs configured

### Compliance Validation Script

The `fips-enable.sh` script performs:
1. Module availability verification
2. OpenSSL FIPS provider functionality test
3. Self-test execution and validation
4. Algorithm restriction enforcement
5. Key size validation
6. Compliance report generation
7. Audit trail documentation

### Compliance Reporting

Generate compliance evidence for:
- FedRAMP authorization
- NIST 800-171 (CMMC Level 1)
- DOD Impact Level 2-5 systems
- Healthcare (HIPAA)
- PCI-DSS Level 1
- SOC 2 Type II

## Performance Impact

FIPS mode imposes measurable performance costs:

**Throughput Reduction**: 5-15% for typical workloads
- AES-GCM: 3-8% slower
- RSA-2048: 2-5% slower
- ECDSA P-256: minimal impact (<1%)

**Latency Increase**: 1-3ms per operation
- Signature generation: +1ms average
- Key derivation: +2-5ms (PBKDF2)

**Memory Overhead**: ~2-5MB for FIPS module + caches

**Optimization Strategies**:
- Enable hardware acceleration (AES-NI)
- Use connection pooling for TLS
- Cache derived keys where possible
- Pre-generate key material during initialization

## Integration with Guardian Vault

### Vault Key Material Protection

All Guardian vault secrets are protected under FIPS-approved algorithms:

```json
{
  "vault_encryption": {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2-SHA256",
    "pbkdf2_iterations": 100000,
    "key_size_bits": 256
  }
}
```

### Compliance Guarantees

When FIPS mode is enabled:
- All vault keys derived via PBKDF2-SHA256
- Vault secrets encrypted with AES-256-GCM
- Authentication tokens use HMAC-SHA256
- Master key sealed with RSA-2048-OAEP or ECDSA P-384

### Vault Audit Requirements

Maintain detailed audit logs:
- All vault access (READ, WRITE, DELETE operations)
- Key rotation events
- Algorithm changes
- FIPS mode toggles
- Self-test results
- Compliance validation checks

## Compliance Reporting

### Generate Compliance Report

```bash
./fips-enable.sh --report
```

Output includes:
- System status (FIPS enabled/disabled)
- OpenSSL version and FIPS provider status
- Kernel crypto module status
- Self-test results
- Algorithm enforcement validation
- Key size verification
- Compliance timestamp
- System configuration snapshot

### Report Location

Compliance reports saved to:
- `/var/log/shadowcypher/fips-compliance.log` (system-wide)
- `$HOME/.shadowcypher/fips-compliance.json` (user-specific)

### Audit Trail

Maintain immutable audit trail:
- Log all FIPS operations to syslog
- Tag entries with `FIPS_COMPLIANCE`
- Include timestamps and operation details
- Store in secure, tamper-evident location

## Emergency Fallback Mechanisms

### Graceful Degradation

If FIPS mode fails:
1. Detect self-test failure
2. Log error with severity and details
3. Prevent cryptographic operations
4. Alert administrators
5. Fall back to non-FIPS mode (requires explicit approval)

### Fallback Configuration

Fallback settings in `fips-config.json`:
```json
{
  "emergency_fallback": {
    "enable_on_fips_failure": false,
    "fallback_algorithms": ["AES-256-CBC", "RSA-2048"],
    "alert_destination": "security@shadowcypher.local",
    "log_location": "/var/log/shadowcypher/fips-fallback.log"
  }
}
```

### Recovery Procedure

1. Identify root cause of failure
2. Check OpenSSL version compatibility
3. Verify kernel module availability
4. Regenerate system crypto policies
5. Re-run compliance validation
6. Document recovery steps
7. Review with security team before re-enabling

## Operational Procedures

### Enable FIPS Mode

```bash
sudo ./fips-enable.sh --enable
```

Requires:
- Root privileges
- System reboot (kernel crypto policy changes)
- No active cryptographic operations
- Backup of current configuration

### Disable FIPS Mode

```bash
sudo ./fips-enable.sh --disable
```

Warning: Disables compliance guarantees. Requires:
- Executive authorization
- Audit trail documentation
- Compliance impact assessment
- Business justification

### Validate Compliance

```bash
./fips-enable.sh --validate
```

Checks:
- FIPS provider loaded
- Self-tests passing
- Algorithms restricted
- Key sizes enforced

### Monitor Status

```bash
./fips-enable.sh --status
```

Shows:
- FIPS mode status
- OpenSSL version
- Last self-test time
- Compliance report date
- Kernel module status

## Troubleshooting

### Common Issues

**"FIPS mode not available on this system"**
- Install openssl-fips package
- Verify kernel version (4.10+)
- Check /dev/urandom availability

**"Self-test failed"**
- Check system entropy (cat /proc/sys/kernel/random/entropy_avail)
- Verify openssl-fips version compatibility
- Review kernel messages (dmesg | grep fips)

**"Performance degradation"**
- Enable hardware acceleration (check for AES-NI: cat /proc/cpuinfo)
- Load kernel crypto modules
- Consider using connection pooling

**"Algorithm not supported in FIPS mode"**
- Review codebase for forbidden algorithms
- Update dependencies to FIPS-compliant versions
- Regenerate keys with approved algorithm

## References

- FIPS PUB 140-2: Security Requirements for Cryptographic Modules
- NIST SP 800-52 Rev. 2: Guidelines for TLS Implementations
- NIST SP 800-132: Password-Based Key Derivation
- NIST SP 800-90A: Recommendation for Random Number Generation
- OpenSSL FIPS Object Module documentation
- Linux kernel crypto API documentation

## Version History

- v1.0 (2026-01-15) - Initial FIPS 140-2 implementation guide

## Approval and Sign-Off

- Security Officer: ___________________ Date: _______
- Compliance Officer: ___________________ Date: _______
- System Administrator: ___________________ Date: _______
