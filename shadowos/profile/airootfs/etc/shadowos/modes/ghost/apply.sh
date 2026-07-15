#!/usr/bin/env bash
# ghost — maximum lockdown: transparent Tor, firejail everything, USBGuard, ephemeral home
set -e

# Inherit all privacy protections
/etc/shadowos/modes/privacy/apply.sh

# Block ALL USB except already-connected devices
systemctl start usbguard
usbguard generate-policy > /tmp/usbguard-boot-policy.rules 2>/dev/null || true
[[ -f /tmp/usbguard-boot-policy.rules ]] && cp /tmp/usbguard-boot-policy.rules /etc/usbguard/rules.conf
usbguard set-parameter InsertedDevicePolicy block
echo "  ✓ USBGuard → only boot-time devices allowed"

# Enable AppArmor enforce mode
aa-enforce /etc/apparmor.d/* 2>/dev/null || true
echo "  ✓ AppArmor → enforce mode"

# Spawn ephemeral tmpfs over /home/shadow (session data gone on reboot)
if ! mountpoint -q /home/shadow 2>/dev/null; then
    mkdir -p /home/shadow
    mount -t tmpfs -o size=2G,mode=700 tmpfs /home/shadow
    cp -r /etc/skel/. /home/shadow/ 2>/dev/null || true
    chown -R shadow:shadow /home/shadow 2>/dev/null || true
    echo "  ✓ Ephemeral home mounted (tmpfs) — session data vanishes on reboot"
fi

# Bluetooth kill — radio off at the rfkill level, daemon stopped
rfkill block bluetooth 2>/dev/null || true
systemctl stop bluetooth 2>/dev/null || true
echo "  ✓ Bluetooth hardware radio blocked"

# Webcam kill — unload UVC driver to prevent covert capture
modprobe -r uvcvideo 2>/dev/null || true
echo "  ✓ Webcam (UVC) driver unloaded"

# Randomize hostname — prevent LAN-level identity correlation across sessions
mkdir -p /var/lib/shadowos
ORIG_HOST=$(hostnamectl hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo "shadowos")
echo "$ORIG_HOST" > /var/lib/shadowos/ghost-pre-hostname
RAND_HOST="shadow-$(tr -dc 'a-f0-9' </dev/urandom 2>/dev/null | head -c8 || date +%s | sha256sum | head -c8)"
hostnamectl set-hostname "$RAND_HOST" 2>/dev/null || true
echo "  ✓ Hostname randomized → $RAND_HOST (real: $ORIG_HOST)"

# Register RAM wipe on shutdown
cat > /etc/systemd/system/shadowos-ramwipe.service << 'UNIT'
[Unit]
Description=ShadowOS Ghost — Secure RAM Wipe on Shutdown
DefaultDependencies=no
Before=shutdown.target reboot.target halt.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/shadowos-ramwipe
TimeoutStartSec=30
[Install]
WantedBy=shutdown.target reboot.target halt.target
UNIT
systemctl daemon-reload
systemctl enable shadowos-ramwipe.service 2>/dev/null || true
echo "  ✓ RAM wipe on shutdown armed"

echo ""
echo "👻 Ghost Mode: MAXIMUM LOCKDOWN"
echo "   All traffic → Tor | Home → tmpfs | USB → blocked | AppArmor → enforced"
