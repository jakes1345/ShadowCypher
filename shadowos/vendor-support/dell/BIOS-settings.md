# Dell Latitude/XPS/PowerEdge BIOS Settings for ShadowOS

## Security Settings

### Secure Boot
- **Status**: Enabled
- **Secure Boot Mode**: Standard UEFI
- **Preferred OS Mode**: Linux Compatible Mode

### TPM Security
- **TPM Module**: Enabled (TPM 2.0)
- **TPM 1.2 Compatibility**: Disabled (use TPM 2.0)
- **TPM Clear on Startup**: Disabled
- **TPM Device Visible**: Enabled

### Virtualization
- **Intel Virtualization Technology (VT-x)**: Enabled
- **Intel VT-d (IOMMU)**: Enabled
- **Hyper-V Support**: Disabled
- **Nested Virtualization**: Disabled

## Boot Settings

### UEFI/Boot Mode
- **Boot Mode**: UEFI Only
- **Boot Order**: ShadowOS drive first
- **Network Boot (PXE)**: Enabled (for deployments)
- **Boot Path Security**: Enabled

### Passwords
- **Supervisor Password**: Set (required)
- **User Password**: Optional
- **Password on Startup**: Enabled

## Power Management

### CPU Power
- **CPU Power Management**: Enabled
- **C-States**: Enabled (allow deep sleep)
- **Turbo Mode (SpeedStep)**: Enabled

### Fan/Thermal
- **Adaptive Thermal Management**: Enabled
- **Fan Curve**: Auto
- **Thermal Threshold**: Normal

### Battery (Latitude/XPS)
- **Battery Health**: Enabled
- **Charge Start**: 20%
- **Charge Stop**: 80%

## Integrated Peripherals

### Graphics
- **Integrated Graphics**: Enabled
- **Shared Memory**: 256MB+

### Audio
- **Audio Device**: Enabled
- **Audio Controller**: HD Audio
- **Front Jack Detection**: Enabled

### Storage
- **SATA Controller Mode**: AHCI (not RAID unless needed)
- **NVMe Controller**: Enabled

### Network
- **Ethernet**: Enabled
- **WiFi/Bluetooth**: Enabled
- **Wake on LAN**: Disabled (security)

## Security Features

### Memory Protection
- **Execute Disable Bit**: Enabled
- **Memory Poisoning**: Enabled
- **SMRAM Protection**: Enabled

### Advanced
- **Dell Secure Boot Key**: Use manufacturer key
- **Intel TXT**: Enabled (if available)
- **AMT (Active Management Technology)**: Disabled
- **Serial Port Redirection**: Disabled

## Model-Specific Notes

| Model | Key Settings |
|-------|--------------|
| Latitude 5000/7000 | TPM 2.0, VT-d, Battery charging thresholds |
| XPS 13/15 | Disable discrete GPU when not needed for power saving |
| Precision Workstations | Enable all virtualization and memory protection features |
| PowerEdge Servers | RAID controller, iDRAC, CPU P-States, Memory RAS |

---

**Last Updated**: 2026-07-06
