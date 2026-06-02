#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
APP_NAME="shadowcypher"
APP_TITLE="ShadowCypher"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

echo "ShadowCypher native installer"
echo ""

echo "[1/6] Dependencies..."
MISSING=""
for dep in gcc pkg-config; do
    command -v "$dep" &>/dev/null || MISSING="$MISSING $dep"
done
pkg-config --exists gtk+-3.0 2>/dev/null || MISSING="$MISSING libgtk-3-dev"

if [ -n "$MISSING" ]; then
    echo "Missing:$MISSING"
    echo "Install: sudo apt install$MISSING"
    exit 1
fi

echo "[2/6] Build..."
cd "$SCRIPT_DIR"
make clean 2>/dev/null || true
make

echo "[3/6] Install binary -> $BIN_DIR"
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "Tip: add ~/.local/bin to PATH in ~/.bashrc"
fi

echo "[4/6] Icons..."
for size in 16 24 32 48 64 128 256; do
    dir="$ICON_DIR/${size}x${size}/apps"
    mkdir -p "$dir"
    [ -f "$SCRIPT_DIR/icons/$APP_NAME-${size}.png" ] && \
        cp "$SCRIPT_DIR/icons/$APP_NAME-${size}.png" "$dir/$APP_NAME.png"
done
mkdir -p "$ICON_DIR/scalable/apps"
[ -f "$SCRIPT_DIR/icon.svg" ] && cp "$SCRIPT_DIR/icon.svg" "$ICON_DIR/scalable/apps/$APP_NAME.svg"
gtk-update-icon-cache "$ICON_DIR" 2>/dev/null || true

echo "[5/6] Desktop entry..."
mkdir -p "$APP_DIR"
cat > "$APP_DIR/$APP_NAME.desktop" << DEOF
[Desktop Entry]
Name=$APP_TITLE
GenericName=Network admin
Comment=GTK system and network tools
Exec=$BIN_DIR/$APP_NAME
Path=$PROJECT_DIR
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=Network;System;Security;Monitor;
Keywords=network;firewall;system;gtk;
StartupNotify=true
StartupWMClass=$APP_TITLE
Actions=terminal;

[Desktop Action terminal]
Name=Terminal in project
Exec=x-terminal-emulator -e "cd \"$PROJECT_DIR\" && exec bash"
DEOF
chmod +x "$APP_DIR/$APP_NAME.desktop"

if [ -d "$DESKTOP_DIR" ]; then
    cp "$APP_DIR/$APP_NAME.desktop" "$DESKTOP_DIR/$APP_NAME.desktop"
    chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"
    gio set "$DESKTOP_DIR/$APP_NAME.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "[6/6] Done. Run: $BIN_DIR/$APP_NAME"
echo "Optional HTTP API (separate): cd $PROJECT_DIR && npm install && npm start"
echo ""
