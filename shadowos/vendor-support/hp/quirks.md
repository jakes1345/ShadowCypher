# HP EliteBook/ProBook Known Quirks and Workarounds

## Critical Issues

### Issue 1: SmartCard Reader Not Recognized
**Affected Models**: EliteBook 840/850, ProBook with reader slot
**Symptoms**: Smart card reader not detected, libccid not finding device
**Root Cause**: Reader not powered on at boot, BIOS setting

**Workaround**:
```bash
# Install smart card support
sudo pacman -S libccid pcsc-tools

# Check if reader is present
lsusb | grep -i smartcard
lsusb | grep -i reader

# Enable in BIOS: Security → Smart Card → Enabled

# Start reader service
sudo systemctl start pcscd
sudo systemctl enable pcscd

# Test
pcsc_scan
```

---

### Issue 2: HP Sure Start Prevents Kernel Modifications
**Affected Models**: EliteBook 840 G8+
**Symptoms**: Cannot boot custom kernels, signature verification fails
**Root Cause**: HP Sure Start BIOS security feature restricting EFI changes

**Workaround**:
```bash
# Option 1: Disable Sure Start in BIOS
# Security → HP Sure Start → Disabled

# Option 2: Use HP-signed kernel (if available)

# Option 3: Bypass via MOK enrollment
# See: https://wiki.archlinux.org/title/Secure_Boot
```

---

## Performance Issues

### Issue 3: High CPU Usage at Idle (HP Elitedesk)
**Affected Models**: EliteBook G8-G10
**Symptoms**: CPU fans loud, 30-50% CPU usage at idle
**Root Cause**: HP Management Agent or HP Connect polling

**Workaround**:
```bash
# Disable HP management services
sudo systemctl disable hp-managed-client
sudo systemctl stop hp-managed-client

# Or check for polling processes
top -p $(pgrep -f 'hp')

# Kill unnecessary processes
pkill -f 'hp-omen'
pkill -f 'hp-client'
```

---

### Issue 4: SSD Throttling After 30 Minutes
**Affected Models**: EliteBook with SK Hynix/Samsung NVMe
**Symptoms**: I/O drops from 500MB/s to 100MB/s during sustained I/O
**Root Cause**: Thermal protection, power budget

**Workaround**:
```bash
# Check NVMe temperature
sudo nvme smart-log /dev/nvme0n1 | grep Temperature

# Monitor throttling
watch -n 1 'cat /sys/devices/pci*/*/nvme/nvme0/hwmon*/temp*'

# Improve airflow with cooling pad or external heatsink
```

---

## Network Issues

### Issue 5: WiFi Drops When Using VPN
**Affected Models**: EliteBook with Intel WiFi 6
**Symptoms**: WiFi disconnects when connecting to VPN
**Root Cause**: Power management, WiFi driver and VPN interaction

**Workaround**:
```bash
# Disable WiFi power save
sudo iw dev wlan0 set power_save off

# Update WiFi firmware
fwupd get-devices
sudo fwupd update

# Or use iwd instead of wpa_supplicant
sudo pacman -S iwd
sudo systemctl enable iwd
sudo systemctl disable wpa_supplicant
```

---

## Audio Issues

### Issue 6: Microphone Input Low Level
**Affected Models**: ProBook 450, EliteBook 840
**Symptoms**: Microphone barely audible, needs boosting
**Root Cause**: ALSA mixer levels not set correctly

**Workaround**:
```bash
# Check recording devices
arecord -l

# Adjust ALSA mixer
alsamixer
# Navigate to: Input → Mic Boost: Set to maximum (20dB+)

# Or adjust via amixer
amixer sset 'Mic Boost' 100%
amixer sset 'Capture' 100%

# Test recording
arecord -d 5 test.wav
aplay test.wav
```

---

## Power Management Issues

### Issue 7: Battery Not Showing 100%
**Affected Models**: EliteBook with adaptive charging
**Symptoms**: Battery stops at 80-95%, won't charge to 100%
**Root Cause**: HP adaptive battery charging enabled for longevity

**Workaround**:
```bash
# Check battery status
upower -e

# Disable battery health mode in BIOS
# Advanced → Battery Health Preservation → Disabled

# Or set charging thresholds manually
echo 100 | sudo tee /sys/class/power_supply/BAT0/charge_stop_threshold
```

---

### Issue 8: Sleep Mode Not Working (System Stays Awake)
**Affected Models**: EliteBook 840 G9+
**Symptoms**: System doesn't sleep despite settings, high battery drain
**Root Cause**: Wake devices enabled, ACPI not cooperating

**Workaround**:
```bash
# Check wake configuration
cat /proc/acpi/wakeup

# Disable devices preventing sleep
echo "XHCI" | sudo tee /proc/acpi/wakeup
echo "GLAN" | sudo tee /proc/acpi/wakeup  # Ethernet wake

# Test sleep
systemctl suspend

# Enable only LID as wake source
echo "LID0" | sudo tee /proc/acpi/wakeup
```

---

## Display Issues

### Issue 9: USB-C Docking Monitor Not Recognized
**Affected Models**: EliteBook with USB-C dock
**Symptoms**: External monitor via dock USB-C not detected
**Root Cause**: Alternate mode negotiation failure

**Workaround**:
```bash
# Check USB-C ports
lsusb -t | grep -i "Bus"

# Manual display hotplug
xrandr --output DP-2 --auto

# Or use arandr GUI
arandr

# Disable and re-enable USB-C port
sudo echo "device_id" > /sys/bus/pci/drivers/xhci_hcd/unbind
sleep 2
sudo echo "device_id" > /sys/bus/pci/drivers/xhci_hcd/bind
```

---

## HP-Specific Issues

### Issue 10: HP QuickDrop File Sharing Conflicts
**Affected Models**: EliteBook with QuickDrop enabled
**Symptoms**: Random crashes, network instability
**Root Cause**: QuickDrop service conflicts with Linux networking

**Workaround**:
```bash
# Disable in BIOS
# Advanced → HP QuickDrop → Disabled

# Or kill the service
pkill -f quickdrop
sudo systemctl disable hp-quickdrop
```

---

### Issue 11: HP Managed Client Service Interferes
**Affected Models**: EliteBook G9-G10 with management features
**Symptoms**: System slowdown, unwanted updates, battery drain
**Root Cause**: HP Management Client continuously polling

**Workaround**:
```bash
# Check if running
ps aux | grep hp

# Disable HP management
sudo systemctl disable hp-managed-client.service
sudo systemctl stop hp-managed-client.service

# Mask it to prevent re-enabling
sudo systemctl mask hp-managed-client.service
```

---

## Compatibility Notes

| Model | Key Issues | Workarounds |
|-------|-----------|------------|
| EliteBook 840/850 | Sure Start, SmartCard | Update BIOS, enable CCID |
| ProBook 450/470 | Mic level, WiFi drops | ALSA boost, disable power save |
| Spectre x360 | Display modes, docking | xrandr, check BIOS USB-C |
| ZBook Fury | GPU cooling, throttling | Monitor temps, improve airflow |

---

**Last Updated**: 2026-07-06
