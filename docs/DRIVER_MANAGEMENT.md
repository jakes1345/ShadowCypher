# ShadowOS Driver Management Guide

Comprehensive guide for managing GPU, wireless, and storage drivers in ShadowOS.

## Table of Contents

- [Quick Start](#quick-start)
- [Supported Hardware](#supported-hardware)
- [Installation Commands](#installation-commands)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [Related Resources](#related-resources)

## Quick Start

### Install All Drivers
```bash
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh all
```

### Install Specific Category
```bash
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh nvidia
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh amd
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh intel
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh wireless
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh storage
```

### View Installation Log
```bash
sudo tail -f /var/log/shadowos-drivers.log
```

## Supported Hardware

### NVIDIA GPUs

| Architecture | Models | Driver | Status |
|---|---|---|---|
| Kepler (2013) | GTX 750 Ti, GTX 960 | nouveau | Legacy |
| Maxwell (2014) | GTX 750, GTX 970, GTX 980 | nvidia, nouveau | Supported |
| Pascal (2016) | GTX 1050, GTX 1080, GTX 1080 Ti | nvidia, nouveau | ✅ Fully Supported |
| Volta (2017) | Titan V, Titan Xp | nvidia | Enterprise |
| Turing (2018) | RTX 2060, RTX 2070, RTX 2080 Ti | nvidia | ✅ Fully Supported |
| Ampere (2020) | RTX 3060, RTX 3080, RTX 3090 | nvidia | ✅ Fully Supported |
| Ada (2022) | RTX 4060, RTX 4070, RTX 4090 | nvidia | ✅ Fully Supported |
| Blackwell (2024) | RTX 5080, RTX 5090 | nvidia | ✅ Fully Supported |
| Quadro Series | Quadro RTX 4000, RTX 6000 | nvidia | ✅ Enterprise |

**Notes:**
- Proprietary `nvidia` driver requires Secure Boot disabled or signed module
- Fallback: `xf86-video-nouveau` (open-source, lower performance)
- 32-bit library support: `lib32-nvidia-utils` (gaming, Proton)

### AMD GPUs

| Architecture | Models | Driver | Status |
|---|---|---|---|
| GCN 1 (2012) | R9 290X, Fury | xf86-video-ati | Legacy |
| Polaris (2016) | RX 480, RX 570, RX 580 | amdgpu | ✅ Supported |
| Vega (2017) | Vega 56, Vega 64, Vega 64 Liquid | amdgpu | ✅ Fully Supported |
| RDNA (2020) | RX 6700, RX 6800, RX 6800 XT | amdgpu | ✅ Fully Supported |
| RDNA 2 (2020) | RX 6900 XT, RX 6950 XT | amdgpu | ✅ Fully Supported |
| RDNA 3 (2022) | RX 7600, RX 7700, RX 7900 | amdgpu | ✅ Fully Supported |
| RDNA 4 (2024) | RX 5070, RX 5090 | amdgpu | ✅ Fully Supported |
| Ryzen APU | 5700G, 7700, 9950X | amdgpu | ✅ Fully Supported |

**Notes:**
- Open-source `amdgpu` stack (MIT/Apache license)
- Vulkan: `vulkan-radeon` + `lib32-vulkan-radeon`
- No closed-source driver; better open-source support than NVIDIA

### Intel GPUs

| Generation | Models | Driver | Status |
|---|---|---|---|
| Gen 8 (Broadwell) | i7-5xxx, i5-5xxx | i915 | Supported |
| Gen 9 (Skylake) | i7-6xxx, i5-6xxx | i915 | ✅ Fully Supported |
| Gen 10 (Comet Lake) | i7-10xxx, i5-10xxx | i915 | ✅ Fully Supported |
| Gen 11 (Tiger Lake) | i7-11xxx, i5-11xxx | i915 | ✅ Fully Supported |
| Gen 12 (Alder Lake) | i7-12xxx, i5-12xxx | i915 | ✅ Fully Supported |
| Gen 13 (Raptor Lake) | i7-13xxx, i5-13xxx | i915 | ✅ Fully Supported |
| Arc A-Series | A750, A770 | i915 | ✅ Fully Supported |
| Data Center GPU | Flex 140 | i915 | Enterprise |

**Notes:**
- Integrated in CPU (iGPU) - no discrete card needed
- Kernel module: `i915` (built-in, automatic)
- Vulkan: `vulkan-intel` + `lib32-vulkan-intel`
- Wayland (Hyprland) recommended over X11

### Wireless Adapters

| Chipset | Driver | Firmware | Status |
|---|---|---|---|
| Intel AX200 | iwlwifi | intel-wireless-fw | ✅ Fully Supported |
| Intel AX201 | iwlwifi | intel-wireless-fw | ✅ Fully Supported |
| Realtek RTL8111 | r8169 | Included in kernel | ✅ Fully Supported |
| Realtek RTL8169 | r8169 | Included in kernel | ✅ Fully Supported |
| Qualcomm QCA9377 | ath10k | ath10k-firmware | ✅ Fully Supported |
| Qualcomm QCA9880 | ath10k | ath10k-firmware | ✅ Fully Supported |
| Atheros AR9271 | ath9k_htc | ath9k-htc-firmware | Supported |
| Broadcom BCM94352 | brcmfmac | broadcom-wl | ⚠️ AUR (sometimes unreliable) |
| MediaTek MT7921 | mt7921e | linux-firmware | ✅ Fully Supported |

**Notes:**
- Most Intel/Qualcomm/Realtek drivers included in kernel
- Firmware: `intel-wireless-fw`, `ath10k-firmware` via pacman
- Realtek newer chips: `rtl88xxau-airmon-git` (AUR - requires build)
- NetworkManager automatically manages wireless profiles

### Storage

| Interface | Chipset | Driver | Status |
|---|---|---|---|
| NVMe | Samsung 970/980 | nvme | ✅ Fully Supported |
| NVMe | Micron Crucial | nvme | ✅ Fully Supported |
| NVMe | WD Black SN850 | nvme | ✅ Fully Supported |
| AHCI | Any SATA | ata_generic | ✅ Fully Supported |
| RAID | MD (software) | md_mod | ✅ Fully Supported |
| Hardware RAID | LSI MegaRAID | megaraid_sas | Supported (may need firmware) |
| UAS | USB/SATA adapters | uas | ✅ Fully Supported |

**Notes:**
- NVMe drivers built into kernel (no installation needed)
- Utilities: `nvme-cli`, `hdparm`, `sdparm`
- Firmware: `linux-firmware` package
- RAID: `mdadm` for software RAID management

## Installation Commands

### NVIDIA Installation

```bash
# Install proprietary driver
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh nvidia

# Verify installation
nvidia-smi
nvidia-smi --query-gpu=driver_version --format=csv,noheader

# Check kernel module
lsmod | grep nvidia
```

**Manual fallback to Nouveau:**
```bash
sudo pacman -S xf86-video-nouveau
```

### AMD Installation

```bash
# Install AMDGPU drivers
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh amd

# Verify GPU detection
lspci | grep -i amd
glxinfo | grep AMD

# Check loaded modules
lsmod | grep amdgpu
```

**Manual fallback to ATI:**
```bash
sudo pacman -S xf86-video-ati
```

### Intel Installation

```bash
# Install Intel GPU drivers
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh intel

# Verify GPU detection
lspci | grep Intel | grep VGA
glxinfo | grep Intel

# Check kernel module
lsmod | grep i915
```

### Wireless Installation

```bash
# Install wireless drivers and firmware
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh wireless

# Verify wireless device
ip link show | grep -E 'wlan|wlp'

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Scan networks
nmcli device wifi list
```

### Storage Installation

```bash
# Install storage utilities
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh storage

# List NVMe drives
nvme list

# List block devices
lsblk

# Check SATA drives
hdparm -i /dev/sda
```

## Troubleshooting

### NVIDIA Issues

**Problem: nvidia-smi command not found**
```bash
# Verify driver installation
pacman -Q nvidia

# Check module load
dmesg | grep nvidia

# Try Nouveau fallback
sudo pacman -S xf86-video-nouveau
sudo systemctl reboot
```

**Problem: NVIDIA module fails to load**
```bash
# Check dmesg for errors
dmesg | grep -i nvidia

# Check Secure Boot (may block unsigned drivers)
sudo systemctl reboot --firmware-setup

# Try signing the kernel module
mokutil --test-key /etc/kernel/keys/nvidia.pem

# Or disable Secure Boot for testing
```

**Problem: CUDA not available**
```bash
# Install CUDA toolkit and runtime
sudo pacman -S cuda

# Verify CUDA installation
cuda-memtest
```

### AMD Issues

**Problem: GPU not detected by amdgpu driver**
```bash
# Verify hardware detection
lspci -vv | grep -A 10 AMD

# Check BIOS: enable PCIe (not limited to Gen 2)
# Reboot and check if GPU loads

# Check module loading
sudo modprobe amdgpu
dmesg | grep amdgpu

# Try ATI driver fallback
sudo pacman -S xf86-video-ati
```

**Problem: Poor OpenGL performance**
```bash
# Ensure mesa is installed
pacman -Q mesa lib32-mesa

# Enable hardware acceleration in X11
echo "Option \"DRI\" \"3\"" | sudo tee /etc/X11/xorg.conf.d/20-amd.conf

# Restart X/Wayland
```

### Intel Issues

**Problem: iGPU not detected in Wayland**
```bash
# Verify iGPU enabled in BIOS
# Reboot, check System Settings > Display

# Check kernel detection
dmesg | grep -i intel | grep -i graphics

# Force iGPU detection
echo "options i915 enable_guc=3" | sudo tee /etc/modprobe.d/i915.conf
sudo update-initramfs -u
```

**Problem: Wayland flickering on Intel GPU**
```bash
# Workaround: disable PSR (Panel Self Refresh)
echo "options i915 enable_psr=0" | sudo tee /etc/modprobe.d/i915-psr.conf
sudo update-initramfs -u
sudo systemctl reboot
```

### Wireless Issues

**Problem: No wireless networks detected**
```bash
# Check device status
ip link show

# Enable wireless device if DOWN
sudo ip link set wlan0 up

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Check firmware loaded
dmesg | grep -i firmware | grep -i wireless

# Check module loaded
lsmod | grep -E 'iwlwifi|ath10k|brcmfmac'
```

**Problem: Slow wireless speed**
```bash
# Check connection speed
iwconfig wlan0 | grep "Bit Rate"

# Check signal strength
iw wlan0 link | grep signal

# Try moving closer to router
# Check for interference on 2.4GHz (switch to 5GHz if available)
```

**Problem: Frequent disconnects**
```bash
# Check logs for errors
journalctl -u NetworkManager -f

# Disable power management
sudo iw wlan0 set power_save off

# Update firmware
sudo pacman -S intel-wireless-fw

# Restart wireless
sudo systemctl restart NetworkManager
```

### Storage Issues

**Problem: NVMe drive not detected**
```bash
# List devices
lsblk

# Check BIOS: NVMe support enabled

# Verify NVMe module loaded
lsmod | grep nvme

# Use nvme-cli to list drives
nvme list

# Force module reload
sudo modprobe -r nvme
sudo modprobe nvme
```

**Problem: Slow NVMe performance**
```bash
# Check drive firmware version
nvme id-ctrl /dev/nvme0 | grep firmware

# Check for link errors
nvme smart-log /dev/nvme0

# Verify max link speed
lspci -vv | grep "LnkSpd\|LnkWid"
```

**Problem: SATA drive not showing**
```bash
# Check BIOS: SATA mode (AHCI vs RAID)

# List devices
lsblk

# Check kernel module
lsmod | grep ata_

# Check dmesg
dmesg | grep -i sata
```

## Advanced Configuration

### Custom Driver Selection

To use a specific driver version or build from source:

```bash
# Build NVIDIA driver from source
git clone https://github.com/NVIDIA/open-gpu-kernel-modules.git
cd open-gpu-kernel-modules
make

# Or use AUR helpers
yay -S nvidia-open-dkms  # Open kernel module driver
```

### Modprobe Configuration

Create `/etc/modprobe.d/` configuration files to tweak driver behavior:

```bash
# NVIDIA: Disable GSP firmware (stability)
echo "options nvidia NVreg_EnableGpuFirmware=0" | sudo tee /etc/modprobe.d/nvidia.conf

# AMD: Enable power saving
echo "options amdgpu dc=1" | sudo tee /etc/modprobe.d/amdgpu.conf

# Intel: Enable PSR
echo "options i915 enable_psr=1" | sudo tee /etc/modprobe.d/i915-psr.conf
```

Apply changes:
```bash
sudo update-initramfs -u
sudo systemctl reboot
```

### Performance Tuning

```bash
# NVIDIA: Check clock speeds
nvidia-smi -q -d CLOCK

# AMD: Enable GPU clocks (amdgpu)
sudo cat /sys/class/drm/card0/device/power_dpm_force_performance_level

# Intel: CPU vs GPU performance balance
# (No direct control; managed by kernel driver)
```

### Verification Commands

```bash
# GPU/APU status
lspci -k | grep -A 2 VGA

# Driver loaded
lsmod | grep -E 'nvidia|amdgpu|i915'

# Wireless status
ip link show | grep -E 'wlan|wlp'

# Storage status
lsblk
nvme list

# OpenGL/Vulkan support
glxinfo | grep "OpenGL version"
vulkaninfo | grep "apiVersion"
```

## Installation Log

All driver installations are logged to `/var/log/shadowos-drivers.log`:

```bash
# View recent logs
tail -20 /var/log/shadowos-drivers.log

# Follow live logs
sudo tail -f /var/log/shadowos-drivers.log
```

## Related Documentation

- [shadowos/drivers/README.md](../shadowos/drivers/README.md) — Driver directory structure
- [ShadowOS README](../shadowos/README.md) — System overview
- [Enterprise Documentation](../docs/) — Enterprise features

## Support & Contributions

For driver-specific issues:
1. Check the troubleshooting section above
2. Review installation logs: `/var/log/shadowos-drivers.log`
3. File an issue: https://github.com/your-repo/issues
4. Consult vendor documentation for hardware-specific problems

## License

ShadowOS drivers include software under various licenses:
- **NVIDIA**: Proprietary + Nouveau (MIT)
- **AMD**: Open-source (MIT/Apache)
- **Intel**: Open-source (MIT)
- **Wireless**: GPL-2, BSD, proprietary firmware
- **Storage**: Open-source + proprietary firmware

See individual driver sources for full license details.
