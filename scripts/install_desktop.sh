#!/usr/bin/env bash
# ShadowCypher - Desktop Integration Script
# This script installs the application icon and creates a desktop entry for the bar and menu.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ICON_NAME="shadowcypher"
APP_NAME="shadowcypher"
APP_DIR="$HOME/.local/share/applications"
ICON_BASE="$HOME/.local/share/icons/hicolor"

echo "[*] ShadowCypher: Integrating with Desktop Environment..."

# 1. Install Icons
echo "[+] Registering icons..."
for size in 16 24 32 48 64 128 256; do
    DIR="$ICON_BASE/${size}x${size}/apps"
    mkdir -p "$DIR"
    if [ -f "$PROJECT_DIR/native/icons/shadowcypher-${size}.png" ]; then
        cp "$PROJECT_DIR/native/icons/shadowcypher-${size}.png" "$DIR/$ICON_NAME.png"
    fi
done

# Scalable icon if exists
mkdir -p "$ICON_BASE/scalable/apps"
if [ -f "$PROJECT_DIR/native/icon.svg" ]; then
    cp "$PROJECT_DIR/native/icon.svg" "$ICON_BASE/scalable/apps/$ICON_NAME.svg"
fi

# Update cache
gtk-update-icon-cache "$ICON_BASE" 2>/dev/null || true

# 2. Create Desktop Entry with Absolute Paths
echo "[+] Creating desktop entry at $APP_DIR/$APP_NAME.desktop..."
mkdir -p "$APP_DIR"

cat > "$APP_DIR/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=3.0
Type=Application
Name=ShadowCypher
GenericName=Tactical Security Suite
Comment=Apex Predator Security HUD with Autonomous AI
Exec=bash -c "cd $PROJECT_DIR && python3 -m shadowcypher.app"
Path=$PROJECT_DIR
Icon=shadowcypher
Terminal=false
Categories=Network;Security;System;Monitor;
Keywords=hacking;security;pentest;matrix;ai;
StartupNotify=true
StartupWMClass=org.shadowcypher.ShadowCypher
EOF

chmod +x "$APP_DIR/$APP_NAME.desktop"

# 3. Create Desktop Shortcut if directory exists
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    echo "[+] Creating desktop shortcut..."
    cp "$APP_DIR/$APP_NAME.desktop" "$DESKTOP_DIR/"
    chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"
    # For GNOME/KDE to trust the launcher
    gio set "$DESKTOP_DIR/$APP_NAME.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "[!] ShadowCypher is now available in your application menu and on the bar."
echo "[!] Search for 'ShadowCypher' in your launcher."
