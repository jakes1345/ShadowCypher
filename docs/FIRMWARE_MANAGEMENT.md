# ShadowOS Firmware Management

## Checking Firmware Updates

```bash
sudo shadowos-firmware-manager check
```

## Installing Updates

```bash
# Install all updates
sudo shadowos-firmware-manager install

# View update history
sudo shadowos-firmware-manager history
```

## Supported Devices

Firmware updates for:
- **System firmware** (BIOS/UEFI)
- **WiFi adapters**
- **Bluetooth devices**
- **Storage controllers**
- **Graphics cards**

## Safety

Firmware updates are:
- Signed and verified
- Backed up before installation
- Atomic (safe to interrupt)
- Tested before rollout

## Firmware Downgrade

To downgrade to a previous firmware version:

```bash
sudo fwupdmgr downgrade
```

## Troubleshooting

If firmware update fails:

```bash
# Check logs
sudo journalctl -u fwupd -n 50

# Retry update
sudo systemctl restart fwupd
sudo shadowos-firmware-manager install
```
