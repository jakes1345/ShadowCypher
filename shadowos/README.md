# ShadowOS

Arch-based live/installable ISO. Enterprise security platform that's also a
practical daily driver — pentest, dev, and gaming, all in one.

## What's in the box

| Layer | What ships |
|-------|-----------|
| **Kernel** | linux-hardened + linux fallback, sysctl hardening |
| **Compositor** | Hyprland (Wayland), animations, blur, rounded corners |
| **DM / Bar / Launcher / Lock** | SDDM (custom theme) · Waybar · Wofi · Hyprlock |
| **Terminal / Shell** | Foot · Zsh + Starship |
| **Boot splash** | Plymouth — custom animated logo + 12-dot orbit spinner |
| **Boot menu** | GRUB — custom theme with teal accent |
| **Browser** | Firefox (arkenfox-hardened user.js) |
| **Dev** | VSCode, neovim, helix, lazygit, gh, docker, podman, kubectl, terraform, rustup, go, nodejs |
| **Pentest** | nmap, sqlmap, hydra, metasploit, aircrack-ng, bettercap, john, hashcat, wireshark, **rustscan, ffuf, feroxbuster, subfinder, httpx, nuclei, naabu, impacket, netexec, sshuttle, mitmproxy** |
| **Gaming** | Steam + steam-runtime, Heroic, Lutris, PrismLauncher (Minecraft), gamemode, MangoHUD, gamescope, wine-staging |
| **Cross-distro tools** | Distrobox (run Kali/Ubuntu/Debian as containers), Flatpak/Flathub |
| **Privacy** | Tor, dnscrypt-proxy, MAC randomizer (per-mode), AppArmor, ufw |
| **Modes** | `shadow-mode <normal/dev/pentest/privacy/ghost>` — hot-swap firewall, DNS, autostart |
| **AI** | ShadowCypher (GTK) pre-installed at /opt/shadowcypher; Ollama for local LLMs |
| **Installer** | archinstall (live → disk) + Calamares config |

## Layout

```
shadowos/
├── profile/                              archiso profile
│   ├── packages.x86_64                   ~250 packages
│   ├── pacman.conf                       core + extra + multilib + blackarch
│   ├── profiledef.sh                     ISO metadata, signing, modes
│   ├── airootfs/                         copied into live root filesystem
│   │   ├── etc/skel/.config/             default user dotfiles (hypr, waybar, ...)
│   │   ├── etc/shadowos/modes/           5 personality scripts
│   │   ├── etc/sysctl.d/99-shadowos.conf kernel hardening
│   │   ├── etc/systemd/system/           MAC randomize + firstboot units
│   │   ├── usr/local/bin/                shadow-mode, shadow-help-me, etc.
│   │   ├── usr/share/backgrounds/        20 wallpapers + 3 login variants
│   │   ├── usr/share/plymouth/themes/    custom animated boot splash
│   │   ├── usr/share/sddm/themes/        custom login screen
│   │   ├── usr/share/grub/themes/        custom boot menu
│   │   └── root/customize_airootfs.sh    runs during ISO build
│   ├── grub/grub.cfg                     live GRUB config
│   ├── grub/themes/shadowos/             live-boot theme assets
│   └── syslinux/                         BIOS fallback boot
├── branding/
│   ├── render_all.py                     generates 20 desktop + 3 login wallpapers
│   ├── render_plymouth.py                generates Plymouth theme assets
│   └── render_grub.py                    generates GRUB theme assets
├── build.sh                              wrapper around mkarchiso
├── build-docker.sh                       Arch-in-Docker build for non-Arch hosts
├── flash-usb.sh                          dd helper
├── Dockerfile                            archlinux:latest + archiso
└── README.md
```

## Build

### Native (Arch host)
```bash
sudo pacman -S archiso
cd shadowos
sudo ./build.sh
# Output: out/shadowos-<date>-x86_64.iso
```

### Docker (any host)
```bash
cd shadowos
./build-docker.sh
```

## Test

```bash
qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/shadowos-*.iso
```

## Flash to USB

```bash
sudo ./flash-usb.sh out/shadowos-*.iso /dev/sdX
```

## Modes

| Mode      | Tor | DNS         | Firewall   | Use case |
|-----------|-----|-------------|------------|----------|
| `normal`  | off | dnscrypt    | deny in    | Daily driver |
| `dev`     | off | dnscrypt    | docker open | Development |
| `pentest` | off | dnscrypt    | scan open  | Active engagement |
| `privacy` | on  | dnscrypt+Tor| Tor-only   | Travel / hostile networks |
| `ghost`   | on  | Tor-only    | drop all   | Maximum lockdown |

Switch with `shadow-mode <name>` or `SUPER+M` for the wofi picker.

## Default credentials (live ISO only)

- User: `shadow` / `shadow`
- Root: `shadow`
- These are reset by the installer; do not leave them on installed systems.

## Regenerating themes / wallpapers

```bash
cd shadowos/branding
python3 render_all.py        # 20 wallpapers + 3 login
python3 render_plymouth.py   # Plymouth boot animation assets
python3 render_grub.py       # GRUB theme background + select pixmaps
```

Requires Pillow; numpy makes it 10× faster.
