# Lenovo ThinkPad/ThinkStation Known Quirks and Workarounds

## Overview
This document lists known hardware compatibility issues, quirks, and workarounds for ShadowOS on Lenovo ThinkPad and ThinkStation platforms.

## Critical Issues

### Issue 1: WiFi 6E Module Not Detected on First Boot
**Affected Models**: ThinkPad X1 Extreme Gen 5+, ThinkPad Z-Series
**Symptoms**: WiFi adapter disabled, shows as "soft-blocked"
**Root Cause**: Hardware killswitch or RF-kill state not cleared during boot

**Workaround**:
```bash
# Check RF-kill status
rfkill list all

# Unblock WiFi if necessary
sudo rfkill unblock wifi
sudo rfkill unblock all

# Verify with NetworkManager
nmtui

# Make persistent via kernel parameter
# Add to /etc/sysctl.d/99-rfkill.conf:
# net.wireless.rfkill_default=0
```

**Prevention**: Enable BIOS settings:
- Wireless Device Enabled
- WLAN Antenna: Enabled
- Integrated Wireless LAN: On

---

### Issue 2: NVIDIA GPU Driver Installation Fails on Secure Boot
**Affected Models**: ThinkPad X1 Extreme Gen 3+, ThinkPad P-Series
**Symptoms**: NVIDIA driver fails to compile, Nouveau module blocks installation
**Root Cause**: DKMS module signing incompatibility with Secure Boot

**Workaround**:

Option 1: Disable Secure Boot (not recommended)
```bash
# In BIOS: Security → Secure Boot → Disabled
```

Option 2: Sign NVIDIA drivers
```bash
# Install NVIDIA with signing
sudo pacman -S nvidia-open-dkms

# If still failing, use Nouveau driver
sudo pacman -S xf86-video-nouveau

# Or compile with MOK (Machine Owner Key)
# See: https://wiki.archlinux.org/title/Secure_Boot
```

**Prevention**: Use `nvidia-open-dkms` instead of legacy `nvidia-dkms` on modern GPUs.

---

### Issue 3: Fingerprint Reader Not Working
**Affected Models**: ThinkPad with integrated fingerprint sensor
**Symptoms**: `fprintd` service fails, sensor not recognized
**Root Cause**: Missing or outdated libfprint driver

**Workaround**:
```bash
# Install libfprint-2 explicitly
sudo pacman -S libfprint-2 fprintd pam-fprintd

# Enroll fingerprints
fprintd-enroll

# Verify driver loaded
lsusb | grep -i fingerprint
```

**Prevention**: Ensure libfprint-2 is in `drivers-to-install.txt` list.

---

## Performance Issues

### Issue 4: High CPU Temperature on IdleThreads
**Affected Models**: ThinkPad X1 Carbon Gen 9-10, T14 Gen 2+
**Symptoms**: CPU runs at 60-70°C at idle, fans constantly spinning
**Root Cause**: Aggressive turbo boost settings, C-states not entering deep sleep

**Workaround**:
```bash
# Verify C-states are enabled
cat /proc/cpuinfo | grep cstate

# Check turbo boost status
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Disable turbo boost for battery life
echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo

# Or set max frequency lower
sudo cpupower frequency-set -u 2400MHz

# Apply TLP profile for laptop
sudo systemctl enable tlp
sudo tlp start
```

**Prevention**: Apply `kernel-params.conf` settings, enable adaptive thermal management in BIOS.

---

### Issue 5: NVMe Drive Thermal Throttling
**Affected Models**: ThinkPad with Samsung/SK Hynix NVMe drives
**Symptoms**: SSD slows to HDD speeds after heavy I/O (backup, compilation)
**Root Cause**: Thermal protection activating at 75-85°C

**Workaround**:
```bash
# Monitor NVMe temperature
sudo nvme-cli smart-log /dev/nvme0n1

# Check throttling status
cat /sys/devices/pci*/*/nvme/nvme*/hwmon*/temp*

# Improve airflow with heatspreader
# Or reduce sustained I/O workload

# For persistent monitoring
watch -n 1 'sudo nvme smart-log /dev/nvme0n1 | grep -i temp'
```

**Prevention**: Ensure adequate disk airflow, use SSD with passive cooling.

---

## Compatibility Issues

### Issue 6: USB-C DisplayPort Hotdocking Not Working
**Affected Models**: ThinkPad X1 Carbon, ThinkPad Yoga with docking station
**Symptoms**: External monitor not recognized when docking, requires reboot
**Root Cause**: BIOS not properly negotiating USB-C alternating mode

**Workaround**:
```bash
# Manual hotplug trigger
xrandr --query  # Detect new output
xrandr --output DP-2 --auto  # Enable new output

# Or use display manager to handle
# For GNOME/KDE, monitors should auto-detect

# If still failing, reset USB controller
sudo echo "0000:00:0d.0" | tee /sys/bus/pci/drivers/xhci_hcd/unbind
sleep 1
sudo echo "0000:00:0d.0" | tee /sys/bus/pci/drivers/xhci_hcd/bind
```

**Prevention**: Update BIOS to latest version. Disable USB C DisplayPort in BIOS if not needed.

---

### Issue 7: Bluetooth Connectivity Drops
**Affected Models**: ThinkPad with MediaTek Bluetooth modules
**Symptoms**: Bluetooth audio cuts out, keyboard disconnects during use
**Root Cause**: Firmware issue with power management, interference with WiFi

**Workaround**:
```bash
# Check Bluetooth adapter firmware
hciconfig -a

# Reconnect device
bluetoothctl
> disconnect <device-mac>
> connect <device-mac>

# Reset Bluetooth subsystem
sudo systemctl restart bluetooth

# Disable Bluetooth power save
# Edit /etc/bluetooth/main.conf:
# [Policy]
# FastConnectable = true
# EnableBrEDR = true
```

**Prevention**: Update WiFi/Bluetooth firmware via `fwupd`.

---

### Issue 8: Trackpad Cursor Acceleration Issues
**Affected Models**: ThinkPad with Elantech touchpad
**Symptoms**: Cursor jumps, erratic movement, sensitivity inconsistent
**Root Cause**: libinput vs. Synaptics driver conflict

**Workaround**:
```bash
# Use libinput (recommended)
sudo pacman -S xf86-input-libinput
sudo pacman -R xf86-input-synaptics  # Remove if conflicting

# Configure libinput
cat > ~/.config/libinput-gestures.conf <<EOF
gesture swipe up 3 xdotool key super
gesture swipe down 3 xdotool key alt+Tab
EOF

# Enable natural scrolling
gsettings set org.gnome.desktop.peripherals.touchpad natural-scroll true
```

**Prevention**: Use `xf86-input-libinput` for modern ThinkPads, Synaptics for older models.

---

## Power Management Issues

### Issue 9: Battery Drain When Suspended
**Affected Models**: ThinkPad X1 Carbon Gen 8-10
**Symptoms**: Battery drains 5-10% per hour in sleep, should be <1%
**Root Cause**: USB devices preventing deep sleep (S3), using S0ix shallow sleep

**Workaround**:
```bash
# Check S3 sleep availability
cat /sys/power/mem_sleep

# Force S3 sleep (if available)
# Edit /etc/default/grub:
# GRUB_CMDLINE_LINUX="... mem_sleep_default=s3"
# Then: sudo grub-mkconfig -o /boot/grub/grub.cfg

# Disable USB wakeup sources
cat /proc/acpi/wakeup  # Check wakeup-enabled devices
sudo echo "XHCI > /proc/acpi/wakeup"  # Disable USB wake

# Check for rogue processes preventing suspend
sudo powertop  # Check "Wakeups from sleep" tab
```

**Prevention**: Disable USB wake sources in BIOS, manage peripheral power.

---

### Issue 10: Keyboard Backlight Drain on Battery
**Affected Models**: ThinkPad with RGB keyboard
**Symptoms**: Battery life reduced 20-30%, keyboard brightness not saving
**Root Cause**: Backlight not respecting power profile settings

**Workaround**:
```bash
# Disable keyboard backlight when on battery
echo 0 | sudo tee /sys/class/leds/*/brightness

# Use thinkpad_acpi to control
echo 0 | sudo tee /proc/acpi/ibm/led  # 0=off, 1=on

# Make persistent via TLP
sudo tee -a /etc/tlp.conf <<EOF
START_CHARGE_THRESH_BAT0=20
STOP_CHARGE_THRESH_BAT0=80
LED_CONTROL_ON_BAT=0  # Disable LEDs on battery
EOF

sudo tlp start
```

**Prevention**: Configure LED control in TLP or systemd power profiles.

---

## Audio Issues

### Issue 11: Audio Jack Detection Fails
**Affected Models**: ThinkPad with analog audio jack
**Symptoms**: Speaker output defaults to laptop speaker, jack not detected when plugging in
**Root Cause**: ALSA/PulseAudio jack detection not configured

**Workaround**:
```bash
# Install audio packages
sudo pacman -S alsa-utils pulseaudio pulseaudio-alsa

# Check audio hardware
arecord -l  # Recording devices
aplay -l    # Playback devices

# Configure ALSA jack detection
alsactl init
alsactl store

# Use PulseAudio to manage
pulseaudio --start
pavucontrol  # GUI for audio management

# Force analog output
pactl set-default-sink alsa_output.pci-0000_00_1f.3.analog-stereo
```

**Prevention**: Ensure jack detection hardware switch is enabled in BIOS.

---

## BIOS Update Issues

### Issue 12: BIOS Update Failed / Bricked
**Affected Models**: All ThinkPad/ThinkStation
**Symptoms**: Failed BIOS flash leaves system unbootable, hung during update
**Root Cause**: Power loss, corrupted firmware image, or incompatible version

**Workaround** (Prevention Only):
```bash
# Check current BIOS version
sudo dmidecode | grep -i "BIOS Information" -A 3

# Download correct BIOS for your model
# From: https://support.lenovo.com (search by serial/model)

# Create bootable USB
sudo dd if=lenovo_bios_update.iso of=/dev/sdX bs=4M conv=fsync

# Boot from USB and follow on-screen instructions
# CRITICAL: Do NOT power off or interrupt update process
# CRITICAL: Ensure AC power is connected
```

**Prevention**: 
- Always use official Lenovo firmware
- Verify checksum before flashing
- Keep AC power connected throughout
- Disable security features (Secure Boot, TPM) during update if required

---

## Networking Issues

### Issue 13: Intel WiFi 6 (AX) Unstable Connections
**Affected Models**: ThinkPad X1 Carbon Gen 9+, ThinkPad Yoga with Intel AX
**Symptoms**: WiFi disconnects intermittently, switching between 5GHz/2.4GHz
**Root Cause**: Firmware power saving, band steering conflicts

**Workaround**:
```bash
# Update WiFi firmware
fwupd get-devices  # Check for WiFi updates
sudo fwupd update

# Disable power save
iw dev wlan0 set power_save off

# Force single band (temporary)
nmcli connection modify <wifi-name> 802-11-wireless.band a  # 5GHz only
nmcli connection up <wifi-name>

# Or use iwd instead of wpa_supplicant
sudo pacman -S iwd
sudo systemctl enable iwd
sudo systemctl disable wpa_supplicant
```

**Prevention**: Update firmware regularly, use compatible AP standards.

---

## Display Issues

### Issue 14: HDMI Hotplug Not Detected
**Affected Models**: ThinkPad with HDMI 2.1
**Symptoms**: External monitor via HDMI not detected without reboot
**Root Cause**: ALPM (Aggressive Link Power Management) suspending HDMI port

**Workaround**:
```bash
# Force HDMI rescan
xrandr --output HDMI-1 --off && xrandr --output HDMI-1 --auto

# Disable ALPM for video
sudo tee /etc/modprobe.d/nouveau.conf <<EOF
# Disable ALPM for better hotplug
options nouveau pstate=0
EOF

# Or use systemd monitor trigger
systemctl start systemd-monitor  # In some distros
```

**Prevention**: Update GPU drivers (NVIDIA/Intel/AMD), configure display manager to handle hotplug.

---

## Security-Related Quirks

### Issue 15: TPM Attestation Fails in Secure Boot
**Affected Models**: ThinkPad with discrete TPM or PTT
**Symptoms**: TPM reads fail, attestation errors during ShadowOS verification
**Root Cause**: TPM state corruption after failed BIOS update or incomplete secure boot chain

**Workaround**:
```bash
# Check TPM status
tpm2_getcap handles-persistent
tpm2_getcap properties-fixed

# Clear TPM (CAUTION: removes all TPM-sealed secrets)
sudo systemctl stop tpm2-abrmd  # Stop TPM daemon
sudo tpm2_clear -C p
sudo systemctl start tpm2-abrmd

# Reseal TPM for ShadowOS attestation
tpm2_pcrread sha256
```

**Prevention**: Perform TPM clear in BIOS during initial ShadowOS install, keep firmware updated.

---

## Model-Specific Recommendations

| Model | Key Quirks | Workarounds |
|-------|-----------|------------|
| X1 Carbon Gen 10+ | GPU driver, TPM attestation | Use nvidia-open-dkms, update BIOS |
| X1 Extreme | WiFi 6E detection, thermal | rfkill unblock, TLP power profile |
| T14 Gen 2+ | Trackpad sensitivity, Bluetooth | libinput driver, firmware update |
| P-Series | NVIDIA certification, virtualization | Driver signing, enable VT-d |
| ThinkStation | RAID conflicts, PCIe performance | Disable RAID unless required |

---

## Reporting New Issues

If you encounter an issue not listed here:

1. **Collect diagnostics**:
   ```bash
   sudo dmesg > ~/dmesg.log
   lspci > ~/lspci.log
   lsusb > ~/lsusb.log
   inxi -v > ~/inxi.log
   ```

2. **Report to vendor support**: vendor-support@shadowcypher.site
3. **Include**:
   - Exact ThinkPad/ThinkStation model and BIOS version
   - ShadowOS version and kernel version
   - Reproduction steps
   - Error messages and logs

---

**Last Updated**: 2026-07-06
**Applies To**: ThinkPad/ThinkStation models 2018 and newer
**Firmware Version**: Latest available from Lenovo Support
