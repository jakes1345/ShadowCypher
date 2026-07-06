# ASUS ProBook/VivoBook/ROG BIOS Settings for ShadowOS

## Security Settings

### Secure Boot
- **Status**: Enabled
- **Secure Boot Mode**: Standard
- **Key Management**: Allow custom keys (MOK)

### TPM Security
- **TPM Device**: Enabled (TPM 2.0)
- **TPM 1.2**: Disabled
- **TPM Clear**: Disabled
- **PTT (Platform Trust Technology)**: Enabled (Intel models)

### Virtualization
- **Intel Virtualization**: Enabled
- **Intel VT-d**: Enabled
- **AMD-V**: Enabled (Ryzen models)
- **AMD-Vi (IOMMU)**: Enabled (Ryzen models)
- **Hyper-V**: Disabled

## Boot Settings

### UEFI/Boot
- **Boot Mode**: UEFI Only
- **Boot Order**: ShadowOS drive first
- **Network Boot**: Enabled (if needed)
- **Fast Boot**: Enabled

### Passwords
- **Supervisor Password**: Set (recommended)
- **User Password**: Optional
- **Password on Startup**: Enabled

## Power Management

### CPU Power
- **CPU Power Management**: Enabled
- **C-States**: Enabled (allow C10+)
- **Turbo Mode**: Enabled
- **Multi-Core Performance**: Enabled

### Fan/Thermal
- **Thermal Management**: Enabled
- **Fan Curve**: Auto or Custom (for gaming)
- **Thermal Target**: Normal (80°C)

### Battery (Laptop)
- **Battery Health**: Enabled
- **Charge Threshold**: 20-80%
- **Rapid Charge**: Disabled (battery longevity)

## Integrated Peripherals

### GPU/Graphics
- **Integrated Graphics**: Enabled
- **Shared Memory**: 256MB+
- **GPU Switching (Optimus)**: Enabled (dual GPU models)

### Audio
- **Audio Device**: Enabled
- **HD Audio**: Enabled
- **Front Panel Audio**: Enabled

### Network
- **Ethernet**: Enabled
- **WiFi**: Enabled
- **Bluetooth**: Enabled
- **Wake on LAN**: Disabled

### Storage
- **SATA Mode**: AHCI
- **NVMe**: Enabled
- **M.2 Slot 1/2**: Enabled

## Advanced Features

### Memory Protection
- **Execute Disable**: Enabled
- **Memory Protection**: Enabled
- **SMRAM Protection**: Enabled

### ASUS-Specific
- **AiOverclock**: Disabled (ShadowOS manages CPU)
- **XMP/DOCP**: Disabled (stability)
- **Sonic Studio**: Disabled (OS manages audio)
- **Aura Sync**: Disabled (O managed)

## Model-Specific Notes

| Model | Key Settings |
|-------|--------------|
| ProBook 450/470 | TPM 2.0, VT-d, Throttling management |
| VivoBook 15/16 | GPU switching, battery thresholds |
| TUF Gaming | Thermal profiles, cooling fan curve |
| ROG Laptop | Turbo power limits, discrete GPU priority |

---

**Last Updated**: 2026-07-06
