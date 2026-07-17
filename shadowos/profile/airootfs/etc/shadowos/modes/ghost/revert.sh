#!/usr/bin/env bash
# ghost revert — wipe ephemeral home, clear traces, restore AppArmor complain, undo privacy rules
set -e

# ── Shred ephemeral home before unmounting ────────────────────────────────────
# This is the Tails-style exit: data is wiped before the tmpfs goes away.
if mountpoint -q /home/shadow 2>/dev/null; then
    echo "  ✓ Shredding ephemeral home contents before unmount..."
    find /home/shadow -type f -exec shred -fuz {} \; 2>/dev/null || true
    umount -f /home/shadow 2>/dev/null || true
    echo "  ✓ Ephemeral home shredded and unmounted"
else
    echo "  ✓ Ephemeral home not mounted"
fi

# ── Clear shell histories left in memory ─────────────────────────────────────
for hist in /home/*/.bash_history /home/*/.zsh_history /root/.bash_history /root/.zsh_history; do
    [[ -f "$hist" ]] && shred -fuz "$hist" 2>/dev/null && echo "  ✓ Shredded: $hist" || true
done

# ── Wipe systemd journal in-memory buffer (live session only) ────────────────
journalctl --vacuum-size=0 2>/dev/null || true

# ── AppArmor: back to complain mode ──────────────────────────────────────────
aa-complain /etc/apparmor.d/* 2>/dev/null || true
echo "  ✓ AppArmor → complain mode"

# ── Disable RAM wipe service (no longer in ghost mode) ───────────────────────
systemctl disable shadowos-ramwipe.service 2>/dev/null || true
rm -f /etc/systemd/system/shadowos-ramwipe.service
systemctl daemon-reload 2>/dev/null || true
echo "  ✓ RAM wipe on shutdown disarmed"

# ── Restore USBGuard to block-only (allow insertion again) ───────────────────
usbguard set-parameter InsertedDevicePolicy reject 2>/dev/null || true

# ── Restore Bluetooth ─────────────────────────────────────────────────────────
rfkill unblock bluetooth 2>/dev/null || true
systemctl start bluetooth 2>/dev/null || true
echo "  ✓ Bluetooth restored"

# ── Restore webcam ────────────────────────────────────────────────────────────
modprobe uvcvideo 2>/dev/null || true
echo "  ✓ Webcam (UVC) restored"

# ── Restore original hostname ─────────────────────────────────────────────────
if [[ -f /var/lib/shadowos/ghost-pre-hostname ]]; then
    ORIG_HOST=$(cat /var/lib/shadowos/ghost-pre-hostname)
    hostnamectl set-hostname "$ORIG_HOST" 2>/dev/null || true
    rm -f /var/lib/shadowos/ghost-pre-hostname
    echo "  ✓ Hostname restored → $ORIG_HOST"
fi

# ── Inherit privacy revert ────────────────────────────────────────────────────
/etc/shadowos/modes/privacy/revert.sh
