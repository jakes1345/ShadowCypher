#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ShadowCLI Launcher — Sovereign Tactical Bridge v3
# Handles environment validation, dependency checks, and
# both GUI and headless (ShadowScript REPL) launch modes.
# ═══════════════════════════════════════════════════════════

set -euo pipefail

# Resolve script directory (works with symlinks)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PYTHON_BIN="$DIR/venv/bin/python3"

# Fallback to system python
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 2>/dev/null || echo '')"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo -e "\033[1;31m[FATAL] Python3 not found. Install python3 or create a venv.\033[0m"
    exit 1
fi

# Set tactical environment
export PYTHONPATH="$DIR:${PYTHONPATH:-}"

# ── Parse Arguments ──
MODE="gui"
SCRIPT_FILE=""

show_help() {
    echo ""
    echo -e "\033[1;36m  SHADOWCYPHER APEX — Sovereign Tactical Platform\033[0m"
    echo ""
    echo "  Usage: ./shadow_cli.sh [OPTIONS]"
    echo ""
    echo "  Options:"
    echo "    --gui           Launch the full GTK interface (default)"
    echo "    --repl          Launch the ShadowScript interactive shell"
    echo "    --run <file>    Execute a .shadow script"
    echo "    --check         Run UI integrity verification"
    echo "    --gauntlet      Spawn the local battleground victim"
    echo "    --help          Show this help"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --gui) MODE="gui"; shift ;;
        --repl) MODE="repl"; shift ;;
        --run)
            MODE="script"
            SCRIPT_FILE="${2:-}"
            if [ -z "$SCRIPT_FILE" ]; then
                echo "[!] --run requires a .shadow file path"
                exit 1
            fi
            shift 2 ;;
        --check) MODE="check"; shift ;;
        --gauntlet) MODE="gauntlet"; shift ;;
        --help|-h) show_help; exit 0 ;;
        *) echo "[!] Unknown option: $1"; show_help; exit 1 ;;
    esac
done

# ── Banner ──
echo -e "\033[1;35m"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   SHADOWCYPHER APEX — SOVEREIGN ENGINE    ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "\033[0m"

# ── Dependency Checks ──
echo -e "\033[1;33m[*] Environment Validation...\033[0m"

# Check GTK (for GUI mode)
if [ "$MODE" = "gui" ]; then
    if ! $PYTHON_BIN -c "import gi; gi.require_version('Gtk','3.0')" 2>/dev/null; then
        echo -e "\033[31m[!] GTK3 not available. Install: sudo apt install python3-gi gir1.2-gtk-3.0\033[0m"
        exit 1
    fi
    echo -e "\033[32m  [+] GTK 3.0: OK\033[0m"
fi

# Check Ollama (optional — don't hard-fail)
if curl -s --max-time 2 http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo -e "\033[32m  [+] Neural Core (Ollama): ONLINE\033[0m"
else
    echo -e "\033[33m  [~] Neural Core (Ollama): OFFLINE (AI features limited)\033[0m"
fi

# Check crypto
if $PYTHON_BIN -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM" 2>/dev/null; then
    echo -e "\033[32m  [+] Cryptography: AES-256-GCM ready\033[0m"
else
    echo -e "\033[33m  [~] Cryptography: Missing (pip install cryptography)\033[0m"
fi

echo ""

# ── Launch ──
case $MODE in
    gui)
        echo -e "\033[1;36m[*] Engaging GTK Interface...\033[0m"
        exec $PYTHON_BIN -m shadowcypher.app "$@"
        ;;
    repl)
        echo -e "\033[1;36m[*] Entering ShadowScript REPL...\033[0m"
        exec $PYTHON_BIN -m shadowcypher.compiler.interpreter
        ;;
    script)
        echo -e "\033[1;36m[*] Executing: $SCRIPT_FILE\033[0m"
        exec $PYTHON_BIN -m shadowcypher.compiler.interpreter "$SCRIPT_FILE"
        ;;
    check)
        echo -e "\033[1;36m[*] Running UI Integrity Check...\033[0m"
        exec $PYTHON_BIN "$DIR/shadowcypher/scripts/ui_integrity.py"
        ;;
    gauntlet)
        echo -e "\033[1;36m[*] Spawning Gauntlet Battleground...\033[0m"
        exec $PYTHON_BIN "$DIR/shadowcypher/shadow_test/gauntlet/gauntlet_victim.py"
        ;;
esac
