# Vendor-Specific Firmware

Firmware packages and update instructions for certified hardware vendors.

## Directories

- **bios/** - System firmware (BIOS/UEFI)
- **wifi/** - WiFi adapter firmware
- **storage/** - NVMe/SATA controller firmware
- **graphics/** - GPU firmware

## Updating Firmware

```bash
sudo shadowos-firmware-manager install
```

Firmware is automatically detected and installed.
