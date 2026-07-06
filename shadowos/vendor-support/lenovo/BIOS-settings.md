# Lenovo ThinkPad/ThinkStation BIOS Settings for ShadowOS

## Overview
Recommended BIOS/UEFI settings for optimal ShadowOS compatibility and security. These settings apply to recent ThinkPad and ThinkStation models (2020 and newer).

## Security Settings

### Secure Boot
- **Status**: Enabled
- **Secure Boot Mode**: Standard or Custom
- **Preferred OS Mode**: Windows UEFI Mode or Linux Compatible Mode
- **Secure Boot Keys**: Clear only on first installation
- **Secure Boot Policy**: Enable

**Note**: ShadowOS supports both traditional and Secure Boot. For maximum security, enable Secure Boot and use ShadowOS-signed kernels.

### TPM Security Chip
- **TPM Module Activation**: Enabled (Critical)
- **TPM Device**: TPM 2.0 (on modern models)
- **TPM Chip Visible**: Enabled
- **Clear TPM on Shutdown**: Disabled (unless troubleshooting)
- **Clear TPM**: Only on fresh ShadowOS installation

**Requirement**: TPM 2.0 is required for Platinum/Gold partnership tiers.

### Intel Platform Trust Technology (PTT)
- **PTT Support**: Enabled
- **PTT Clear on Shutdown**: Disabled
- **PTT Clear**: Manual only

### Virtualization
- **Intel Virtualization Technology**: Enabled
- **Intel VT-d (IOMMU)**: Enabled (recommended)
- **Hyper-V Support**: Disabled (unless required)
- **Nested Virtualization**: Disabled (security)

## Boot Settings

### Boot Mode
- **Boot Mode**: UEFI Only (not Legacy BIOS)
- **Boot Order**: Specify ShadowOS drive first
- **Network Boot**: PXE (if using network installation)
- **Quick Boot**: Enabled (for faster startup)
- **Startup BIOS Verbose Mode**: Disabled (unless troubleshooting)

### UEFI/BIOS Password
- **Supervisor Password**: Set (recommended)
- **User Password**: Set (optional)
- **Password on Startup**: Enabled
- **Password on Change Settings**: Enabled

## Power Management

### CPU Power Management
- **CPU Power Management**: Enabled
- **CPU Technology (Intel SpeedStep)**: Enabled
- **CPU C-States**: Enabled
  - Allow deepest C-states (C10 on modern platforms)
  - Automatic state selection preferred
- **C-State Package Limit**: Auto
- **Turbo Mode**: Enabled

### Fan Thermal Control
- **Adaptive Thermal Management**: Enabled
- **Fan Always On**: Disabled (allows smart cooling)
- **Thermal Threshold**: Normal (80-90°C)
- **Fan Curve Control**: Auto (BIOS managed)
- **Quiet Thermal Profile**: Enabled (for laptops)

### Battery Management (Laptop Models)
- **Battery Health**: Enabled
- **Start Charging Threshold**: 20% (or 10% for frequent use)
- **Stop Charging Threshold**: 80% (or 100% for desktop use)
- **Rapid Charge**: Disabled for battery longevity
- **Battery Discharge During Power Loss**: Disabled

### USB Charging (Laptop Models)
- **Always On USB**: Disabled (power saving)
- **USB Power During Sleep**: Enabled (if charging via USB-C)

## Integrated Peripherals

### Integrated Graphics (Intel)
- **Integrated Graphics Device**: Enabled
- **Shared Memory**: 256MB (or higher)
- **Integrated Graphics Priority**: Auto
- **UEFI Framebuffer**: Enabled

### Audio Subsystem
- **Audio Device**: Enabled
- **Audio Controller**: HD Audio
- **Front Audio Jack Detection**: Enabled
- **Microphone Input**: Enabled

### Touchpad
- **Touchpad**: Enabled
- **Keyboard Touchpad Combo**: Enabled
- **Trackpoint (pointing stick)**: Enabled
- **One-Touch Launch Buttons**: Enabled

### Built-in Camera (if present)
- **Camera**: Enabled (or disabled for privacy)
- **Camera Privacy Shutter**: Enabled (if available)

### WLAN/Bluetooth
- **WLAN Antenna**: Enabled
- **Bluetooth**: Enabled
- **Bluetooth Power Save**: Enabled
- **Wake on Wireless**: Disabled

### Ethernet (if available)
- **Ethernet Adapter**: Enabled
- **Ethernet PXE Boot**: Enabled (if using network boot)
- **Wake on LAN**: Disabled (security)

## Storage

### SATA Controller
- **SATA Controller Mode**: AHCI (not RAID unless required)
- **SATA Power Management**: Enabled
- **Aggressive LPM**: Disabled (stability)

### NVMe Support
- **NVMe**: Enabled
- **NVMe Cold Shutdown**: Enabled

### Storage Security
- **SSD Data Encryption**: Enabled (if hardware supported)
- **Encrypted Storage**: Enable ShadowOS disk encryption instead

## Trusted Execution & Memory Protection

### Intel TXT (Trusted Execution Technology)
- **Intel TXT Technology**: Enabled (if available)
- **TXT-capable VT-d mode**: Enabled

### AMD Secure Execution (on Ryzen ThinkPads)
- **AMD SEV (Secure Encrypted Virtualization)**: Enabled
- **AMD SME (Secure Memory Encryption)**: Enabled

### Memory Protection
- **XD Bit (Execute Disable Bit)**: Enabled
- **NX Bit**: Enabled
- **Memory Poisoning**: Enabled
- **SMRAM Protection**: Enabled

## Debug and Service Features

### Debug Features
- **Serial Port Console Redirection**: Disabled (unless needed)
- **Debug Mode**: Disabled
- **BIOS Debug**: Disabled
- **Serial Port for Debugging**: Disabled

### Service Features (Disable for security)
- **Intel AMT (Active Management Technology)**: Disabled
- **vPro**: Disabled (unless required)
- **Remote Management**: Disabled
- **Watchdog Timer**: Disabled

## USB Security

### USB Controller
- **USB Devices**: Enabled
- **USB 3.0 Controller**: Enabled
- **USB Legacy Support**: Disabled (UEFI boot preferred)
- **USB Charge-out Port**: Enabled (power delivery)

### Port Disabling
- **Disable USB Ports**: Disable non-essential ports if available
  - Keep USB 3.0 main port enabled
  - Disable unused ports for security

## Miscellaneous

### Time & Date
- **System Time**: Set to UTC
- **System Date**: Set correctly
- **Time Zone**: UTC (synced via NTP in OS)
- **Daylight Saving Time**: Disabled (OS manages)

### Language & Keyboard
- **Language**: English
- **Keyboard Layout**: US (or preferred)

### Restore Settings
- **Factory Settings**: Do not reset unless troubleshooting
- **Load Setup Defaults**: Use for baseline only
- **Load Optimal Defaults**: Recommended starting point

## Model-Specific Notes

### ThinkPad X1 Carbon / Yoga (Modern Generations)
- Uses UEFI-only boot mode
- TPM 2.0 standard
- Intel 12th Gen or newer (Alder Lake)
- Recommended: All above settings enabled

### ThinkPad T-Series (Workstation Class)
- Enterprise firmware available
- Extensive password protection options
- RAID support (may disable for ShadowOS)
- Recommended: All above settings enabled

### ThinkStation (Desktop)
- More BIOS options than laptops
- Server-grade security features available
- TPM 2.0 and TXT support
- Virtualization features extensive
- Recommended: Enable all virtualization and security features

### ThinkPad P-Series (Workstation)
- Professional GPU options
- Advanced thermal management
- Workstation-class security
- Recommended: Customize GPU memory per use case

## Post-Installation Verification

After ShadowOS installation:

```bash
# Verify TPM2.0 is recognized
tpm2_getcap handles-persistent

# Check Secure Boot status
bootctl status

# Verify IOMMU/VT-d
dmesg | grep DMAR

# Check CPU virtualization support
grep vmx /proc/cpuinfo  # Intel
grep svm /proc/cpuinfo  # AMD
```

## Support & Troubleshooting

- For BIOS update procedures, see [quirks.md](quirks.md)
- For driver issues, see [drivers-to-install.txt](drivers-to-install.txt)
- For kernel parameter conflicts, see [kernel-params.conf](kernel-params.conf)

---

**Last Updated**: 2026-07-06
**Applicable Models**: ThinkPad X1/T/P Series, ThinkStation (2020+)
**BIOS Version**: Latest available from Lenovo support
