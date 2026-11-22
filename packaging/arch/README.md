# ShadowOS pacman repository

A signed pacman repository for installing ShadowOS packages on an existing Arch system. The packages are built from the PKGBUILDs in [`packaging/arch/`](../packaging/arch/) by the `publish-arch.yml` workflow, which commits the results to `x86_64/` here.

## Current state

Only three packages are published at the moment: `shadowos-keyring`, `shadowos-mirrorlist` and `shadowos-meta`, all version 1.0-1. `shadowos-meta` depends on the other packages listed below, which aren't in the repo yet, so `pacman -S shadowos-meta` fails until they are. The published `shadowos-meta` also still depends on `shadowcypher-agent`, which has no PKGBUILD.

## Setup

`install.sh` does the setup in one go. Read it first, then:

```bash
curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash
```

It imports the signing key, writes `/etc/pacman.d/shadowos-mirrorlist`, adds a `[shadowos]` section to `/etc/pacman.conf` and runs `pacman -Sy`. Pass `--meta` (`sudo bash -s -- --meta`) to install `shadowos-meta` as well.

By hand:

```bash
# 1. Import and locally sign the key
curl -fsSL https://shadowcypher.site/arch/shadowos.gpg | sudo pacman-key --add -
sudo pacman-key --lsign-key 3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083

# 2. Add the repo to /etc/pacman.conf
sudo tee -a /etc/pacman.conf <<'EOF'

[shadowos]
SigLevel = Required DatabaseOptional
Server = https://shadowcypher.site/arch/$repo/$arch
EOF

# 3. Sync
sudo pacman -Sy
```

## Packages

| Package | Contents | Published |
|---|---|---|
| `shadowos-keyring` | The repo signing key | yes |
| `shadowos-mirrorlist` | Server list for the repo | yes |
| `shadowos-meta` | Depends on all of the below plus upstream defaults | yes |
| `shadowos-base` | sysctl hardening, faillock, polkit rules, mode scripts, os-release | no |
| `shadowos-branding` | Wallpapers and the Plymouth, GRUB and SDDM themes | no |
| `shadowos-tools` | `shadow-mode`, `shadow-update`, `shadow-help-me`, `shadow-leak-test`, `shadowos-diag` and other scripts, plus the Calamares branding | no |
| `shadowos-hyprland-config` | Default Hyprland, Waybar, Mako, Foot, Wofi and Zsh config | no |
| `shadowos-firefox-config` | Hardened Firefox `user.js`, derived from arkenfox | no |
| `shadowos-fastfetch` | Fastfetch banner with the ShadowOS logo | no |
| `shadowcypher` | The Qt6 desktop app, its daemon and runtime | no |

`packaging/arch/` also has PKGBUILDs for `shadowbrowser` and `shadowos-shell`, which the workflow doesn't build.

## Signing key

- Fingerprint: `3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083`
- UID: `ShadowCypher Packages <admin@shadowcypher.site>`

Packages and the repo database are signed in GitHub Actions with a key stored in the `APT_SIGNING_KEY` repository secret. The workflow is `.github/workflows/publish-arch.yml`.
