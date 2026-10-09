#!/usr/bin/env bash
# Revert steamos mode — restore desktop compositor and governors
set -e

for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "schedutil" > "$cpu" 2>/dev/null || true
done
for pwr in /sys/class/drm/*/device/power_dpm_force_performance_level; do
    echo "auto" > "$pwr" 2>/dev/null || true
done

if command -v hyprctl &>/dev/null; then
    hyprctl keyword animations:enabled true 2>/dev/null || true
fi

# Kill gamescope if running
pkill -f gamescope 2>/dev/null || true

echo "  ✓ SteamOS mode reverted — desktop restored"
