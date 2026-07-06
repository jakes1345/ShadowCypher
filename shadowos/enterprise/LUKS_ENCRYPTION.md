# LUKS Disk Encryption for ShadowCypher

## Overview

LUKS (Linux Unified Key Setup) provides full-disk encryption on Linux systems, protecting sensitive data at rest using industry-standard cryptographic algorithms. ShadowCypher integrates LUKS encryption as a core enterprise security feature for the Guardian vault and sensitive system operations.

## Architecture

### Encryption Model

ShadowCypher uses LUKS2 format with the following encryption architecture:

- **Cipher Algorithm**: AES-256 in XTS mode (AES-XTS-PLAIN64)
- **Key Size**: 512 bits (256-bit key + 256-bit tweak key)
- **Key Derivation Function (KDF)**: PBKDF2 with SHA-256
- **Iteration Time**: 2000 milliseconds (tuned for security vs. performance)
- **Sector Size**: 512 bytes (standard)

### Integration Points

1. **Guardian Vault**: LUKS encrypted volumes store vault master keys and encrypted credentials
2. **System Boot**: Optional encrypted `/` and `/home` partitions
3. **Data Partitions**: User data, audit logs, threat feeds
4. **Backup Storage**: Recovery keys stored in secure offline locations

## Security Benefits

### Data Protection at Rest

- **Full-disk encryption**: All data becomes inaccessible without proper decryption keys
- **Tamper detection**: Any unauthorized modification invalidates the encryption header
- **Key stretching**: PBKDF2 iteration time makes brute-force attacks computationally expensive
- **Sector-level encryption**: Individual 512-byte sectors encrypted independently

### Threat Model Protection

1. **Stolen/Physical Device**
   - Without correct passphrase, attacker cannot read any data
   - Encryption header integrity prevents key extraction attacks

2. **Cold Boot Attacks**
   - Hibernation with encrypted swap prevents memory dumps
   - Master key cleared from memory on shutdown

3. **Side-Channel Attacks**
   - Constant-time operations in cryptsetup/kernel
   - XTS mode prevents plaintext recovery from ciphertext patterns

4. **Passphrase Compromise**
   - Key slots allow multiple passphrases with independent key material
   - Compromised slot can be revoked without re-encrypting entire volume

## Implementation

### Prerequisites

```bash
# Required packages
cryptsetup >= 2.3.0
lvm2 >= 2.03
util-linux >= 2.35
```

### Encryption Setup Process

1. **Device Preparation**
   - Identify target device or partition
   - Backup existing data
   - Verify device is not in use

2. **LUKS2 Format**
   ```bash
   cryptsetup luksFormat --type luks2 \
     --cipher aes-xts-plain64 \
     --key-size 512 \
     --iter-time 2000 \
     /dev/sdXn
   ```

3. **Volume Opening**
   ```bash
   cryptsetup luksOpen /dev/sdXn guardian-vault
   ```

4. **Filesystem Creation**
   ```bash
   mkfs.ext4 /dev/mapper/guardian-vault
   ```

5. **Persistent Mounting**
   - Add entry to `/etc/crypttab` for automatic decryption
   - Mount via `/etc/fstab`

### Key Management

**Master Key Storage**
- 512-bit random master key generated during LUKS format
- Stored encrypted in LUKS header (accessible only with passphrase)

**Key Slots**
- LUKS2 supports up to 32 key slots
- Each slot contains independently encrypted copy of master key
- Allows multiple users/recovery methods

**Recovery Procedures**
- Recovery key backup created during setup
- Stored offline in secure location
- Used to unlock volume if passphrase forgotten

## Guardian Vault Integration

### Vault Structure

```
/mnt/guardian-vault/
├── master-keys/           # Encrypted master key material
├── credentials/           # User credentials (double-encrypted)
├── audit-logs/           # Access and modification logs
└── threat-feeds/         # Encrypted threat intelligence
```

### Access Flow

1. User provides passphrase
2. LUKS decryption unlocks volume at `/dev/mapper/guardian-vault`
3. Volume mounted to `/mnt/guardian-vault`
4. Guardian daemon loads master keys
5. User requests access to credential
6. Guardian decrypts with master key (separate from LUKS key)
7. Data returned only to authenticated session

### Double-Encryption Security

- Layer 1: LUKS encryption (disk/volume level)
- Layer 2: Guardian encryption (data level)
- Compromise of either key does not expose data
- Provides defense in depth against key extraction

## Recovery Procedures

### Emergency Unlock (Lost Passphrase)

1. Boot from recovery media
2. Verify recovery key authenticity (offline)
3. Add recovery key as new LUKS slot:
   ```bash
   cryptsetup luksAddKey /dev/sdXn --key-file recovery.key
   ```
4. Unlock with recovery key
5. Change passphrase to new value

### Emergency Wipe

If volume is captured and cannot be securely unlocked:

```bash
# Overwrite LUKS header (destroys all key material)
dd if=/dev/urandom of=/dev/sdXn bs=4M count=1
```

Data is now cryptographically destroyed (no key exists to decrypt).

### Backup and Restoration

**Header Backup**
```bash
cryptsetup luksHeaderBackup /dev/sdXn --header-backup-file header.img
```

**Header Restore**
```bash
cryptsetup luksHeaderRestore /dev/sdXn --header-backup-file header.img
```

Keep encrypted backups in multiple locations for disaster recovery.

## Performance Considerations

- **CPU Impact**: 5-15% overhead for typical workloads (AES-NI accelerated)
- **Memory**: ~100 MB per open volume
- **Throughput**: 500+ MB/s (modern SSD) with AES-NI

## Compliance

- **FIPS 140-2**: AES-XTS-PLAIN64 approved algorithm
- **NIST**: SP 800-38E compliant
- **LUKS Specification**: Conforms to LUKS2 reference implementation

## Monitoring

### Log Encryption Events

Monitor kernel logs for encryption-related events:

```bash
journalctl -u dm-crypt.service
dmesg | grep -i crypt
```

### Volume Status

```bash
cryptsetup status /dev/mapper/guardian-vault
```

## Troubleshooting

### Cannot Unlock Volume

1. Verify passphrase
2. Check device availability
3. Verify LUKS header integrity:
   ```bash
   cryptsetup luksDump /dev/sdXn
   ```

### Mount Failures

1. Check `/etc/crypttab` syntax
2. Verify `/etc/fstab` mount point exists
3. Check filesystem corruption:
   ```bash
   fsck.ext4 /dev/mapper/guardian-vault
   ```

### Performance Degradation

1. Check CPU usage during encryption operations
2. Verify AES-NI support: `grep aes /proc/cpuinfo`
3. Monitor I/O wait: `iostat -x 1`

## Future Enhancements

- TPM 2.0 integration for automatic unlock
- Hardware security module (HSM) support
- Multi-device RAID encryption
- Incremental encryption of existing volumes
