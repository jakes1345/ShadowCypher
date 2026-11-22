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

Run like that, every package comes out at release 1. To build what the workflow would publish, with the versions users would see, point the script at the published repository:

```bash
PUBLISHED_URL=https://shadowcypher.site/arch/shadowos/x86_64 packaging/arch/build-repo.sh /tmp/shadowos-repo
```

A single package also builds on its own with `makepkg` in its directory.

## Versions

pacman upgrades a package only when its version goes up, so the build sets the release number (`pkgrel`) itself. It compares each package it has just built with the published one:

- **Same contents:** the published file is kept. A rebuild differs only in its timestamps, and pacman expects a file it has already downloaded not to change.
- **Different contents:** the package is published one release higher (`1.0-2` becomes `1.0-3`), and `pacman -Syu` picks it up.

"Contents" is every installed file with its mode and owner, the install script, and the package's metadata, such as its dependencies. Build dates and the packager do not count.

So there is nothing to bump by hand. Change a file under `shadowos/profile/airootfs` or in `shadowcypher-qt/`, and the packages it ends up in get a new release when the change reaches `main`. The summary of a pull request's `Build packages` run shows which packages it changes.

- Leave `pkgrel` in the PKGBUILDs alone.
- Raise `pkgver` when a package deserves a new version number; its release starts again at 1. `pkgver` must never go down, and the build refuses if it does.

The release numbers live in the published repository, not in git. If the published database cannot be read, the build stops. Starting again at release 1 would hand users packages older than the ones they have.

## Publishing

`publish-arch.yml` runs the same script.

- On a pull request that touches the packages it builds them unsigned and publishes nothing.
- On `main` it signs them and publishes to the [`arch-repo`](https://github.com/jakes1345/ShadowCypher/releases/tag/arch-repo) release with `publish-release.sh`: the new package versions go up first, then the database, and then the versions they replace are removed. Packages that did not change are not touched.

The repository is not kept in git: `main` is protected, and `shadowos-branding` is larger than GitHub's 100 MB file limit. `https://shadowcypher.site/arch/shadowos/x86_64/` is a redirect to the release assets (`www/_redirects`), and `install.sh` and `shadowos.gpg` are served from `www/arch/`.

## Signing key

- Fingerprint: `3ACC49288AC4F3BCBE1CDE98D9F1D18F1313F083`
- UID: `ShadowCypher Packages <admin@shadowcypher.site>`

Packages and the repo database are signed in GitHub Actions with a key stored in the `APT_SIGNING_KEY` repository secret.
