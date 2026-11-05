# Drivers

This folder is empty apart from this README. Driver installation is done by `../install-drivers.sh`, which installs packages with `pacman` rather than from files here. The ISO build doesn't run it; it's meant for an installed system.

## Usage

Run it as root from the `shadowos` folder, with one category:

```bash
sudo ./install-drivers.sh nvidia      # or amd, intel, wireless, storage, all
```

Each category checks for matching hardware with `lspci` (except `wireless` and `storage`, which always run), syncs the package database and installs:

| Category | Packages |
|---|---|
| `nvidia` | `nvidia`, `nvidia-utils`, `lib32-nvidia-utils`, then `linux-headers`. Falls back to `xf86-video-nouveau` if that install fails |
| `amd` | `xf86-video-amdgpu`, `mesa`, `lib32-mesa`, `vulkan-radeon`, `lib32-vulkan-radeon`. Falls back to `xf86-video-ati` |
| `intel` | `xf86-video-intel`, `mesa`, `lib32-mesa`, `vulkan-intel`, `lib32-vulkan-intel`, `intel-ucode` |
| `wireless` | `wireless_tools`, `wpa_supplicant`, `dialog`, Intel and Atheros firmware, `rtl88xxau-airmon-git`, `broadcom-wl` |
| `storage` | `nvme-cli`, `hdparm`, `sdparm`, `mdadm`, `linux-firmware` |

Output and errors go to `/var/log/shadowos-drivers.log`.

## Known issues

- The Intel check never matches (`lspci | grep -q Intel | grep -q VGA` gives the second `grep` no input), so `intel` always skips.
- The `nvidia` package only ships modules for the stock `linux` kernel, and the script installs `linux-headers`. When booted into `linux-hardened` you need the DKMS variant of the driver and `linux-hardened-headers`.
- `xf86-video-*` packages are X11 drivers. Hyprland runs on Wayland and only needs Mesa or the NVIDIA driver.
- Some packages, such as `rtl88xxau-airmon-git`, may only be available from AUR or the extra repos ShadowOS enables. Failures are logged as warnings and the script carries on.
- Nothing is written to modprobe or Xorg config.
