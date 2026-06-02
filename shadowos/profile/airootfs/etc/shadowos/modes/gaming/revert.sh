#!/usr/bin/env bash
# Restore normal governors when leaving gaming mode
set -e
for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
    echo schedutil > "$cpu" 2>/dev/null || true
done
sysctl -qw vm.swappiness=60 2>/dev/null || true
sysctl -qw vm.max_map_count=65530 2>/dev/null || true
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target 2>/dev/null || true
for card in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
    echo auto > "$card" 2>/dev/null || true
done
echo "✓ Gaming mode reverted → normal governors"
