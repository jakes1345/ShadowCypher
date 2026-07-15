#!/usr/bin/env bash
# undercover revert — restore normal waybar theme (network was already open, nothing else to undo)
set -e

# Restore normal waybar theme (theme-apply handles this via shadow-mode, but
# be explicit here in case revert.sh is called standalone)
DESKTOP_USER="${SUDO_USER:-}"
[[ -z "$DESKTOP_USER" ]] && DESKTOP_USER=$(loginctl list-sessions --no-legend 2>/dev/null \
    | awk '{print $3}' | grep -v root | head -1 || echo "shadow")
CONFIG_DIR="/home/${DESKTOP_USER}/.config/waybar"
if [[ -f "$CONFIG_DIR/config.normal.jsonc" ]]; then
    cp -f "$CONFIG_DIR/config.normal.jsonc" "$CONFIG_DIR/config.jsonc"
    [[ -f "$CONFIG_DIR/style.normal.css" ]] && cp -f "$CONFIG_DIR/style.normal.css" "$CONFIG_DIR/style.css"
    pkill -SIGUSR2 waybar 2>/dev/null || true
fi

echo "  ✓ undercover: theme restored to normal"
