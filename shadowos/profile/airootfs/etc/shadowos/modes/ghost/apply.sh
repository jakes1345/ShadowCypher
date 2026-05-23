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
conntrack -F 2>/dev/null || true
nft flush ruleset
nft -f - <<'NFT'
table inet shadow {
    chain input {
        type filter hook input priority 0; policy drop;
        iifname "lo" accept
    }
    chain output {
        type filter hook output priority 0; policy drop;
        oifname "lo" accept
        meta skuid "tor" accept
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFT

rm -rf /tmp/shadow-* /tmp/sc_* 2>/dev/null || true
sync && echo 3 > /proc/sys/vm/drop_caches
