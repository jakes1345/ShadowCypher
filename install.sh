#!/bin/bash
# ShadowCypher: Installation Engine (V20)
# Cross-platform installer for Linux (Debian/Ubuntu, Arch), macOS, and Windows/WSL

set -e

echo "[SHADOW] INITIATING_TACTICAL_DEPLOYMENT..."
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ICON_PATH="$APP_DIR/assets/icon.png"
DESKTOP_FILE="$HOME/.local/share/applications/shadowcypher.desktop"

# ── 1. Python Dependencies ──
echo "[SHADOW] Installing Python dependencies..."
if [ -d "$APP_DIR/venv" ]; then
    echo "[SHADOW] Using existing virtual environment..."
    source "$APP_DIR/venv/bin/activate"
    pip install -r "$APP_DIR/requirements.txt" -q
elif command -v python3 &>/dev/null; then
    # Try venv first (recommended)
    python3 -m venv "$APP_DIR/venv" 2>/dev/null && {
        source "$APP_DIR/venv/bin/activate"
        pip install -r "$APP_DIR/requirements.txt" -q
        echo "[SHADOW] Virtual environment created at $APP_DIR/venv"
    } || {
        # Fallback: install globally
        pip3 install -r "$APP_DIR/requirements.txt" --user -q 2>/dev/null || \
        pip3 install -r "$APP_DIR/requirements.txt" -q
    }
fi

# ── 2. System Dependencies (Linux only) ──
if [ "$(uname)" = "Linux" ]; then
    echo "[SHADOW] Installing system packages..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
            libcairo2-dev nmap ffuf wget unzip curl git 2>/dev/null || true
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python-gobject gtk3 cairo nmap 2>/dev/null || true
    fi
fi

# ── 3. Optional Arsenal ──
echo "[SHADOW] Checking optional security tools..."
if [ "$(uname)" = "Linux" ]; then
    if [ ! -d "/opt/Responder" ]; then
        echo "[SHADOW] Installing Responder..."
        sudo git clone https://github.com/SpiderLabs/Responder.git /opt/Responder 2>/dev/null || true
    fi
    if ! command -v nuclei &>/dev/null; then
        echo "[SHADOW] Installing Nuclei..."
        NUCLEI_VER="3.2.0"
        wget -q "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VER}/nuclei_${NUCLEI_VER}_linux_amd64.zip" -O /tmp/nuclei.zip 2>/dev/null && {
            sudo unzip -o /tmp/nuclei.zip -d /usr/local/bin/ nuclei
            rm -f /tmp/nuclei.zip
        } || echo "[SHADOW] Nuclei install skipped (download failed)"
    fi
fi

# ── 4. Create Required Directories ──
echo "[SHADOW] Creating project directories..."
mkdir -p "$APP_DIR/wordlists" "$APP_DIR/findings" "$APP_DIR/reports" \
         "$APP_DIR/tickets" "$APP_DIR/logs" "$APP_DIR/tools"

# ── 5. Universal Launcher ──
echo "[SHADOW] Creating launcher..."
cat <<LAUNCHER > "$APP_DIR/run.sh"
#!/bin/bash
cd "$APP_DIR"
# Auto-detect display server
if [ -n "\$WAYLAND_DISPLAY" ]; then
    export GDK_BACKEND=wayland
elif [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi
# Use venv if available
[ -d "$APP_DIR/venv" ] && source "$APP_DIR/venv/bin/activate"
python3 -m shadowcypher.app "\$@"
LAUNCHER
chmod +x "$APP_DIR/run.sh"

# ── 6. System-wide CLI command ──
echo "[SHADOW] Installing 'shadowcypher' command..."
sudo ln -sf "$APP_DIR/run.sh" /usr/local/bin/shadowcypher 2>/dev/null || true

# ── 7. Desktop Entry (Linux only) ──
if [ "$(uname)" = "Linux" ]; then
    echo "[SHADOW] Registering desktop application..."
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    cat <<DESKTOP > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=ShadowCypher
Comment=Autonomous Offensive Security Platform
Exec=$APP_DIR/run.sh
Icon=${ICON_PATH:-security-high}
Categories=Development;Security;System;
Terminal=false
StartupNotify=true
DESKTOP
    chmod +x "$DESKTOP_FILE"
    update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  SHADOWCYPHER DEPLOYED SUCCESSFULLY          ║"
echo "║                                              ║"
echo "║  Launch: shadowcypher                        ║"
echo "║  Or:     ./run.sh                            ║"
echo "║  Or:     python3 -m shadowcypher.app         ║"
echo "╚══════════════════════════════════════════════╝"
