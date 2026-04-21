#!/usr/bin/env bash
# ==============================================================================
# SHADOWCYPHER // LOCAL ENVIRONMENT BOOTSTRAP
# ==============================================================================
# Automated local installation and dependency resolution script.

set -e

# --- Colors & Logging ---
CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

log_step() { echo -e "${CYAN}[SYSTEM]${NC} $1"; }
log_succ() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_err()  { echo -e "${RED}[FATAL]${NC} $1"; exit 1; }

# --- 0. Initialization ---
log_step "Initializing ShadowCypher local deployment..."

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
ICON_PATH="$APP_DIR/native/icons/shadowcypher-256.png"
LOCAL_BIN="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/shadowcypher.desktop"

mkdir -p "$LOCAL_BIN" "$DESKTOP_DIR"
mkdir -p "$APP_DIR/wordlists" "$APP_DIR/findings" "$APP_DIR/reports" \
         "$APP_DIR/logs" "$APP_DIR/tools"

# --- 1. Python Environment ---
log_step "Resolving Python dependencies and virtual environment..."
if command -v python3 &>/dev/null; then
    if [ ! -d "$APP_DIR/venv" ]; then
        python3 -m venv "$APP_DIR/venv"
    fi
    source "$APP_DIR/venv/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$APP_DIR/requirements.txt" -q
    log_succ "Python ecosystem synchronized."
else
    log_err "Python 3 is required but not found in PATH."
fi

# --- 2. Pre-Flight Audit ---
log_step "Executing system stability audit..."
source "$APP_DIR/venv/bin/activate"
if [ -f "$APP_DIR/shadowcypher_overlord_audit.py" ]; then
    python3 "$APP_DIR/shadowcypher_overlord_audit.py" || log_err "System audit failed. Deployment aborted."
fi

# --- 3. Executable Wrapper ---
log_step "Generating local executable wrapper..."
cat <<LAUNCHER > "$APP_DIR/shadowcypher_launch"
#!/usr/bin/env bash
# ShadowCypher Local Launcher
export PATH="\$PATH:$LOCAL_BIN:$APP_DIR/tools"
cd "$APP_DIR"

# Wayland compatibility enforcement
if [ -n "\$WAYLAND_DISPLAY" ]; then
    export GDK_BACKEND=wayland
elif [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0
fi

source "$APP_DIR/venv/bin/activate"
exec python3 -m shadowcypher.app "\$@"
LAUNCHER

chmod +x "$APP_DIR/shadowcypher_launch"
ln -sf "$APP_DIR/shadowcypher_launch" "$LOCAL_BIN/shadowcypher"

# --- 4. Desktop Integration ---
log_step "Registering desktop environment integration..."
cat <<DESKTOP > "$DESKTOP_FILE"
[Desktop Entry]
Version=3.0
Type=Application
Name=ShadowCypher
GenericName=Tactical Security Suite
Comment=Enterprise-grade offensive security and intelligence platform.
Exec=$LOCAL_BIN/shadowcypher
Icon=$ICON_PATH
Path=$APP_DIR
Terminal=false
Categories=System;Security;Network;
Keywords=security;pentest;sigint;
StartupNotify=true
StartupWMClass=org.shadowcypher.ShadowCypher
DESKTOP

chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# --- 5. Finalization ---
echo ""
log_succ "Deployment finalized successfully."
echo -e "  -> Executable Path: ${CYAN}$LOCAL_BIN/shadowcypher${NC}"
echo -e "  -> Base Directory:  ${CYAN}$APP_DIR${NC}"
echo -e "Ready for execution."
