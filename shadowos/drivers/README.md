# ShadowOS Driver Package Management

Centralized driver management for ShadowOS, supporting NVIDIA, AMD, Intel, wireless, and storage controllers.

## Directory Structure

```
drivers/
├── nvidia/          NVIDIA GPU drivers (proprietary, open-source fallback)
├── amd/             AMD GPU drivers (AMDGPU stack)
├── intel/           Intel GPU drivers (iGPU, Arc)
├── wireless/        Wireless firmware (Intel, Realtek, Qualcomm, Broadcom)
└── storage/         NVMe, SATA, RAID controller firmware
```

## Quick Start

Install all drivers:
```bash
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh all
```

Install specific driver category:
```bash
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh nvidia
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh amd
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh intel
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh wireless
sudo /home/jack/ShadowCypher/shadowos/install-drivers.sh storage
```

## Supported Hardware

### NVIDIA
- GeForce GTX 900 series and newer (RTX 40/50 series supported)
- Quadro / RTX workstation GPUs
- Fallback: `xf86-video-nouveau` (open-source)

### AMD
- Radeon RX 6000, 7000 series
- RDNA, RDNA 2, RDNA 3 architectures
- Legacy: Polaris, Vega fallback

### Intel
- Integrated UHD Graphics (Gen 8+)
- Arc A770, A750 discrete GPUs
- Data Center GPU Flex

### Wireless
- Intel AX200/AX201 (Wi-Fi 6)
- Realtek RTL8169/RTL8111 (Ethernet)
- Qualcomm Atheros AR9xxx, QCA9xxx
- Broadcom BCM94352

### Storage
- NVMe: Samsung, Micron, WD, SK Hynix
- SATA: AHCI controllers
- RAID: MD software RAID, hardware controller firmware

## Driver Installation Details

Each driver category installs:
1. **Package dependencies** — Core libraries and tools
2. **Firmware** — Microcode and device firmware
3. **Configuration** — Modprobe rules, xorg.conf snippets (if needed)
4. **Verification** — Automatic device detection and status logging

### Installation Log
All installations are logged to `/var/log/shadowos-drivers.log`

## Troubleshooting

### NVIDIA
If proprietary driver fails to load:
1. Check BIOS: disable Secure Boot if driver is unsigned
2. Check kernel: `dmesg | grep nvidia` for module load errors
3. Fallback: installer auto-switches to `xf86-video-nouveau` if needed
4. Verify: `nvidia-smi` should show GPU info

### AMD
If AMDGPU doesn't detect GPU:
1. Verify: `lspci | grep -i amd`
2. Check BIOS: enable "PCIe Gen" (not limited to Gen 2)
3. Module check: `lsmod | grep amdgpu`
4. Fallback: `xf86-video-ati` (legacy driver)

### Intel
If iGPU is not detected:
1. Verify BIOS: enable iGPU (sometimes labeled "Integrated Graphics")
2. Check kernel: `dmesg | grep -i intel` for initialization
3. Verify: `lspci | grep Intel | grep VGA`
4. Wayland hint: Intel GPU works best with Wayland (Hyprland)

### Wireless
If network device not detected:
1. Verify: `ip link show` or `iwconfig`
2. Check firmware: `dmesg | grep -i firmware`
3. Module load: `modprobe -v <module-name>`
4. Restart networking: `sudo systemctl restart NetworkManager`

### Storage
If NVMe drive not detected:
1. Verify: `lsblk` or `nvme list`
2. Check BIOS: enable NVMe support (usually default)
3. Module: Ensure `nvme` module is loaded
4. Firmware: Some drives benefit from vendor firmware updates

## Adding Custom Drivers

To add a custom driver:
1. Create a subdirectory under `drivers/`
2. Place driver package or build script in the subdirectory
3. Update `install-drivers.sh` with a new case statement
4. Document in this README

Example structure:
```
drivers/custom/
├── README.md              Driver-specific docs
├── build.sh               Optional: build from source
└── firmware/              Firmware blobs (if any)
```

## License & Attribution

ShadowOS drivers include:
- **NVIDIA**: Proprietary (EULA) + Nouveau (MIT)
- **AMD**: Open-source AMDGPU (MIT/Apache)
- **Intel**: Open-source i915 (MIT)
- **Wireless**: Mixed (GPL-2, BSD, proprietary firmware blobs)
- **Storage**: Open-source kernel modules + vendor firmware (typically proprietary)

See individual driver subdirectories for license details.

## Related Documentation

- [DRIVER_MANAGEMENT.md](../docs/DRIVER_MANAGEMENT.md) — Full management guide
- [ShadowOS README](../README.md) — System overview
