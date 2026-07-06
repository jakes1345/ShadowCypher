# ShadowOS Downloads

## Latest Release: ShadowOS Enterprise 3.0.0

**Release Date:** 2026-07-15  
**ISO Size:** ~3.2 GB  
**Integrity:** SHA256 verified, GPG signed

### Download

| Format | Size | Download | Signature |
|--------|------|----------|-----------|
| ISO | 3.2 GB | [shadowos-3.0.0.iso](https://dl.shadowcypher.site/shadowos-3.0.0.iso) | [.sig](https://dl.shadowcypher.site/shadowos-3.0.0.iso.sig) |
| Compressed | 1.8 GB | [shadowos-3.0.0.iso.tar.gz](https://dl.shadowcypher.site/shadowos-3.0.0.iso.tar.gz) | [.sig](https://dl.shadowcypher.site/shadowos-3.0.0.iso.tar.gz.sig) |

### Verify Download

**One-click verification:**
```bash
curl -fL https://shadowcypher.site/verify-download.sh | bash shadowos-3.0.0.iso
```

**Manual verification:**
```bash
# Download public key
curl -fL https://shadowcypher.site/shadowos_release.pub | gpg --import

# Verify signature
gpg --verify shadowos-3.0.0.iso.sig shadowos-3.0.0.iso

# Expected output:
# gpg: Good signature from "ShadowCypher Release <release@shadowcypher.site>"
```

### Release Notes

- Guardian security platform integrated and running by default
- CIS Arch Linux benchmark compliance (level 1 & 2)
- Kernel hardening via linux-hardened
- LUKS disk encryption support
- Secure Boot compatible
- 4 security modes: normal, pentest, privacy, ghost
- 50+ pre-installed security tools

### Previous Releases

- [ShadowOS 2.2.0](https://dl.shadowcypher.site/shadowos-2.2.0.iso) - 2026-06-15
- [ShadowOS 2.1.0](https://dl.shadowcypher.site/shadowos-2.1.0.iso) - 2026-05-15

---

## Supported Hardware

See [hardware-compatibility.md](hardware-compatibility.md) for certified devices.
