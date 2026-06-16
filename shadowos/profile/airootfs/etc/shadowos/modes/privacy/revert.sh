#!/usr/bin/env bash
# privacy revert — restore normal networking, stop Tor proxy, restore browsers
set -e

# Flush transparent Tor proxy rules
nft flush ruleset 2>/dev/null || true
echo "  ✓ nftables: Tor proxy rules flushed"

# Stop privacy services
systemctl stop tor 2>/dev/null || true
systemctl stop dnscrypt-proxy 2>/dev/null || true
systemctl stop usbguard 2>/dev/null || true

# Restore real browser binaries (remove firejail symlinks)
for browser in librewolf firefox chromium; do
    REAL=$(command -v "$browser" 2>/dev/null || true)
    if [[ -L "/usr/local/bin/$browser" ]]; then
        rm -f "/usr/local/bin/$browser"
        echo "  ✓ $browser: firejail wrapper removed"
    fi
done

# Restore UFW defaults
ufw default allow outgoing 2>/dev/null || true
echo "  ✓ privacy: network restored to normal"
