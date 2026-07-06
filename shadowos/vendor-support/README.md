# Vendor-Specific Support Configurations

This directory contains hardware vendor-specific configurations for ShadowOS pre-load and optimization. Each vendor subdirectory contains platform-specific kernel parameters, driver configurations, BIOS settings, and known quirks.

## Directory Structure

```
vendor-support/
├── lenovo/              # Lenovo ThinkPad/ThinkStation configurations
├── dell/                # Dell Latitude/XPS/PowerEdge configurations
├── asus/                # ASUS ProBook/VivoBook configurations
├── hp/                  # HP EliteBook/ProBook configurations
└── README.md            # This file
```

## Per-Vendor Directory Contents

Each vendor subdirectory contains the following files:

### kernel-params.conf
Vendor-specific kernel parameters optimized for the hardware platform. Includes:
- CPU governor and frequency scaling settings
- Memory management parameters
- I/O scheduler tuning
- Thermal management settings
- Power management parameters
- Security-related kernel parameters (SELinux, AppArmor)

**Format**: INI-style configuration file with sections for different kernel subsystems

### drivers-to-install.txt
List of essential and recommended drivers for the vendor's platforms:
- Network drivers (Ethernet, WiFi, Cellular)
- GPU drivers (Intel, NVIDIA, AMD)
- Touchpad and input device drivers
- Audio subsystem drivers
- Power management firmware
- BIOS/UEFI update utilities

**Format**: Line-separated package names compatible with pacman package manager

### BIOS-settings.md
Documentation of recommended BIOS/UEFI settings for ShadowOS optimization:
- Secure Boot configuration
- TPM 2.0 enabling and settings
- Virtualization features (Intel VT-x/AMD-V)
- Hardware virtualization (Intel VT-d/AMD-Vi)
- Power management settings
- Fan curve optimization
- Memory protection features
- Debug port disabling

### quirks.md
Known hardware quirks, workarounds, and vendor-specific issues:
- Incompatibilities with ShadowOS components
- Required kernel patches or driver modifications
- BIOS update procedures and precautions
- Known performance limitations
- Thermal or power management issues
- Display/GPU-specific quirks
- Audio subsystem issues
- Network driver oddities

## Vendor Configuration Format

### kernel-params.conf Format

```ini
[cpu]
# CPU scaling governor: performance, powersave, schedutil, ondemand
cpu_governor=schedutil
cpu_max_freq=3600000
cpu_min_freq=800000

[io]
# I/O scheduler: mq-deadline, kyber, bfq, noop
io_scheduler=mq-deadline

[memory]
# Memory swappiness (0-100)
vm_swappiness=10
# Dirty ratio for background writeout
vm_dirty_ratio=20

[power]
# Laptop battery threshold percentages
battery_charge_start=20
battery_charge_stop=80

[security]
# SELinux mode: enforcing, permissive, disabled
selinux_mode=enforcing
```

### drivers-to-install.txt Format

```
linux-firmware
intel-microcode  # or amd-microcode for AMD systems
networkmanager
iw
wpa_supplicant
alsa-utils
pulseaudio
xf86-video-intel  # or appropriate GPU driver
xf86-input-synaptics
```

### BIOS-settings.md Format

```markdown
## Lenovo ThinkPad X1 Carbon Gen 10

### Security Settings
- **Secure Boot**: Enabled (recommended)
  - Mode: Standard
  - Preferred OS: Windows UEFI Mode
  - Alternative: Linux Compatible Mode (for ShadowOS)
- **TPM Security Chip**: Enabled (required)
  - Clear TPM: Only on first install
- **Intel Platform Trust Technology**: Enabled

### Power Management
- **Adaptive Thermal Management**: Enabled
- **Fan Always On**: Disabled (allows smart cooling)
- **CPU Power Management**: Enabled
- **Integrated Graphics Power Saving**: Enabled

### Virtualization
- **Intel Virtualization Technology**: Enabled
- **Intel VT-d**: Enabled
```

### quirks.md Format

```markdown
## Known Issues and Workarounds

### Issue: WiFi 6E not detected on startup
**Affected Models**: ThinkPad X1 Extreme Gen 5
**Symptoms**: WiFi adapter disabled or not recognized
**Workaround**: Unblock with rfkill
```

## Using Vendor Configurations

### For Pre-Load Distribution

1. Select appropriate vendor directory
2. Extract kernel-params.conf
3. Merge with default ShadowOS kernel configuration
4. Install drivers from drivers-to-install.txt
5. Apply BIOS settings documented in BIOS-settings.md
6. Create bootable pre-load image with vendor customizations

### For End-User Optimization

1. Identify device vendor and model
2. Apply kernel parameters from vendor/kernel-params.conf
3. Verify recommended BIOS settings match documentation
4. Install any missing drivers
5. Check quirks.md for known issues and workarounds

### Example: Applying Lenovo Configuration

```bash
# Copy kernel parameters to system configuration
sudo cp lenovo/kernel-params.conf /etc/sysctl.d/99-lenovo-optimization.conf

# Install vendor-specific drivers
cat lenovo/drivers-to-install.txt | pacman -S -

# Review BIOS settings
cat lenovo/BIOS-settings.md

# Check known quirks
cat lenovo/quirks.md
```

## Vendor Partnership Program Integration

These vendor configurations are maintained as part of the ShadowOS Vendor Partnership Program. See [../.github/vendor-partnerships.md](../../.github/vendor-partnerships.md) for partnership information.

Vendors participate in:
- **Platinum Program**: Custom kernel optimization, priority support
- **Gold Program**: Standard kernel parameters, regular updates
- **Silver Program**: Community configurations, basic support

## Maintenance and Updates

### Update Frequency
- Kernel parameters: Quarterly reviews
- Driver lists: Monthly updates (new releases)
- BIOS settings: As manufacturer specifications change
- Quirks: Continuous (reported by users and support team)

### Reporting Issues

For vendor-specific issues:
1. Report via vendor support portal: vendor-support@shadowcypher.site
2. Include: Device model, ShadowOS version, specific issue
3. Provide reproduction steps and system logs
4. Support team will evaluate and update configurations

## Contributing Vendor Configurations

New vendor support can be added by:

1. **Creating vendor directory** under vendor-support/
2. **Submitting PR** with:
   - kernel-params.conf (optimized parameters)
   - drivers-to-install.txt (essential drivers)
   - BIOS-settings.md (recommended settings)
   - quirks.md (known issues and workarounds)
3. **Testing and validation** by ShadowOS team
4. **Inclusion in certification** and pre-load program

## Supported Vendors

- **Lenovo**: ThinkPad, ThinkStation, ThinkBook
- **Dell**: Latitude, XPS, PowerEdge, Precision
- **ASUS**: ProBook, VivoBook, TUF, ROG
- **HP**: EliteBook, ProBook, Envy

Contact vendor-partnerships@shadowcypher.site to add your hardware vendor.

---

**Last Updated**: 2026-07-06
**Version**: 1.0
