# Installing ShadowOS

ShadowOS ships as a bootable ISO that doubles as a **live system** (try it without installing) and an **installer** (Calamares) for a permanent install.

## Quick install

### 1. Download the ISO

```bash
curl -fLO https://shadowcypher.site/downloads/shadowos-latest.iso
curl -fLO https://shadowcypher.site/downloads/shadowos-latest.iso.sha256
sha256sum -c shadowos-latest.iso.sha256
```

Expected: `shadowos-latest.iso: OK`

### 2. Write to USB (8GB+ drive)

```bash
# Linux / macOS — use the bundled helper
git clone https://github.com/jakes1345/ShadowCypher
cd ShadowCypher/shadowos
./flash-usb.sh ~/Downloads/shadowos-latest.iso

# or use dd directly
sudo dd if=shadowos-latest.iso of=/dev/sdX bs=4M status=progress oflag=sync
```

On Windows, use **Rufus** or **balenaEtcher**. Pick "DD mode" if asked.

### 3. Boot from the USB

- Reboot
- Hit your BIOS/UEFI boot menu key (F12 / F11 / Esc / F2 — varies)
- Pick the USB drive
- ShadowOS loads to the GRUB menu — pick **ShadowOS (hardened)**

You're now in the **live system**. Default user `shadow` / password `shadow`.

### 4. Install to disk (optional)

Open the dock → click the **Install ShadowOS** icon (or run `shadowos-install` from a terminal). Calamares walks you through it with these install profiles:

| Profile | Installed size | What's included |
|---------|---------------|-----------------|
| **Minimal** | ~2 GB | Base + Hyprland + ShadowBrowser. Add anything else later via `pacman -S`. |
| **Security Pro** | ~5 GB | + nmap, metasploit, wireshark, rustscan, impacket, ffuf, the full pentest arsenal |
| **Everything** | ~10 GB | + Steam, Lutris, Heroic, VSCode, Docker, GIMP, Blender, Krita, full dev/creator/gaming stack |

## Update later

Once installed, `pacman -Syu` pulls updates from:
- **Arch core/extra/multilib** — kernel, drivers, base packages
- **BlackArch** — pentest tools
- **ShadowOS** — our branding, scripts, configs, ShadowCypher app

Or use the friendly wrapper:
```bash
shadow-update
```

It shows ShadowOS-specific updates separately, gracefully refuses to update over clearnet when you're in `privacy`/`ghost` mode, and prompts you to reboot if the kernel was upgraded.

## Add ShadowOS to an existing Arch install

You can also install ShadowOS *components* (branding, shell, modes, ShadowCypher app) on top of any existing Arch system — no reinstall needed:

```bash
curl -fsSL https://shadowcypher.site/arch/install.sh | sudo bash -s -- --meta
```

This adds the `[shadowos]` repo to pacman and installs `shadowos-meta` which pulls everything in.

## Default credentials

Live ISO ships with:
- User: `shadow` / `shadow`
- Root: `shadow`

These are reset during install — the installer makes you set a real password.

## Modes

Once installed, switch the OS's security posture instantly:

```bash
shadow-mode pentest    # firewall opens, raw sockets for nmap, no Tor
shadow-mode privacy    # all egress via Tor, MAC randomized, browsers in firejail
shadow-mode ghost      # Tor only, every other app blocked
shadow-mode dev        # docker daemon up, normal firewall
shadow-mode normal     # daily driver (default)
```

Or open the wofi picker: **Super + M**

## Hardware

- 64-bit x86 CPU (KVM/AMD-V helpful but not required)
- 4 GB RAM minimum, 8 GB recommended
- 10 GB disk minimum (more if Everything profile)
- UEFI or BIOS boot — both supported
- Most laptops and desktops work; bleeding-edge GPUs may need linux-firmware updates

## Troubleshooting

**ISO won't boot:** verify SHA256 again, try a different USB stick, try the "stock kernel" GRUB entry.

**No Wi-Fi after install:** run `nmtui` to connect. We ship `network-manager-applet` for tray-based connection management.

**Hyprland is black after login:** older Intel GPUs need `WLR_RENDERER=pixman`. Add to `~/.config/hypr/hyprland.conf`.

**Tor doesn't start in privacy mode:** run `sudo systemctl status tor` — usually a transient bridge issue. `shadow-mode normal && shadow-mode privacy` re-applies cleanly.

## Where to get help

- Docs: https://shadowcypher.site/docs.html
- Issues: https://github.com/jakes1345/ShadowCypher/issues
- Chat: ShadowCypher's built-in Community Chat (login with your shadowcypher.site API key)
