#!/usr/bin/env bash
# ghost revert — undo ephemeral home, AppArmor complain mode, restore privacy revert
set -e

# AppArmor: back to complain mode
aa-complain /etc/apparmor.d/* 2>/dev/null || true
echo "  ✓ AppArmor → complain mode"

# Disable RAM wipe service (no longer in ghost mode)
systemctl disable shadowos-ramwipe.service 2>/dev/null || true
rm -f /etc/systemd/system/shadowos-ramwipe.service
systemctl daemon-reload 2>/dev/null || true
echo "  ✓ RAM wipe on shutdown disarmed"

# Unmount ephemeral home if mounted
if mountpoint -q /home/shadow 2>/dev/null; then
    echo "  ⚠ Ephemeral home still mounted — will persist until reboot"
fi

# Inherit privacy revert
/etc/shadowos/modes/privacy/revert.sh
