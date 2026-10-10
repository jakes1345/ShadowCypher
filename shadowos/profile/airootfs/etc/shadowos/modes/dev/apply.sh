#!/usr/bin/env bash
# dev mode — performance CPU, open dev ports, start container runtime
set -e
source /etc/shadowos/modes/_network_open.sh
shadowos_network_open

# CPU governor → performance
if command -v cpupower >/dev/null 2>&1; then
    cpupower frequency-set -g performance 2>/dev/null && echo "  ✓ CPU governor → performance"
elif [ -d /sys/devices/system/cpu ]; then
    for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$f" 2>/dev/null || true
    done
    echo "  ✓ CPU governor → performance (sysfs)"
fi

# Start Docker if installed, don't fail if not
if systemctl list-unit-files docker.service &>/dev/null; then
    systemctl start docker.service 2>/dev/null && echo "  ✓ Docker started" \
        || echo "  ! Docker start failed (install: pacman -S docker)"
else
    echo "  - Docker not installed  →  pacman -S docker docker-compose"
fi

# Start Podman socket if installed
systemctl --user start podman.socket 2>/dev/null || true

# Open dev ports in nftables — loopback-only for DB ports, LAN-accessible for web ports
# Only adds the rule if not already present
if ! nft list ruleset 2>/dev/null | grep -q "shadowos_dev"; then
    nft add table inet shadowos_dev 2>/dev/null || true
    nft add chain inet shadowos_dev input "{ type filter hook input priority 0; }" 2>/dev/null || true
    # Web/API ports — accept from any (localhost + LAN dev servers)
    for port in 3000 8080 8443 9000; do
        nft add rule inet shadowos_dev input tcp dport "$port" accept 2>/dev/null || true
    done
    # DB ports (postgres 5432, redis 6379) — loopback only
    for port in 5432 6379; do
        nft add rule inet shadowos_dev input iifname lo tcp dport "$port" accept 2>/dev/null || true
    done
    echo "  ✓ Dev ports open: 3000 8080 8443 9000 (any), 5432 6379 (loopback only)"
fi

echo "  ✓ Dev mode active"
