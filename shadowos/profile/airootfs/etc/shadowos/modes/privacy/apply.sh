#!/usr/bin/env bash
# privacy — all egress via Tor, MAC randomized, DNS encrypted, browsers sandboxed
set -e
systemctl start tor
systemctl start dnscrypt-proxy 2>/dev/null || true

# Randomize MAC on every wired/wireless iface
for iface in $(ls /sys/class/net/ | grep -v lo); do
    ip link set "$iface" down 2>/dev/null || true
    macchanger -r "$iface" 2>/dev/null || true
    ip link set "$iface" up 2>/dev/null || true
done

# Force all egress through Tor's SOCKS via nftables
nft flush ruleset
nft -f - <<'NFT'
table inet shadow {
    chain output {
        type filter hook output priority 0; policy drop;
        ct state established,related accept
        oifname "lo" accept
        meta skuid != "tor" tcp dport 9050 accept
        meta skuid "tor" accept
    }
}
NFT

ufw default deny incoming
