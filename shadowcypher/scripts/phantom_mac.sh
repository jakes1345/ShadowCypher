#!/bin/bash
# ── PHANTOM-MAC v1.0 — Sovereign Hardware Masking ─────────────────
# This script randomizes the MAC address of the tactical interface 
# to prevent ISP-level device tracking and fingerprinting.

INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

if [ -z "$INTERFACE" ]; then
    echo -e "\033[0;31m[!] FATAL: No active tactical interface detected.\033[0m"
    exit 1
fi

echo -e "\033[0;36m[GHOST] INTERFACE_IDENTIFIED:\033[0m $INTERFACE"
echo -e "\033[0;36m[GHOST] CURRENT_MAC:\033[0m $(cat /sys/class/net/$INTERFACE/address)"

# 1. Bring interface down
sudo ip link set dev $INTERFACE down

# 2. Randomize MAC (Using a generic 'Intel/Apple' prefix to blend in)
# Common OUI: 00:0c:29 (VMWare), 00:03:93 (Apple), 00:50:56 (VMWare)
NEW_MAC=$(printf '00:60:2f:%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))

sudo ip link set dev $INTERFACE address $NEW_MAC

# 3. Bring interface up
sudo ip link set dev $INTERFACE up

echo -e "\033[0;32m[GHOST] SOVEREIGN_MAC_APPLIED:\033[0m $NEW_MAC"
echo -e "\033[0;32m[GHOST] You are now invisible to hardware tracking.\033[0m"
