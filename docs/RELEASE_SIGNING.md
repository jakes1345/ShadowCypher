# ShadowOS Release Signing & Verification

## GPG Key

- Key ID: `0x<YOUR_KEY_ID>` (example: 0xABCD1234)
- Fingerprint: published on shadowcypher.site/verify
- Public key: shadowcypher.site/downloads/shadowos_release.pub

## Signing Process

1. Build ISO: `./build.sh`
2. Generate hash: `sha256sum shadowos-*.iso > SHA256SUMS`
3. Sign hash: `gpg --detach-sign SHA256SUMS`
4. Sign ISO: `gpg --detach-sign shadowos-*.iso`
5. Upload all to downloads server

## Verification (User)

```bash
# Download public key
curl -fL https://shadowcypher.site/downloads/shadowos_release.pub | gpg --import

# Verify ISO
gpg --verify shadowos-*.iso.sig shadowos-*.iso

# Verify SHA256
gpg --verify SHA256SUMS.sig SHA256SUMS
sha256sum -c SHA256SUMS
```
