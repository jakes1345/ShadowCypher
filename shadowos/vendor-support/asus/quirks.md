# ASUS ProBook/VivoBook/ROG Known Quirks and Workarounds

## Critical Issues

### Issue 1: Aura Sync LED Control Conflicts with Linux
**Affected Models**: ProBook 450+, VivoBook, TUF Gaming, ROG
**Symptoms**: LED constantly flickering, power drain 5-10%
**Root Cause**: BIOS Aura Sync daemon polling LED controller

**Workaround**:
```bash
# Disable Aura Sync in BIOS
# Advanced → Aura Sync → Disabled

# Or control LEDs via OpenRGB
sudo pacman -S openrgb
openrgb --config savedprofile.orp
```

---

### Issue 2: GPU Switching (Optimus) Not Working
**Affected Models**: VivoBook, ProBook with NVIDIA
**Symptoms**: Only NVIDIA GPU active, high power drain, no iGPU switching
**Root Cause**: ACPI-based switching not implemented in Linux

**Workaround**:
```bash
# Install supergfxctl for GPU management
sudo pacman -S supergfxctl

# Check GPU status
supergfxctl -S

# Switch to integrated GPU (iGPU only)
supergfxctl -m Integrated

# Switch to dedicated GPU
supergfxctl -m Dedicated

# Or use NVIDIA Prime
nvidia-smi
prime-select query  # Check current
prime-select intel  # Switch to iGPU
prime-select nvidia # Switch to dGPU
```

---

### Issue 3: Microphone Input Reversed (Stereo Swap)
**Affected Models**: VivoBook 15, ProBook with dual microphones
**Symptoms**: Built-in mic sounds like it's recording in stereo or reversed
**Root Cause**: ALSA mixer configuration mismatch with ASUS codec

**Workaround**:
```bash
# Check microphone channels
arecord -l

# Adjust ALSA mixer
alsamixer
# Navigate to Input, check Mic Left/Right balance

# Or swap channels programmatically
amixer scontrols
amixer sset 'Mic' 50,50

# Make persistent in .asoundrc
cat > ~/.asoundrc <<EOF
pcm.duplexmic {
  type asym
  playback.pcm "playback"
  capture.pcm "capture"
}
EOF
```

---

## Performance Issues

### Issue 4: Fan Noise Constant Despite Low Load
**Affected Models**: TUF Gaming, ROG (all models)
**Symptoms**: Fans spinning at 50%+ even at idle
**Root Cause**: BIOS fan curve not optimized, thermal zone aggressive

**Workaround**:
```bash
# Check fan speeds
sensors

# Adjust BIOS fan curve (Advanced → Fan Curve)
# Set idle temperature lower for smarter control

# Or use custom fan control
sudo echo "aggressive" | tee /sys/devices/virtual/thermal/cooling_device*/cur_state

# Install alternative thermal management
sudo pacman -S tlp
sudo systemctl enable tlp
sudo tlp start
```

---

### Issue 5: Thermal Throttling in Gaming
**Affected Models**: ROG Laptop, TUF Gaming
**Symptoms**: FPS drops to 30-40 after 15 minutes gaming
**Root Cause**: Power/thermal limits too conservative for sustained load

**Workaround**:
```bash
# Check power limits
cat /sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj

# Increase turbo power limit (requires BIOS unlock)
# BIOS → Advanced → Performance → Turbo Power Limit

# Or use gamemode for performance profile
gamemode  # Automatic when gaming

# Monitor throttling
watch -n 1 'cat /sys/devices/system/cpu/cpu0/cpufreq/*'
```

---

## Network Issues

### Issue 6: Intel WiFi 6 (AX200) Disconnection
**Affected Models**: ProBook 450+, VivoBook 15 (2021+)
**Symptoms**: WiFi drops every 5-10 minutes, reconnects automatically
**Root Cause**: Power saving mode too aggressive, firmware issue

**Workaround**:
```bash
# Disable WiFi power saving
sudo iw dev wlan0 set power_save off

# Or update firmware
fwupd get-devices
sudo fwupd update

# Check driver
lsmod | grep iwlwifi

# Try iwd instead of wpa_supplicant
sudo pacman -S iwd
sudo systemctl enable iwd
sudo systemctl disable wpa_supplicant
```

---

## Audio Issues

### Issue 7: Speaker Crackling/Popping at Low Volume
**Affected Models**: ProBook 450, VivoBook
**Symptoms**: Audio has static/crackling at volume <30%
**Root Cause**: Realtek codec DC offset, ALSA mixer configuration

**Workaround**:
```bash
# Disable dynamic power saving for audio
echo 0 | sudo tee /sys/module/snd_hda_intel/parameters/power_save

# Adjust mixer settings
alsamixer
# PCM: Set to 100%
# Speaker: Adjust to comfortable level (avoid <20%)

# Or use PulseAudio volume normalization
pactl set-sink-volume 0 100%

# Install audio firmware updates
sudo pacman -S sof-firmware
```

---

## Display Issues

### Issue 8: Second Display Not Detected (USB-C/Thunderbolt)
**Affected Models**: VivoBook 13 OLED, ProBook 440G8+
**Symptoms**: USB-C monitor not recognized, Thunderbolt not negotiating
**Root Cause**: Alternate mode not enabled, firmware issue

**Workaround**:
```bash
# Check USB-C port capabilities
lsusb -t

# Try manual hotplug
xrandr --output DP-2 --auto

# Or reset USB controller
sudo echo "xhci_hcd" | tee /sys/bus/pci/drivers/xhci_hcd/unbind
sleep 2
sudo echo "xhci_hcd" | tee /sys/bus/pci/drivers/xhci_hcd/bind

# Verify in BIOS: USB-C Alternate Mode Enabled
```

---

## Power Management Issues

### Issue 9: Battery Not Charging Beyond 80%
**Affected Models**: VivoBook, ProBook (battery health mode)
**Symptoms**: Stops charging at 80%, requires manual override
**Root Cause**: BIOS battery health/lifespan mode enabled

**Workaround**:
```bash
# Disable battery health mode in BIOS
# Advanced → Battery Health → Off

# Or check charge thresholds
cat /sys/class/power_supply/BAT*/charge_*

# Manually set thresholds
echo 100 | sudo tee /sys/class/power_supply/BAT0/charge_stop_threshold
```

---

### Issue 10: Sleep Does Not Resume
**Affected Models**: TUF Gaming, older ROG
**Symptoms**: System fails to wake from sleep, requires power cycle
**Root Cause**: Wake devices disabled, ACPI configuration

**Workaround**:
```bash
# Check sleep states
cat /sys/power/mem_sleep

# Enable wake devices
cat /proc/acpi/wakeup  # Check what's enabled
echo "LID0" | sudo tee /proc/acpi/wakeup  # Enable LID wake

# Test sleep/wake
systemctl suspend
# Press power button or open lid to wake

# Make wake configuration persistent
cat > /etc/systemd/system/acpi-wakeup.service <<EOF
[Unit]
Description=ACPI Wake Configuration
Before=sleep.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo LID0 > /proc/acpi/wakeup'

[Install]
WantedBy=sleep.target
EOF
```

---

## ASUS-Specific Issues

### Issue 11: asusctl Daemon Conflicts
**Affected Models**: ROG, ProBook with asusctl
**Symptoms**: Random shutdowns, brightness control not working
**Root Cause**: asusctl and systemd power management conflict

**Workaround**:
```bash
# Disable asusctl if not needed
sudo systemctl disable asusctl
sudo systemctl mask asusctl

# Or use it properly
sudo pacman -S asusctl supergfxctl
asusctl profile -P Quiet  # Low performance/quiet
asusctl profile -P Balanced
asusctl profile -P Performance

# Check status
asusctl -S
```

---

### Issue 12: Fan Curve Reset After Sleep
**Affected Models**: TUF Gaming, ROG
**Symptoms**: Fan curve reverts to aggressive after sleep/wake
**Root Cause**: BIOS fan control resetting power state

**Workaround**:
```bash
# Set fan curve in BIOS to "Auto" instead of custom
# Or apply fan settings via script after wake

# Create systemd service to reapply settings
cat > /etc/systemd/system/apply-fan-curve.service <<EOF
[Unit]
Description=Apply Fan Curve After Wake
After=suspend.target

[Service]
Type=simple
ExecStart=/usr/local/bin/apply-fan-curve.sh

[Install]
WantedBy=suspend.target
EOF

# Create script
sudo cat > /usr/local/bin/apply-fan-curve.sh <<'SCRIPT'
#!/bin/bash
# Apply custom fan settings via echo to sysfs
sleep 2  # Wait for devices to come online
# Add your fan control commands here
SCRIPT
sudo chmod +x /usr/local/bin/apply-fan-curve.sh
```

---

## Compatibility Notes

| Model | Key Issues | Workarounds |
|-------|-----------|------------|
| ProBook 450/470 | Intel WiFi drops, Mic stereo | Use iwd, check ALSA config |
| VivoBook 15 OLED | GPU switching, USB-C display | supergfxctl, xrandr hotplug |
| TUF Gaming | Thermal throttling, fan noise | BIOS curve, gamemode |
| ROG Laptop | Aura LED drain, asusctl conflicts | Disable Aura, systemctl mask asusctl |

---

**Last Updated**: 2026-07-06
