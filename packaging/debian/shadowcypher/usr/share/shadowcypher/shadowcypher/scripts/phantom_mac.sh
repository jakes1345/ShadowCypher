#!/usr/bin/env bash
# ==============================================================================
# SHADOWCYPHER // HARDWARE ADDRESS RANDOMIZATION
# ==============================================================================
# Randomizes the MAC address of the default network interface to prevent
# layer-2 hardware fingerprinting.

set -euo pipefail

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

INTERFACE=$(ip route | awk '/default/ {print $5}' | head -n1)

if [ -z "$INTERFACE" ]; then
    log_err "No active default network interface detected."
fi

log_info "Default interface identified: $INTERFACE"
log_info "Current hardware address: $(cat /sys/class/net/$INTERFACE/address)"

# 1. Bring interface down
log_info "Bringing interface down for address rotation..."
ip link set dev "$INTERFACE" down

# 2. Randomize MAC (Using a generic OUI prefix)
NEW_MAC=$(printf '00:60:2f:%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))
ip link set dev "$INTERFACE" address "$NEW_MAC"

# 3. Bring interface up
ip link set dev "$INTERFACE" up

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}[SUCCESS] Hardware address successfully randomized.${NC}"
echo -e "New MAC Address: ${CYAN}$NEW_MAC${NC}"
echo -e "Layer-2 hardware tracking mitigated for interface: $INTERFACE"
echo -e "${GREEN}==============================================================================${NC}"
