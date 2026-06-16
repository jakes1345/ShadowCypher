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

# Restore Hyprland compositing
if command -v hyprctl >/dev/null 2>&1; then
    DESKTOP_USER="${SUDO_USER:-}"
    if [[ -z "$DESKTOP_USER" ]]; then
        DESKTOP_USER=$(loginctl list-sessions --no-legend 2>/dev/null \
            | awk '{print $3}' | grep -v root | head -1 || echo "shadow")
    fi
    HIS=$(find /run/user/$(id -u "$DESKTOP_USER" 2>/dev/null || echo 1000)/hypr \
        -maxdepth 1 -mindepth 1 -type d 2>/dev/null | head -1 | xargs basename 2>/dev/null || true)
    if [[ -n "$HIS" ]]; then
        sudo -u "$DESKTOP_USER" env HYPRLAND_INSTANCE_SIGNATURE="$HIS" \
            hyprctl keyword decoration:blur:enabled true  2>/dev/null || true
        sudo -u "$DESKTOP_USER" env HYPRLAND_INSTANCE_SIGNATURE="$HIS" \
            hyprctl keyword animations:enabled true       2>/dev/null || true
    fi
fi

# Restore normal Waybar layout
DESKTOP_USER="${SUDO_USER:-}"
[[ -z "$DESKTOP_USER" ]] && DESKTOP_USER=$(loginctl list-sessions --no-legend 2>/dev/null \
    | awk '{print $3}' | grep -v root | head -1 || echo "shadow")
CONFIG_DIR="/home/${DESKTOP_USER}/.config/waybar"
if [[ -f "$CONFIG_DIR/config.normal.jsonc" ]]; then
    cp "$CONFIG_DIR/config.normal.jsonc" "$CONFIG_DIR/config.jsonc"
    cp "$CONFIG_DIR/style.normal.css"    "$CONFIG_DIR/style.css" 2>/dev/null || true
    pkill -SIGUSR2 waybar 2>/dev/null || true
fi
