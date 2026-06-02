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
