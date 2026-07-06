# ShadowOS SSH Hardening

## Configuration

SSH is hardened with:
- Public key authentication only (no passwords)
- ED25519 keys enforced
- Strong ciphers (ChaCha20, AES-256-GCM)
- Rate limiting on failed attempts
- No root login permitted

## First Login

```bash
# Generate SSH key
chmod +x shadowos/ssh-key-gen.sh
./shadowos/ssh-key-gen.sh

# Copy to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@remote
```

## Remote Access

```bash
ssh shadow@shadowos-machine
```

## Allowed Users

Only user `shadow` can SSH to the system.

## Disabling SSH

```bash
sudo systemctl disable ssh
sudo systemctl stop ssh
```
