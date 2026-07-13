#!/usr/bin/env bash
# ==============================================================================
# SHADOWCYPHER // AUTOMATED SYSTEM HYGIENE & LOG SANITIZATION
# ==============================================================================
# Safely clears temporary session data, application logs, and shell history
# to ensure local operational security.

set -euo pipefail

# Resolve repo root from script location — works regardless of install path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# --- Typography & Colors ---
CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_succ() { echo -e "${GREEN}[OK]${NC}   $1"; }
log_err()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

if [ "$EUID" -ne 0 ]; then
    log_err "This script requires root privileges. Please run with sudo."
fi

echo ""
echo -e "=============================================================================="
echo -e " SHADOWCYPHER // SYSTEM HYGIENE PROTOCOL"
echo -e "==============================================================================\n"

# 1. Wipe Application Logs
log_info "Sanitizing application log directory..."
rm -rf "${REPO_DIR}/logs/"*.log 2>/dev/null || true
rm -rf /tmp/shadowcypher_* 2>/dev/null || true
log_succ "Application logs cleared."

# 2. Kernel Memory Flush
log_info "Initiating kernel memory drop caches (dentries and inodes)..."
sync; echo 3 | tee /proc/sys/vm/drop_caches > /dev/null
log_succ "Kernel caches flushed."

# 3. Application State Cleared
log_info "Clearing local peer connectivity state..."
rm -f "${REPO_DIR}/shadowcypher/native/relay/peers.json" 2>/dev/null || true
log_succ "Peer states cleared."

# 4. Clear Shell History
log_info "Truncating user shell histories..."
if [ -n "${SUDO_USER:-}" ]; then
    USER_HOME=$(eval echo "~$SUDO_USER")
    cat /dev/null > "$USER_HOME/.bash_history" 2>/dev/null || true
    cat /dev/null > "$USER_HOME/.python_history" 2>/dev/null || true
fi
# Root history
cat /dev/null > /root/.bash_history 2>/dev/null || true
cat /dev/null > /root/.python_history 2>/dev/null || true
history -c || true
log_succ "Shell histories truncated."

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}[SUCCESS] System Hygiene Protocol Complete.${NC}"
echo -e "All session artifacts and temporary application logs have been sanitized."
echo -e "${GREEN}==============================================================================${NC}"
