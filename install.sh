#!/bin/bash
# ShadowCypher: Apex Deployment Engine (V22)
# Google-grade tactical installation for high-fidelity security operations.

set -e

# ── 0. Initialization ──
echo -e "\033[1;36m[SHADOW] INITIATING_APEX_DEPLOYMENT_V22...\033[0m"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ICON_PATH="$APP_DIR/native/icons/shadowcypher-256.png"
LOCAL_BIN="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/shadowcypher.desktop"

mkdir -p "$LOCAL_BIN" "$DESKTOP_DIR"
mkdir -p "$APP_DIR/wordlists" "$APP_DIR/findings" "$APP_DIR/reports" \
         "$APP_DIR/logs" "$APP_DIR/tools"

# ── 1. Dependency Synchronization ──
echo "[SHADOW] Synchronizing enterprise ecosystem..."
if command -v python3 &>/dev/null; then
    if [ ! -d "$APP_DIR/venv" ]; then
        python3 -m venv "$APP_DIR/venv"
    fi
    source "$APP_DIR/venv/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$APP_DIR/requirements.txt" -q
    echo "[SHADOW] Ecosystem stabilized."
else
    echo -e "\033[1;31m[ERROR] Python 3 not found. Deployment critical failure.\033[0m"
    exit 1
fi

# ── 2. Pre-Flight Audit (Overlord Protocol) ──
echo "[SHADOW] Engaging Apex Overlord for pre-flight stability audit..."
source "$APP_DIR/venv/bin/activate"
python3 "$APP_DIR/shadowcypher_overlord_audit.py" || { echo "[ERROR] System instability detected. Aborting."; exit 1; }

# ── 3. High-Fidelity Launcher ──
echo "[SHADOW] Engineering tactical launcher..."
cat <<LAUNCHER > "$APP_DIR/shadowcypher_launch"
#!/bin/bash
# ShadowCypher Universal Entry Point
export PATH="\$PATH:$LOCAL_BIN:$APP_DIR/tools"
cd "$APP_DIR"

# Wavelet & GUI Synchronization
if [ -n "\$WAYLAND_DISPLAY" ]; then
    export GDK_BACKEND=wayland
elif [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi

source "$APP_DIR/venv/bin/activate"
python3 -m shadowcypher.app "\$@"
LAUNCHER
chmod +x "$APP_DIR/shadowcypher_launch"
ln -sf "$APP_DIR/shadowcypher_launch" "$LOCAL_BIN/shadowcypher"

# ── 4. Mainframe Identity (Desktop) ──
echo "[SHADOW] Registering Premium Identity..."
cat <<DESKTOP > "$DESKTOP_FILE"
[Desktop Entry]
Version=3.0
Type=Application
Name=ShadowCypher
GenericName=Autonomous SIGINT Platform
Comment=Enterprise-grade offensive security suite with Wavelet Pulse detection.
Exec=$LOCAL_BIN/shadowcypher
Icon=$ICON_PATH
Path=$APP_DIR
Terminal=false
Categories=System;Security;Network;
Keywords=hacking;security;sigint;pulse;ai;matrix;
StartupNotify=true
StartupWMClass=org.shadowcypher.ShadowCypher
DESKTOP
chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# ── 5. Deployment Report ──
echo -e "\n\033[1;32m┌────────────────────────────────────────────────────────────┐"
echo "│  SHADOWCYPHER APEX DEPLOYMENT COMPLETE (V22)               │"
echo "├────────────────────────────────────────────────────────────┤"
echo "│                                                            │"
echo "│  [ENTRY]    shadowcypher                                   │"
echo "│  [ENGINE]   V3 Autonomous (ShadowPulse SIGINT Active)      │"
echo "│  [PATH]     $LOCAL_BIN                                     │"
echo "│                                                            │"
echo "└────────────────────────────────────────────────────────────┘\033[0m"
echo "[SHADOW] SYSTEM_NOMINAL. STANDING BY FOR COMMAND."
