# ShadowOS

An Arch-based live ISO built with archiso. It boots into Hyprland with the ShadowCypher desktop app installed, and it can be installed to disk with Calamares. The goal is a small, privacy-focused daily driver with a curated set of network-monitoring and hardening tools. Anything else can be installed from the repos it has enabled, which include BlackArch and Chaotic-AUR.

**Status: in development.** ShadowOS isn't ready for daily use yet. Expect things here to change as it comes together.

## What's in the image

The full list is in `profile/packages.x86_64` (about 160 packages).

| Area | What ships |
|---|---|
| Kernel | `linux-hardened` (default boot entry) and `linux` (fallback entry), sysctl hardening in `etc/sysctl.d/99-shadowos.conf` |
| Boot | GRUB for UEFI and syslinux for BIOS, both themed, with a Plymouth splash |
| Desktop | Hyprland, SDDM, Waybar, Wofi, Mako, Hyprlock, Hypridle, Hyprpaper |
| Terminal and shell | Ghostty and Foot, Zsh with Starship |
| Privacy and security | nftables (inbound dropped by default), AppArmor, Tor and torsocks, dnscrypt-proxy, macchanger, firejail, USBGuard, fail2ban, rkhunter, Lynis, KeePassXC, VeraCrypt |
| Network tools | nmap, Wireshark, tcpdump, OpenBSD netcat, proxychains-ng, WireGuard, OpenVPN |
| ShadowCypher | `/usr/bin/shadowcypher`, its daemon and `shadowcypher-runtime`, plus the Ghost mode root helper, built from `shadowcypher-qt/` during the ISO build |
| Dev | git, neovim, tmux, ripgrep, fd, fzf, jq, base-devel |
| Other | Flatpak with Flathub added, PipeWire, Bluetooth, zram |
| Installer | Calamares, started with `shadowos-install` |

A few things the configs expect aren't in the package list yet:

- LibreWolf is the default browser in the Hyprland config and `mimeapps.list`, but no browser is installed.
- `shadowos-ai-setup` downloads three models (deepseek-r1:8b, qwen2.5-coder:7b and mistral:7b, about 14 GB), but it needs Ollama, which isn't installed.
- The Qt6 installer in `installer/` (`shadowos-installer`) drives archinstall, which isn't installed either.

## Layout

```
shadowos/
├── profile/                              archiso profile
│   ├── packages.x86_64                   package list
│   ├── pacman.conf                       core, extra, multilib, blackarch, chaotic-aur
│   ├── profiledef.sh                     ISO name, boot modes, file permissions
│   ├── airootfs/                         copied into the live root filesystem
│   │   ├── etc/skel/.config/             default dotfiles (hypr, waybar, wofi, mako, foot, ghostty, ...)
│   │   ├── etc/shadowos/modes/           apply/revert scripts for each mode
│   │   ├── etc/sysctl.d/99-shadowos.conf kernel hardening
│   │   ├── etc/systemd/system/           MAC randomizer, first boot, VPN kill-switch units
│   │   ├── usr/local/bin/                shadow-mode, shadow-update, shadow-help-me, shadowos-* scripts
│   │   ├── usr/share/backgrounds/        12 wallpapers in 1080p and 4K, 3 login variants
│   │   ├── usr/share/plymouth/themes/    boot splash
│   │   ├── usr/share/sddm/themes/        login screen
│   │   ├── usr/share/grub/themes/        boot menu theme
│   │   └── root/customize_airootfs.sh    runs inside the image during the build
│   ├── grub/grub.cfg                     live GRUB menu
│   └── syslinux/                         BIOS boot
├── installer/                            Qt6 installer (archinstall front end)
├── branding/                             wallpaper sources and desktop mock-ups
├── build.sh                              native build, wraps mkarchiso
├── build-docker.sh                       same build inside an Arch container
├── Dockerfile                            archlinux:latest with archiso
├── qemu-test.sh                          boots the newest ISO in QEMU
└── flash-usb.sh                          writes the ISO to a USB stick
```

## Build

On an Arch host:

```bash
sudo pacman -S archiso cmake qt6-base qt6-websockets
cd shadowos
sudo ./build.sh
```

`build.sh` must run as root. It builds the desktop app and the installer with CMake, installs them into `airootfs`, then runs `mkarchiso`. It stops if the desktop app fails to build, so you never get an image without it. The ISO lands in `out/` as `shadowos-<version>-<date>-x86_64.iso`.

On any other host with Docker:

```bash
cd shadowos
./build-docker.sh
```

## Test

```bash
bash qemu-test.sh
```

This boots the newest ISO in `out/` with KVM, 4 GB of RAM, 4 CPUs and UEFI (OVMF), and creates a 32 GB `test-disk.qcow2` the first time so you can try an install.

## Write to USB

```bash
./flash-usb.sh out/shadowos-*.iso
```

The script lists removable drives, asks which one to use and refuses non-removable disks. If there's a `.sha256` file next to the ISO it checks it first, and after writing it reads back the first 1 GB to verify.

## Modes

`shadow-mode <name>` runs `/etc/shadowos/modes/<name>/apply.sh` after reverting the previous mode. `Super+M` opens a Wofi picker, `Super+Shift+M` goes back to `normal`, and `Super+Shift+T` toggles Tor on its own.

| Mode | What it does |
|---|---|
| `normal` | Stops Tor, reloads the base nftables rules (inbound dropped except rate-limited SSH) and restarts dnscrypt-proxy |
| `privacy` | Starts Tor and dnscrypt-proxy, randomizes MAC addresses, sends all TCP and DNS through Tor's transparent proxy, drops other outbound traffic, and wraps LibreWolf, Firefox and Chromium in firejail |
| `ghost` | Everything in `privacy`, plus USBGuard blocking new USB devices, AppArmor in enforce mode, a tmpfs home for the `shadow` user, Bluetooth and the webcam driver off, a random hostname, and a RAM wipe on shutdown |
| `dev` | `normal` networking, performance CPU governor, starts Docker and the Podman socket if installed, opens ports 3000, 8080, 8443 and 9000, and 5432 and 6379 on loopback only |
| `gaming` | Performance CPU governor and Feral GameMode if installed |

`shadow-mode status` shows the current mode, Tor, dnscrypt-proxy, the nftables tables and MAC addresses. There is also a `pentest` script in `etc/shadowos/modes/`, but `shadow-mode` doesn't accept it as a mode yet.

## Live session login

The live user is `shadow`. Its password is generated randomly when the image is built, saved in `/etc/shadowos/live-password` and shown in the login message. The root account is locked; use `sudo`. SSH is off by default and only accepts keys when you turn it on.

## Themes and wallpapers

The wallpapers and the Plymouth, GRUB and SDDM themes are committed as images under `branding/` and `profile/airootfs/usr/share/`. The scripts that used to generate them were removed with the rest of the project's Python, so edit the images directly.
