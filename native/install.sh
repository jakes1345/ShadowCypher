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

echo "╔══════════════════════════════════════╗"
echo "║   ShadowCypher Desktop Installer     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check dependencies
echo "[1/6] Checking dependencies..."
MISSING=""
for dep in gcc node npm pkg-config; do
    if ! command -v "$dep" &>/dev/null; then
        MISSING="$MISSING $dep"
    fi
done
pkg-config --exists gtk+-3.0 2>/dev/null || MISSING="$MISSING libgtk-3-dev"
pkg-config --exists webkit2gtk-4.1 2>/dev/null || MISSING="$MISSING libwebkit2gtk-4.1-dev"

if [ -n "$MISSING" ]; then
    echo "  MISSING:$MISSING"
    echo "  Install with: sudo apt install$MISSING"
    exit 1
fi
echo "  All dependencies found."

# Compile
echo "[2/6] Compiling native binary..."
cd "$SCRIPT_DIR"
make clean 2>/dev/null || true
make
echo "  Binary compiled: $SCRIPT_DIR/$APP_NAME"

# Install binary
echo "[3/6] Installing binary..."
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"
echo "  Installed to $BIN_DIR/$APP_NAME"

# Make sure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "  NOTE: $HOME/.local/bin is not in your PATH."
    echo "  Add this to your ~/.bashrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

# Install icons
echo "[4/6] Installing icons..."
for size in 16 24 32 48 64 128 256; do
    dir="$ICON_DIR/${size}x${size}/apps"
    mkdir -p "$dir"
    if [ -f "$SCRIPT_DIR/icons/$APP_NAME-${size}.png" ]; then
        cp "$SCRIPT_DIR/icons/$APP_NAME-${size}.png" "$dir/$APP_NAME.png"
    fi
done
# Also install SVG for scalable
mkdir -p "$ICON_DIR/scalable/apps"
cp "$SCRIPT_DIR/icon.svg" "$ICON_DIR/scalable/apps/$APP_NAME.svg"
# Update icon cache
gtk-update-icon-cache "$ICON_DIR" 2>/dev/null || true
echo "  Icons installed to $ICON_DIR"

# Create .desktop file
echo "[5/6] Creating desktop entry..."
mkdir -p "$APP_DIR"
cat > "$APP_DIR/$APP_NAME.desktop" << DEOF
[Desktop Entry]
Name=$APP_TITLE
GenericName=Network Admin Panel
Comment=Intel-grade router admin, offensive security, and network operations
Exec=$BIN_DIR/$APP_NAME
Path=$PROJECT_DIR
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=Network;System;Security;Monitor;
Keywords=router;admin;network;firewall;security;hacking;pentest;opsec;
StartupNotify=true
StartupWMClass=$APP_TITLE
Actions=terminal;kill-server;

[Desktop Action terminal]
Name=Open Terminal Only
Exec=x-terminal-emulator -e "cd $PROJECT_DIR && node server.js"

[Desktop Action kill-server]
Name=Stop Server
Exec=bash -c "pkill -f 'node.*server.js' && notify-send '$APP_TITLE' 'Server stopped'"
DEOF
chmod +x "$APP_DIR/$APP_NAME.desktop"

# Also put on desktop
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APP_DIR/$APP_NAME.desktop" "$DESKTOP_DIR/$APP_NAME.desktop"
    chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"
    # Trust the desktop file (Cinnamon)
    gio set "$DESKTOP_DIR/$APP_NAME.desktop" metadata::trusted true 2>/dev/null || true
    echo "  Desktop shortcut created on $DESKTOP_DIR"
fi
echo "  Desktop entry installed to $APP_DIR"

# Verify
echo "[6/6] Verifying installation..."
echo ""
echo "  Binary:   $BIN_DIR/$APP_NAME"
echo "  Desktop:  $APP_DIR/$APP_NAME.desktop"
echo "  Icon:     $ICON_DIR/scalable/apps/$APP_NAME.svg"
echo "  Project:  $PROJECT_DIR"
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Installation complete!             ║"
echo "║                                      ║"
echo "║   Launch from:                       ║"
echo "║   • App Menu → ShadowCypher          ║"
echo "║   • Desktop shortcut                 ║"
echo "║   • Terminal: shadowcypher            ║"
echo "╚══════════════════════════════════════╝"
