#!/usr/bin/env bash
# Revert amnesia mode — restore persistent storage, NTP, etc.
set -e

echo "  Reverting amnesia mode..."

# Stop RAM wipe service so it doesn't wipe on reboot
systemctl disable shadowos-amnesia-ramwipe.service 2>/dev/null || true
systemctl stop shadowos-amnesia-ramwipe.service 2>/dev/null || true
echo "  ✓ RAM wipe service disabled"

# Restore NTP
systemctl unmask systemd-timesyncd 2>/dev/null || true
systemctl start systemd-timesyncd 2>/dev/null || true
echo "  ✓ NTP restored"

# Restore swap (re-enable from /etc/fstab)
swapon -a 2>/dev/null || true
echo "  ✓ Swap restored"

# Restore persistent journal
sed -i 's/^Storage=.*/Storage=auto/' /etc/systemd/journald.conf 2>/dev/null || true
systemctl restart systemd-journald 2>/dev/null || true
echo "  ✓ Journal back to persistent mode"

# Stop AnonSurf / restore direct routing
if command -v shadow-anonsurf &>/dev/null; then
    shadow-anonsurf stop 2>&1 | grep -E '✓|✗' | sed 's/^/  /' || true
fi

# Remove browser firejail wrappers
for browser in librewolf mullvad-browser firefox chromium; do
    if [[ -L "/usr/local/bin/$browser" ]]; then
        rm -f "/usr/local/bin/$browser"
    fi
done

rm -f /etc/sysctl.d/99-amnesia-nodump.conf
sysctl -p 2>/dev/null || true

echo "  ✓ Amnesia mode reverted — direct routing restored"
