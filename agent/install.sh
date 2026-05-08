#!/usr/bin/env bash
# ShadowCypher Guardian Agent — Install Script
# Usage: curl -sSL https://shadowcypher.site/agent/install.sh | bash
set -e

CYAN='\033[1;36m'; GREEN='\033[1;32m'; RED='\033[1;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${CYAN}[shadow]${NC} $1"; }
ok()   { echo -e "${GREEN}[done]${NC}  $1"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $1"; }
fail() { echo -e "${RED}[fail]${NC}  $1"; exit 1; }

echo ""
echo -e "${CYAN}  ╔══════════════════════════════════════╗"
echo -e "  ║   SHADOWCYPHER GUARDIAN AGENT        ║"
echo -e "  ║   Sovereign Network Monitor          ║"
echo -e "  ╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Requirements check ────────────────────────────────────────────────────
log "Checking requirements..."

if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Install it with: sudo apt install python3 (Linux) or brew install python3 (macOS)"
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python $PY_VER detected"

if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
    warn "pip not found — attempting to install..."
    python3 -m ensurepip --upgrade 2>/dev/null || fail "Could not install pip. Install manually: https://pip.pypa.io"
fi

# ── 2. Install Python dependencies ───────────────────────────────────────────
log "Installing dependencies (requests)..."
python3 -m pip install --quiet --upgrade requests 2>/dev/null || \
    pip3 install --quiet --upgrade requests 2>/dev/null || \
    fail "Could not install 'requests'. Try: pip3 install requests"
ok "Dependencies installed"

# ── 3. Download agent script ──────────────────────────────────────────────────
INSTALL_DIR="$HOME/.shadowcypher"
AGENT_PATH="$INSTALL_DIR/shadow-agent.py"
BIN_PATH="/usr/local/bin/shadow-agent"

log "Downloading agent to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"

if command -v curl &>/dev/null; then
    curl -fsSL "https://shadowcypher.site/agent/shadow-agent.py" -o "$AGENT_PATH"
elif command -v wget &>/dev/null; then
    wget -qO "$AGENT_PATH" "https://shadowcypher.site/agent/shadow-agent.py"
else
    fail "curl or wget required to download the agent"
fi

chmod +x "$AGENT_PATH"
ok "Agent downloaded to $AGENT_PATH"

# ── 4. Create wrapper binary ──────────────────────────────────────────────────
log "Installing shadow-agent command..."

WRAPPER="#!/usr/bin/env bash
exec python3 \"$AGENT_PATH\" \"\$@\""

if [ -w /usr/local/bin ]; then
    echo "$WRAPPER" > "$BIN_PATH"
    chmod +x "$BIN_PATH"
    ok "shadow-agent installed to $BIN_PATH"
else
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    echo "$WRAPPER" > "$LOCAL_BIN/shadow-agent"
    chmod +x "$LOCAL_BIN/shadow-agent"
    ok "shadow-agent installed to $LOCAL_BIN/shadow-agent"
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        warn "Add this to your shell profile: export PATH=\"\$PATH:$LOCAL_BIN\""
    fi
    BIN_PATH="$LOCAL_BIN/shadow-agent"
fi

# ── 5. Optional: systemd service ─────────────────────────────────────────────
if command -v systemctl &>/dev/null && [ "$(uname)" = "Linux" ]; then
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"
    cat > "$SERVICE_DIR/shadow-agent.service" << EOF
[Unit]
Description=ShadowCypher Guardian Agent
After=network.target

[Service]
ExecStart=$BIN_PATH run
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
EOF
    ok "Systemd user service written to $SERVICE_DIR/shadow-agent.service"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Installation complete.${NC} Next steps:"
echo ""
echo -e "  ${CYAN}1.${NC} Connect your account:"
echo -e "     ${YELLOW}shadow-agent init${NC}"
echo ""
echo -e "  ${CYAN}2.${NC} Start monitoring:"
echo -e "     ${YELLOW}shadow-agent run${NC}"
echo ""
if command -v systemctl &>/dev/null && [ "$(uname)" = "Linux" ]; then
echo -e "  ${CYAN}3.${NC} Or run as a background service:"
echo -e "     ${YELLOW}systemctl --user enable --now shadow-agent${NC}"
echo ""
fi
echo -e "Your dashboard: ${CYAN}https://shadowcypher.site${NC}"
echo ""
