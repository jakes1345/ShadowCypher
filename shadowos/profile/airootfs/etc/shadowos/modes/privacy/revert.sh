#!/usr/bin/env bash
# privacy revert — restore normal networking, stop Tor proxy, restore browsers
set -e

# Remove privacy overlay tables and restore the base firewall.
# Do NOT flush the entire ruleset — that leaves the machine with zero protection.
nft delete table inet shadow_privacy 2>/dev/null || true
nft delete table ip6 shadow_ipv6_block 2>/dev/null || true
nft delete table inet anonsurf 2>/dev/null || true
nft delete table ip6 anonsurf_v6 2>/dev/null || true
nft -f /etc/nftables.conf
echo "  ✓ nftables: privacy rules removed — base firewall restored"

# Stop privacy services
systemctl stop tor 2>/dev/null || true
systemctl stop usbguard 2>/dev/null || true
systemctl stop i2pd 2>/dev/null || true

# dnscrypt-proxy: restart (it was running before privacy mode; keep it running)
systemctl restart dnscrypt-proxy 2>/dev/null || true

# Restore services that were stopped to prevent LAN beaconing
for svc in avahi-daemon cups; do
    systemctl start "$svc" 2>/dev/null || true
done

# Restore real browser binaries (remove firejail symlinks)
for browser in librewolf firefox chromium; do
    if [[ -L "/usr/local/bin/$browser" ]]; then
        rm -f "/usr/local/bin/$browser"
        echo "  ✓ $browser: firejail wrapper removed"
    fi
done

echo "  ✓ privacy: network restored to normal"
