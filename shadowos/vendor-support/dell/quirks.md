# Dell Latitude/XPS/PowerEdge Known Quirks and Workarounds

## Critical Issues

### Issue 1: Killer WiFi Driver Not Recognized
**Affected Models**: Latitude 5000/7000 series, some XPS models
**Symptoms**: WiFi disabled, device not visible to Linux
**Root Cause**: Proprietary Dell Killer networking requires firmware and driver

**Workaround**:
```bash
# Install Linux Killer driver
sudo pacman -S ath10k-firmware
sudo pacman -S backports  # May need for newer kernels

# Or use Linux alternatives
sudo pacman -S iw wpa_supplicant iwd

# Check device
lspci | grep -i network

# Unblock radio
rfkill unblock all
```

---

### Issue 2: Dell PERC RAID Controller Detected as Loop Device
**Affected Models**: PowerEdge servers with PERC H740P, H840
**Symptoms**: RAID array shows as /dev/loop instead of /dev/sda
**Root Cause**: RAID firmware initialization incomplete at boot

**Workaround**:
```bash
# Install Dell RAID management tools
sudo pacman -S megaraid-sas-status storcli

# Initialize RAID array
sudo storcli /c0 show

# Or use Dell OpenManage Enterprise
# See: https://www.dell.com/support/home/en-us/product-support/product/poweredge-r750/docs
```

---

## Performance Issues

### Issue 3: GPU Throttling in XPS 15
**Affected Models**: XPS 15 (9500+) with NVIDIA dGPU
**Symptoms**: GPU performance drops 50% after 2-3 minutes under load
**Root Cause**: Thermal/power budget throttling, shared power delivery

**Workaround**:
```bash
# Check GPU power state
nvidia-smi -q | grep Power

# Monitor thermal
nvidia-smi dmon -s wpcume

# Set performance mode
nvidia-smi -pm 1

# Or improve cooling (external dock, cooling pad)
```

---

## Audio/Codec Issues

### Issue 4: Internal Microphone Not Working
**Affected Models**: Latitude 5000, XPS 13+
**Symptoms**: Microphone shows in `arecord -l` but no input detected
**Root Cause**: ALSA mixer gain needs adjustment, codec firmware issue

**Workaround**:
```bash
# Check microphone presence
arecord -l

# Set microphone input
alsamixer  # Navigate to Input, ensure Mic is unmuted and set to 100

# Verify with recording test
arecord -d 5 test.wav
aplay test.wav
```

---

## Network Issues

### Issue 5: Ethernet Intermittent Connection Loss
**Affected Models**: Latitude 7000 series with Intel I219 NICs
**Symptoms**: Network drops every few minutes, 2-3 second disconnect
**Root Cause**: Driver power management, interrupt coalescing

**Workaround**:
```bash
# Check driver status
ethtool -d eth0

# Disable power save
ethtool --set-eee eth0 eee off

# Adjust interrupt coalescing
ethtool -C eth0 rx-usecs 0 tx-usecs 0

# Make persistent in /etc/modprobe.d/intel-e1000.conf
options e1000e InterruptThrottleRate=0
```

---

## Display/Graphics Issues

### Issue 6: HDMI Hotplug Unreliable on Dock
**Affected Models**: Latitude with TB3/USB-C dock
**Symptoms**: Monitor not detected when docking, requires restart
**Root Cause**: Display Port alternate mode not negotiating properly

**Workaround**:
```bash
# Force display detection
xrandr --output HDMI-1 --off
sleep 1
xrandr --output HDMI-1 --auto

# Or use external display tool
arandr  # GUI for display management
```

---

## Power Management Issues

### Issue 7: High Battery Drain in Sleep (XPS)
**Affected Models**: XPS 13/15 with discrete GPU
**Symptoms**: Battery drains 10-15% per hour in sleep
**Root Cause**: Discrete GPU not powering down in S3, using S0ix

**Workaround**:
```bash
# Force S3 sleep (if available)
echo 's3' | sudo tee /sys/power/mem_sleep

# Or disable discrete GPU
prime-select intel  # Use integrated only
```

---

## Dell-Specific Issues

### Issue 8: Dell Secure Boot Certificate Conflicts
**Affected Models**: All Latitude/XPS/PowerEdge with Dell SCB keys
**Symptoms**: Cannot boot custom kernels, MOK enrollment fails
**Root Cause**: Dell UEFI certificates prevent third-party kernel signing

**Workaround**:
```bash
# Option 1: Disable Secure Boot (BIOS)
# Security → Secure Boot → Disabled

# Option 2: Enroll custom key in MOK
# See: https://wiki.archlinux.org/title/Secure_Boot

# Option 3: Use Dell-signed kernel (if available)
```

---

## Server-Specific (PowerEdge)

### Issue 9: iDRAC Network Interface Isolated
**Affected Models**: PowerEdge R750, R7515
**Symptoms**: iDRAC IP unreachable despite DHCP assignment
**Root Cause**: Dedicated iDRAC NIC not bridged to system network

**Workaround**:
```bash
# Assign iDRAC static IP (via iDRAC web interface or IPMI)
ipmitool lan set 1 ipaddr 192.168.1.100
ipmitool lan set 1 netmask 255.255.255.0

# Access iDRAC console
# https://192.168.1.100
```

---

### Issue 10: RAID Controller Not Visible to BIOS
**Affected Models**: PowerEdge with PERC H755
**Symptoms**: RAID array shows in BIOS but Linux doesn't detect
**Root Cause**: RAID driver module not loaded

**Workaround**:
```bash
# Load RAID driver module
sudo modprobe megaraid_sas

# Or include in initramfs for early boot
# Edit /etc/mkinitcpio.conf
# MODULES=(megaraid_sas ...)
# Rebuild: sudo mkinitcpio -p linux
```

---

## Compatibility Notes

| Model Line | Key Issues | Workarounds |
|------------|-----------|------------|
| Latitude 3000/5000 | Killer WiFi, display | Use iwd driver, check BIOS hotplug |
| Latitude 7000 | Ethernet drops, docking | ethtool settings, xrandr |
| XPS 13/15 | GPU throttling, GPU drain | Monitor temps, use prime-select |
| Precision | CUDA compatibility | Install cuda-toolkit via NVIDIA |
| PowerEdge | RAID detection, iDRAC | Load megaraid_sas, set iDRAC IP |

---

**Last Updated**: 2026-07-06
