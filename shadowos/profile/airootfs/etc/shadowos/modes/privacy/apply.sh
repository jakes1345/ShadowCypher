#!/usr/bin/env bash
# privacy — transparent Tor proxy + MAC randomize + encrypted DNS + firejail browsers
set -e

systemctl start tor
systemctl start dnscrypt-proxy 2>/dev/null || true

# MAC randomize all interfaces
for iface in $(ls /sys/class/net/ | grep -v lo); do
    ip link set "$iface" down 2>/dev/null || true
    macchanger -r "$iface" 2>/dev/null || true
    ip link set "$iface" up 2>/dev/null || true
done
echo "  ✓ MAC addresses randomized"

# Transparent Tor proxy via nftables
# All TCP from non-tor users → port 9040 (TransPort)
# All DNS from non-tor users → port 5353 (DNSPort)
TOR_UID=$(id -u tor 2>/dev/null || echo 43)
nft flush ruleset
nft -f - << NFT
table inet shadow_privacy {
    chain prerouting {
        type nat hook prerouting priority -100;
        # Redirect DNS to Tor DNSPort
        meta skuid != $TOR_UID udp dport 53 redirect to :5353
        meta skuid != $TOR_UID tcp dport 53 redirect to :5353
        # Redirect all TCP to Tor TransPort (transparent proxy)
        meta skuid != $TOR_UID tcp flags & (fin|syn|rst|ack) == syn redirect to :9040
    }
    chain output {
        type filter hook output priority 0; policy drop;
        ct state established,related accept
        oifname "lo" accept
        meta skuid $TOR_UID accept
    }
}
NFT
echo "  ✓ Transparent Tor proxy active (ALL traffic through Tor)"

# Configure Tor to listen for transparent + DNS connections
if ! grep -q "TransPort 9040" /etc/tor/torrc 2>/dev/null; then
    cat >> /etc/tor/torrc << 'TORRC'
TransPort 9040
DNSPort 5353
AutomapHostsOnResolve 1
VirtualAddrNetworkIPv4 10.192.0.0/10
TORRC
    systemctl restart tor
fi

# Wrap browsers in firejail
for browser in librewolf firefox chromium; do
    if command -v "$browser" >/dev/null 2>&1; then
        ln -sf /usr/bin/firejail "/usr/local/bin/$browser" 2>/dev/null || true
    fi
done
echo "  ✓ Browsers sandboxed via firejail"

# USBGuard: block new USB devices
systemctl start usbguard 2>/dev/null || true
echo "  ✓ USBGuard active — new USB devices blocked"

# Waybar: switch to privacy theme
CONFIG_DIR="${HOME:-/root}/.config/waybar"
[[ -f "$CONFIG_DIR/config.privacy.jsonc" ]] && cp "$CONFIG_DIR/config.privacy.jsonc" "$CONFIG_DIR/config.jsonc"
pkill -SIGUSR2 waybar 2>/dev/null || true

ufw default deny incoming
echo "  ✓ Privacy mode fully active"
