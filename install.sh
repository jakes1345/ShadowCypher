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

# --- 5. Ollama AI Model Setup ---
log_step "Detecting GPU and selecting AI model tier..."

if command -v ollama &>/dev/null; then
    # Detect VRAM via nvidia-smi or rocm-smi
    VRAM_MB=0
    if command -v nvidia-smi &>/dev/null; then
        VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | awk '{sum+=$1} END{print sum}')
    elif command -v rocm-smi &>/dev/null; then
        VRAM_MB=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i "total" | awk '{sum+=$NF} END{print int(sum/1024/1024)}')
    fi

    VRAM_GB=$(echo "$VRAM_MB / 1024" | bc 2>/dev/null || echo "0")

    if   [ "$VRAM_GB" -ge 22 ] 2>/dev/null; then
        SHADOW_BASE="dolphin-mixtral:8x7b"
        TIER="ELITE (Mixtral 8x7B, ~26GB)"
    elif [ "$VRAM_GB" -ge 12 ] 2>/dev/null; then
        SHADOW_BASE="dolphin-llama3.1:8b-q8_0"
        TIER="PRO (Llama 3.1 8B Q8, ~8.5GB)"
    elif [ "$VRAM_GB" -ge 7 ] 2>/dev/null; then
        SHADOW_BASE="dolphin-llama3:8b"
        TIER="STANDARD (Llama 3 8B, ~4.7GB)"
    else
        SHADOW_BASE="dolphin-mistral:7b"
        TIER="LITE (Mistral 7B, ~3.8GB)"
    fi

    echo -e "  -> VRAM detected:   ${CYAN}${VRAM_GB}GB${NC}"
    echo -e "  -> Model tier:      ${CYAN}${TIER}${NC}"
    echo -e "  -> Pulling base:    ${CYAN}${SHADOW_BASE}${NC}"

    ollama pull "$SHADOW_BASE" || echo -e "${RED}[WARN]${NC} Could not pull $SHADOW_BASE — start Ollama manually and run: ollama pull $SHADOW_BASE"

    # Build shadow fleet on top of the selected base
    if ollama list | grep -q "^$SHADOW_BASE"; then
        log_step "Building ShadowCypher AI fleet..."
        # Patch Modelfiles to use detected base, then create
        for MF in ollama/Modelfile.shadowcypher-ai ollama/Modelfile.shadow-sec ollama/Modelfile.shadow-recon; do
            [ -f "$APP_DIR/$MF" ] || continue
            NAME=$(basename "$MF" | sed 's/Modelfile\.//')
            # shadow-recon uses shadow-coder base, keep that as-is
            if [[ "$NAME" == "shadow-recon" ]]; then
                ollama create "$NAME" -f "$APP_DIR/$MF" && echo -e "  -> Built: ${GREEN}$NAME${NC}" || true
            else
                TMPFILE=$(mktemp)
                sed "s|^FROM .*|FROM $SHADOW_BASE|" "$APP_DIR/$MF" > "$TMPFILE"
                ollama create "$NAME" -f "$TMPFILE" && echo -e "  -> Built: ${GREEN}$NAME${NC}" || true
                rm -f "$TMPFILE"
            fi
        done
        log_succ "ShadowCypher AI fleet deployed on $SHADOW_BASE."
    fi
else
    echo -e "${RED}[WARN]${NC} Ollama not installed. Install from https://ollama.com then re-run install.sh."
fi

# --- 6. Finalization ---
echo ""
log_succ "Deployment finalized successfully."
echo -e "  -> Executable Path: ${CYAN}$LOCAL_BIN/shadowcypher${NC}"
echo -e "  -> Base Directory:  ${CYAN}$APP_DIR${NC}"
echo -e "Ready for execution."
