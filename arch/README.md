# ShadowOS pacman repository

Signed Arch Linux package repository for ShadowOS.

## Quick install (existing Arch)

```bash
curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash
```

Then:
```bash
sudo pacman -S shadowos-meta     # full ShadowOS experience
# or pick individual packages:
sudo pacman -S shadowcypher      # just the security GTK app
sudo pacman -S shadowos-tools    # just the shadow-* CLI suite
sudo pacman -S shadowos-branding # wallpapers + Plymouth + GRUB + SDDM themes
```

## Manual setup

```bash
# 1. Import key
curl -fsSL https://shadowcypher.site/arch/shadowos.gpg | sudo pacman-key --add -
sudo pacman-key --lsign-key 3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083

# 2. Add to /etc/pacman.conf
sudo tee -a /etc/pacman.conf <<'EOF'

[shadowos]
SigLevel = Required DatabaseOptional
Server = https://shadowcypher.site/arch/$repo/$arch
EOF

# 3. Sync
sudo pacman -Sy
```

## Packages

| Package | Purpose |
|---------|---------|
| `shadowos-keyring` | Distributes the repo signing key |
| `shadowos-mirrorlist` | Server URL(s) for the repo |
| `shadowos-base` | sysctl hardening, faillock, polkit rules, mode scripts |
| `shadowos-branding` | 20 wallpapers + Plymouth + GRUB + SDDM themes |
| `shadowos-tools` | shadow-mode, shadow-update, shadow-help-me, leak-test, diag |
| `shadowos-hyprland-config` | Default Hyprland + Waybar + Mako + Foot + Wofi + zsh dotfiles |
| `shadowos-firefox-config` | Privacy-hardened user.js (arkenfox-derived) |
| `shadowos-fastfetch` | Terminal banner with ShadowOS ASCII logo |
| `shadowos-meta` | Pulls all of the above + curated upstream defaults |
| `shadowcypher` | The GTK security suite app |
| `shadowcypher-agent` | Guardian endpoint agent |

## Signing key

- Fingerprint: `3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083`
- UID: `ShadowCypher Packages <admin@shadowcypher.site>`
- Same OpenPGP key that signs the `apt` repo.

## Trust

Packages are signed at build time by GitHub Actions using a key stored
in the `APT_SIGNING_KEY` GitHub Secret. The build pipeline lives at
`.github/workflows/publish-arch.yml` in the source repo.
