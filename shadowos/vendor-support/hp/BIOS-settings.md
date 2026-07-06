# HP EliteBook/ProBook BIOS Settings for ShadowOS

## Security Settings

### Secure Boot
- **Status**: Enabled
- **Secure Boot Mode**: Standard
- **HP Secure Boot Keys**: Use manufacturer
- **Custom Boot Options**: Allowed

### TPM Security
- **TPM Device**: Enabled (TPM 2.0)
- **TPM Support**: Enable
- **TPM 1.2 Compatibility**: Disabled
- **TPM Visibility**: Enabled

### Virtualization
- **Intel Virtualization (VT-x)**: Enabled
- **Intel VT-d (IOMMU)**: Enabled
- **Hyper-V**: Disabled
- **Nested Virtualization**: Disabled

## Boot Settings

### UEFI/Boot
- **Boot Mode**: UEFI
- **Boot Order**: ShadowOS drive first
- **Network Boot**: Enabled (optional)
- **Fast Boot**: Enabled

### Passwords
- **Supervisor Password**: Set (required)
- **User Password**: Optional
- **Password on Startup**: Enabled

## Power Management

### CPU Power
- **CPU Power Management**: Enabled
- **C-States**: Enabled
- **Turbo Mode**: Enabled

### Fan/Thermal
- **Thermal Management**: Enabled
- **Fan Control**: Automatic
- **Thermal Target**: Normal (85°C)

### Battery
- **Battery Health**: Enabled
- **Charge Start**: 20%
- **Charge Stop**: 80%
- **Rapid Charge**: Disabled

## Integrated Peripherals

### Graphics
- **Integrated Graphics**: Enabled
- **Shared Memory**: 256MB+

### Audio
- **Audio Device**: Enabled
- **HD Audio**: Enabled

### Network
- **Ethernet**: Enabled
- **WiFi**: Enabled
- **Bluetooth**: Enabled

### Storage
- **SATA Mode**: AHCI
- **NVMe**: Enabled

## Advanced Features

### Memory Protection
- **Execute Disable**: Enabled
- **Memory Protection**: Enabled

### HP-Specific
- **HP Sure Start**: Enabled (security feature)
- **HP SureRun**: Disabled (unless required)
- **QuickDrop**: Disabled

## Model-Specific Notes

| Model | Key Settings |
|-------|--------------|
| EliteBook 840/850 G8+ | TPM 2.0, VT-d, Sure Start |
| ProBook 450/470 G9+ | Battery health, audio codec |
| Spectre x360 | GPU switching, security |

---

**Last Updated**: 2026-07-06
