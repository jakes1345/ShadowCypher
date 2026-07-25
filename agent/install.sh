#!/usr/bin/env bash
# ShadowCypher Guardian Agent — one-liner installer
# Usage: curl -sSL https://shadowcypher.site/agent/install.sh | bash
set -euo pipefail

CYAN='\033[38;2;0;224;164m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

INSTALL_DIR="$HOME/.local/share/shadowcypher-agent"
BIN_DIR="$HOME/.local/bin"
AGENT_URL="https://shadowcypher.site/agent/shadowcypher_agent.py"

echo -e "\n${CYAN}${BOLD}ShadowCypher Guardian Agent${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"

# ── 1. Python check ──────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[!] python3 not found"
    if command -v apt-get &>/dev/null; then
        echo "[*] installing python3..."
        sudo apt-get install -y python3 python3-venv
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3
    else
        echo "[!] install Python 3.9+ and re-run"
        exit 1
    fi
fi

PY="$(command -v python3)"
PY_VER="$("$PY" -c 'import sys; print(sys.version_info[:2] >= (3,9))')"
if [ "$PY_VER" != "True" ]; then
    echo "[!] Python 3.9+ required (found $("$PY" --version))"
    exit 1
fi
echo "  Python:   $("$PY" --version)"

# ── 2. Download agent ────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR" "$BIN_DIR"
echo "[*] Downloading agent to $INSTALL_DIR..."
curl -sSL "$AGENT_URL" -o "$INSTALL_DIR/shadowcypher_agent.py"
chmod +x "$INSTALL_DIR/shadowcypher_agent.py"

# ── 3. Create venv and install deps ─────────────────────────────────────────
echo "[*] Setting up Python environment..."
"$PY" -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install --quiet requests

# ── 4. Write wrapper script ──────────────────────────────────────────────────
cat > "$INSTALL_DIR/shadow-agent" <<WRAPPER
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/shadowcypher_agent.py" "\$@"
WRAPPER
chmod +x "$INSTALL_DIR/shadow-agent"

# Symlink to ~/. local/bin so it's in PATH
ln -sf "$INSTALL_DIR/shadow-agent" "$BIN_DIR/shadow-agent"

# Ensure ~/. local/bin is in PATH for this session
export PATH="$BIN_DIR:$PATH"

# ── 5. Configure ─────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}Configuration${RESET}"
echo -e "${DIM}Get your API key at: https://shadowcypher.site → Account → API Key${RESET}"
echo ""
"$INSTALL_DIR/shadow-agent" init

# ── 6. Install systemd service (if available) ────────────────────────────────
echo ""
if command -v systemctl &>/dev/null && systemctl --user status &>/dev/null 2>&1; then
    echo "[*] Installing Guardian as a persistent system service..."
    "$INSTALL_DIR/shadow-agent" install-service
else
    echo "[*] systemd not available — run manually:"
    echo "    shadow-agent run"
fi

# ── 7. Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}✓ Guardian Agent installed${RESET}"
echo ""
echo "  Commands:"
echo "    shadow-agent status            # check daemon status"
echo "    shadow-agent once              # run a single scan"
echo "    shadow-agent uninstall-service # remove daemon"
echo ""
echo -e "${DIM}Add $BIN_DIR to your PATH if not already there:${RESET}"
echo "    echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
echo ""
