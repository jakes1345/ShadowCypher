#!/usr/bin/env bash
# steamos — SteamOS Big Picture gaming mode for ShadowOS
# Launches full-screen Steam via gamescope, sets performance governors,
# enables controller support, and applies Proton/DXVK settings.
set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ShadowOS STEAMOS MODE — Big Picture Gaming"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# CPU → performance governor
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "performance" > "$cpu" 2>/dev/null || true
done
echo "  ✓ CPU governor → performance"

# GPU power profile (AMD)
for pwr in /sys/class/drm/*/device/power_dpm_force_performance_level; do
    echo "high" > "$pwr" 2>/dev/null || true
done
echo "  ✓ GPU power profile → high"

# Start Steam with Proton environment variables
export PROTON_NO_ESYNC=0
export PROTON_NO_FSYNC=0
export DXVK_ASYNC=1
export DXVK_FRAME_RATE=0
export STEAM_RUNTIME=1
export STEAM_LINUX_RUNTIME=1
export SDL_GAMECONTROLLERCONFIG_FILE=/etc/shadowos/modes/steamos/controller-db.txt

# Apply gamemode settings
if command -v gamemoded &>/dev/null; then
    systemctl start gamemoded 2>/dev/null || gamemoded -d 2>/dev/null || true
    echo "  ✓ GameMode daemon started"
fi

# Enable controller udev rules
udevadm trigger --subsystem-match=input --action=change 2>/dev/null || true
echo "  ✓ Controller udev rules refreshed"

# Disable compositor blur/shadows for performance (via hyprctl)
if command -v hyprctl &>/dev/null; then
    hyprctl keyword decoration:blur:enabled false 2>/dev/null || true
    hyprctl keyword decoration:shadow:enabled false 2>/dev/null || true
    hyprctl keyword animations:enabled false 2>/dev/null || true
    echo "  ✓ Hyprland compositor effects disabled for performance"
fi

# Launch gamescope session in background
echo "  ✓ Launching Steam Big Picture via gamescope..."
echo ""
echo "    Press SUPER+F10 again or run 'shadow-mode normal' to exit"
echo ""

# Run as the actual user if we're root
if [[ $EUID -eq 0 ]] && [[ -n "${SUDO_USER:-}" ]]; then
    su - "$SUDO_USER" -c "shadow-gamescope" &
else
    shadow-gamescope &
fi
