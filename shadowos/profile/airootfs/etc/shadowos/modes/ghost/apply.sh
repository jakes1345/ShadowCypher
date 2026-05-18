#!/usr/bin/env bash
# ghost — maximum lockdown. Tor only. Everything else blocked.
set -e
systemctl start tor

# Randomize MAC
for iface in $(ls /sys/class/net/ | grep -v lo); do
    ip link set "$iface" down 2>/dev/null || true
    macchanger -r "$iface" 2>/dev/null || true
    ip link set "$iface" up 2>/dev/null || true
done

# Lock down to Tor + loopback only, drop everything else
nft flush ruleset
nft -f - <<'NFT'
table inet shadow {
    chain input {
        type filter hook input priority 0; policy drop;
        ct state established,related accept
        iifname "lo" accept
    }
    chain output {
        type filter hook output priority 0; policy drop;
        ct state established,related accept
        oifname "lo" accept
        meta skuid "tor" accept
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

# Kill cached state
rm -rf /tmp/* /var/tmp/* 2>/dev/null || true
sync && echo 3 > /proc/sys/vm/drop_caches
