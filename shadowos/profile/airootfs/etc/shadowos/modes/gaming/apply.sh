#!/usr/bin/env bash
# gaming mode — performance CPU, gamemode service, low-latency audio hint
set -e

# CPU governor → performance
if command -v cpupower >/dev/null 2>&1; then
    cpupower frequency-set -g performance 2>/dev/null && echo "  ✓ CPU governor → performance"
elif [ -d /sys/devices/system/cpu ]; then
    for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$f" 2>/dev/null || true
    done
    echo "  ✓ CPU governor → performance (sysfs)"
fi

# Enable gamemode if installed (Feral GameMode — lets games request CPU boost)
if systemctl list-unit-files gamemoded.service &>/dev/null; then
    systemctl start gamemoded.service 2>/dev/null && echo "  ✓ gamemoded started" \
        || echo "  ! gamemoded start failed"
else
    echo "  - Feral GameMode not installed  →  pacman -S gamemode"
fi

# Steam / Heroic / Lutris hints (not bundled in ISO — install on demand)
if ! command -v steam &>/dev/null; then
    echo "  - Steam not installed  →  pacman -S steam"
fi

# Low-latency audio: remind user to set realtime scheduling if desired
echo "  - For low-latency audio: install realtime-privileges (pacman -S realtime-privileges)"

echo "  ✓ Gaming mode active"
