# ShadowOS Custom Update Channel — Research & Design

Goal: ship ShadowOS as a real downloadable distro where installed systems get
ongoing updates via `pacman -Syu`, both for upstream packages (kernel, browsers,
pentest tools, etc.) AND for our own customization (themes, scripts, configs).

---

## 1. What the major Arch-derived distros actually do

### EndeavourOS — *the closest model to what we want*
- One extra signed repo (`[endeavouros]`) on top of stock Arch + multilib
- No package mirroring; users hit Arch mirrors for kernel + everything else
- Their repo contains ~25 small packages:
  - `endeavouros-keyring` — distributes their signing key
  - `endeavouros-mirrorlist` — `Server = https://mirror.endeavouros.com/...`
  - `eos-bash-shared` — shared shell functions for their tools
  - `eos-hooks` — pacman hooks (e.g., warn before kernel upgrade)
  - `eos-quickstart` — first-boot wizard
  - `eos-update-notifier` — desktop notification when updates available
  - `welcome` — GUI welcome app
  - `reflector-simple` — friendly mirror picker
  - Various branding packages
- Releases are **rolling** — they push package updates whenever, never cut a "new version"
- ISOs are periodic snapshots, but the installed system never "knows" about them
- **This is the model that fits ShadowOS.**

### Manjaro — too heavy
- Maintains their own stable/testing/unstable branches
- Holds back Arch packages 1–2 weeks for QA
- Requires their own mirror network
- Massive maintenance burden — wrong for a small team

### Garuda — also a good reference
- Their repo + chaotic-aur enabled by default
- `garuda-update` wrapper around pacman
- Heavy custom theming + zen kernel by default
- Some valuable add-ons (their `garuda-system-maintenance` package)

### BlackArch — the layered-repo pattern
- Pure additive: their repo just adds security tools to stock Arch
- Already part of our stack
- Demonstrates the keyring + mirrorlist split that works

### CachyOS — kernel-focused
- Custom optimized kernels (x86_64-v3, v4)
- Not directly relevant unless we want a "shadow-linux" kernel later

---

## 2. The technical pieces we need

### Pacman repo format
A pacman repo is just a directory served over HTTP with:
- `<repo>.db` — gzipped tar of package metadata (one entry per pkg)
- `<repo>.db.tar.gz` — same, alternate ext
- `<repo>.files` — file listings (for `pacman -F`)
- `<repo>.db.sig` — detached signature of `.db`
- `*.pkg.tar.zst` + `*.pkg.tar.zst.sig` — the actual packages, signed

The `.db` is built by `repo-add --sign --key <KEYID> <repo>.db.tar.gz pkg.tar.zst`.

### Signing trust chain
1. We have a master OpenPGP key (the one already generated for apt: `D9F1D18F1313F083`)
2. CI signs every `.pkg.tar.zst` + the `<repo>.db` with this key
3. ShadowOS ships a `shadowos-keyring` package that:
   - Installs `/usr/share/pacman/keyrings/shadowos.gpg` (the public key)
   - Runs `pacman-key --add` + `pacman-key --lsign-key` in its postinst
4. Users adding the repo to existing Arch first install `shadowos-keyring` via a one-liner from our website

### pacman.conf entry
```ini
[shadowos]
SigLevel = Required DatabaseOptional
Include = /etc/pacman.d/shadowos-mirrorlist
```

### Bootstrap on existing Arch (curl install one-liner)
```bash
curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash
```
which: imports the key, drops the mirrorlist, adds `[shadowos]` to pacman.conf,
then runs `pacman -Sy shadowos-meta`.

---

## 3. The package split

Based on EndeavourOS's pattern, our `[shadowos]` repo would contain:

| Package | Contents | Notes |
|---------|----------|-------|
| **shadowos-keyring** | `/usr/share/pacman/keyrings/shadowos.gpg` + postinst that imports + lsigns | Foundation — must install first |
| **shadowos-mirrorlist** | `/etc/pacman.d/shadowos-mirrorlist` | Single mirror v1; multi-mirror v2 |
| **shadowos-base** | `/etc/sysctl.d/99-shadowos.conf`, `/etc/security/faillock.conf`, `/etc/shadowos/modes/*`, `/etc/polkit-1/rules.d/49-shadowos.rules`, polkit actions | Core distro identity |
| **shadowos-branding** | All 23 wallpapers + login bgs, Plymouth theme, GRUB theme, SDDM theme | Visual identity, ~13MB |
| **shadowos-tools** | `/usr/local/bin/shadow-*`, `shadowos-firstboot`, `shadowos-install`, `shadowos-mac-randomize`, systemd units | Custom CLI + services |
| **shadowos-hyprland-config** | `/etc/skel/.config/hypr/*`, waybar, mako, foot, wofi, starship, zsh | Default DE — backup= flagged so user customizations survive |
| **shadowos-firefox-config** | `/etc/skel/.mozilla/firefox/shadow.default/user.js` | Privacy-hardened FF defaults |
| **shadowos-fastfetch** | `/etc/fastfetch/shadowos.jsonc` | Login banner |
| **shadowos-meta** | Empty pkg with `depends=()` listing all the above + curated upstream (steam, lutris, mangohud, distrobox, …) | One-command install |
| **shadowcypher** | The GTK app from `shadowcypher/` | Versioned with the app |
| **shadowcypher-agent** | The agent service | Versioned with the app |

A user installing on existing Arch: `pacman -S shadowos-meta` → everything cascades.

The ISO build becomes much thinner: `airootfs/` only contains things that
*can't* be packaged (the customize_airootfs hook itself, basically). Everything
else is `pacman -S shadowos-meta` during mkarchiso.

---

## 4. Key decisions before we build

| # | Decision | Recommendation | Why |
|---|----------|---------------|-----|
| 1 | URL: `shadowcypher.site/arch` vs `arch.shadowcypher.site` | **/arch** | Matches apt setup; no extra DNS needed |
| 2 | Channels: rolling only vs stable/edge | **Rolling only v1** | Lower maintenance; EndeavourOS model; add channels in v2 if needed |
| 3 | Reuse apt GPG key or generate new pacman-only key | **Reuse** | Same key works for both; one secret to protect |
| 4 | Custom kernel (linux-shadowos) | **No** | Use Arch's `linux-hardened`; ship custom kernel only if real value (privacy patches?) |
| 5 | ISO bootstrap of our own repo | **Pre-installed** | mkarchiso build container imports our keyring + mirrorlist before package install |
| 6 | Update frequency policy | **As-needed** | Push when fixing/adding; auto-rebuild on git push via CI |
| 7 | Version scheme | **`<semver>-<release>`, bump release on content-only changes** | Standard Arch convention |
| 8 | Pacman hooks: warn on kernel upgrade, regenerate Plymouth on theme change | **Yes** | Real distros do this — adds polish |
| 9 | `shadow-update` CLI wraps `pacman -Syu` with progress bar + post-update tips | **Yes** | Already partly exists (`/usr/local/bin/shadow-update`) — move into `shadowos-tools` |
| 10 | Mirroring strategy | **Single mirror v1** | Hosted on GitHub Pages or Cloudflare R2; geographic mirrors later if needed |

---

## 5. What this changes about the current ISO build

**Before (today):**
- `airootfs/` is 180MB of stuff that gets copied into the live ISO
- Updates require rebuilding the ISO and asking users to reinstall

**After:**
- `airootfs/` is ~5MB — just `customize_airootfs.sh` and a stub
- mkarchiso runs `pacman -S shadowos-meta` during build → pulls everything from our repo
- Installed users `pacman -Syu` → atomic updates of all our customization

This is a one-way transition: once we ship as packages, we never go back to baking things into airootfs.

---

## 6. Infrastructure: where does the repo live?

**Option A: GitHub Pages (same as apt)** ✓ recommended for v1
- Pros: free, already set up, simple
- Cons: file size limit ~100MB/file (a non-issue for our packages)

**Option B: Cloudflare R2 + Workers**
- Pros: scalable, fast, no file size limits
- Cons: not free at scale, more setup

**Option C: Self-hosted**
- Pros: full control
- Cons: hosting cost + maintenance

v1 = GitHub Pages at `https://shadowcypher.site/arch/$repo/$arch/`.

---

## 7. CI build pipeline

`.github/workflows/publish-arch.yml`:
1. Triggers on push to main where `packaging/arch/**` or `shadowcypher/**` or branding changes
2. Runs in `archlinux:latest` container
3. For each PKGBUILD in `packaging/arch/*/`:
   - `makepkg --sign --key D9F1D18F1313F083 --noconfirm`
4. `repo-add --sign --key D9F1D18F1313F083 shadowos.db.tar.gz *.pkg.tar.zst`
5. Commit `arch/x86_64/*.pkg.tar.zst` + `.sig` + `shadowos.db*` to git
6. Push → GitHub Pages serves them

CI takes ~2-5 min per push (we don't rebuild what hasn't changed; smart caching).

---

## 8. Risk analysis

| Risk | Impact | Mitigation |
|------|--------|-----------|
| CI signing key compromise | All users get malicious packages | GitHub 2FA, restrict secret access, audit log alerts |
| Bad release breaks users | Stuck systems | `backup=()` in PKGBUILDs preserves user configs; rollback via `downgrade` |
| GitHub Pages outage | Updates unavailable temporarily | Users keep working; cache for offline; add mirrors later |
| Mismatch between ISO and repo | New install bricked | CI gates: must publish repo before publishing ISO |
| User adds repo without keyring first | Repo blocked by SigLevel=Required | Install one-liner handles ordering |
| Conflict with Arch upstream renames | `pacman -Syu` fails | Pin versions only when essential; otherwise let it ride |

---

## 9. What I need from you to start building

Looking at the table in Section 4, I'm recommending all the defaults shown.
Two questions where your call matters most:

**Q1: Custom kernel — yes or no?**
A `linux-shadowos` kernel with extra hardening (lockdown=confidentiality,
LSM=landlock,lockdown,yama,apparmor, KASLR forced, etc.) would be a distinctive
feature but adds ~30 min to every build and we need to track upstream linux
releases. Default: stay with `linux-hardened`. Override if you want the prestige.

**Q2: Custom-kernel question aside, anything else you want bundled?**
- Auto-update notification widget for waybar? (yes/no)
- `shadow-update` as the canonical updater that wraps pacman -Syu? (yes/no)
- ShadowCypher app published as `shadowcypher` package (versioned and updateable like everything else)? (recommend yes)

Once you answer those two, I'll write all the PKGBUILDs + CI workflow + bootstrap script. Estimated ~3 hours of focused work for the full v1.
