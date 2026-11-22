# ShadowOS pacman repository

A signed pacman repository for installing ShadowOS packages on an existing Arch system. The packages are built from the PKGBUILDs in this directory by the `publish-arch.yml` workflow.

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

| Package | Contents |
|---|---|
| `shadowos-keyring` | The repo signing key |
| `shadowos-mirrorlist` | Server list for the repo |
| `shadowos-meta` | Depends on all of the below plus upstream defaults |
| `shadowos-base` | sysctl hardening, polkit rules, the mode scripts, os-release |
| `shadowos-branding` | Wallpapers and the Plymouth, GRUB and SDDM themes |
| `shadowos-tools` | `shadow-mode`, `shadow-update`, `shadow-help-me`, `shadow-leak-test`, `shadowos-diag` and other scripts, plus the Calamares branding |
| `shadowos-hyprland-config` | Default Hyprland, Waybar, Mako, Foot, Wofi and Zsh config for new users (`/etc/skel`) |
| `shadowos-firefox-config` | Hardened Firefox profile for new users, derived from arkenfox |
| `shadowos-fastfetch` | Fastfetch banner with the ShadowOS logo |
| `shadowcypher` | The Qt6 desktop app, its daemon and runtime |

The packages take their files from `shadowos/profile/airootfs` and `shadowcypher-qt/`, so they carry what the ISO carries. Three things the ISO has are left out on purpose, because they would break an existing system:

- `/etc/security/faillock.conf` belongs to `pam`, and pacman refuses a package that brings a file another package owns.
- The ISO's `sshd_config.d` files are written for the live session. As drop-ins they would override the admin's own `sshd_config`.
- `/etc/os-release` and `/etc/hostname` are installed as `.pacnew` files when the system already has its own.

This directory also has PKGBUILDs for `shadowbrowser` and `shadowos-shell`, which are not built or published.

## Building

On Arch, as a normal user who can `sudo pacman`:

```bash
packaging/arch/build-repo.sh /tmp/shadowos-repo
```

That builds all ten packages and the repository database, unsigned, into the directory you name. The script names every package that fails and writes nothing if one does. Before it writes the repository it has pacman resolve every package against `[shadowos]` plus the official repositories, and checks that no package ships a file another package owns. `SIGN_KEY=<fingerprint>` signs the result and has pacman verify it against the key in `shadowos-keyring/`.

A single package also builds on its own with `makepkg` in its directory.

## Publishing

`publish-arch.yml` runs the same script.

- On a pull request that touches the packages it builds them unsigned and publishes nothing.
- On `main` it signs them and uploads the packages and the database as the assets of the [`arch-repo`](https://github.com/jakes1345/ShadowCypher/releases/tag/arch-repo) release, replacing the previous set.

The repository is not kept in git: `main` is protected, and `shadowos-branding` is larger than GitHub's 100 MB file limit. `https://shadowcypher.site/arch/shadowos/x86_64/` is a redirect to the release assets (`www/_redirects`), and `install.sh` and `shadowos.gpg` are served from `www/arch/`.

Every package is at a fixed version (`pkgver`-`pkgrel` in its PKGBUILD). pacman only upgrades a package whose version went up, so a change to a package's contents reaches installed systems only when its `pkgrel` is raised in the same change.

## Signing key

- Fingerprint: `3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083`
- UID: `ShadowCypher Packages <admin@shadowcypher.site>`

Packages and the repo database are signed in GitHub Actions with a key stored in the `APT_SIGNING_KEY` repository secret.
