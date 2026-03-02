#!/bin/bash
APP_NAME="shadowcypher"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

echo "Removing ShadowCypher..."
rm -f "$BIN_DIR/$APP_NAME"
rm -f "$APP_DIR/$APP_NAME.desktop"
rm -f "$DESKTOP_DIR/$APP_NAME.desktop"
for size in 16 24 32 48 64 128 256; do
    rm -f "$ICON_DIR/${size}x${size}/apps/$APP_NAME.png"
done
rm -f "$ICON_DIR/scalable/apps/$APP_NAME.svg"
gtk-update-icon-cache "$ICON_DIR" 2>/dev/null || true
echo "ShadowCypher uninstalled."
