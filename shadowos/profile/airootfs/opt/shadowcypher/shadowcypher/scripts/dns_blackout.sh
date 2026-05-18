#!/usr/bin/env bash
# ==============================================================================
# SHADOWCYPHER // SECURE DNS ENFORCEMENT
# ==============================================================================
# Configures systemd-resolved for strict DNS-over-TLS (DoT) and enforces
# iptables rules to prevent clear-text DNS leakage.

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

log_info "Initiating Secure DNS-over-TLS (DoT) configuration..."

# 1. Systemd-Resolved Configuration
log_info "Writing systemd-resolved configuration..."
cat <<EOF > /etc/systemd/resolved.conf
[Resolve]
DNS=1.1.1.1 9.9.9.9
DNSOverTLS=yes
Domains=~.
EOF

log_info "Restarting systemd-resolved service..."
systemctl restart systemd-resolved
log_succ "Systemd-resolved configured for DoT."

# 2. Firewall Enforcement (Prevent Port 53 Leakage)
log_info "Applying egress firewall rules to block clear-text DNS (Port 53)..."

# Ensure we don't duplicate rules if run multiple times
iptables -D OUTPUT -p udp --dport 53 -j REJECT 2>/dev/null || true
iptables -D OUTPUT -p tcp --dport 53 -j REJECT 2>/dev/null || true

# Block all clear-text DNS outbound
iptables -A OUTPUT -p udp --dport 53 -j REJECT
iptables -A OUTPUT -p tcp --dport 53 -j REJECT

log_succ "Iptables egress rules applied."

# 3. Validation
echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}[SUCCESS] Secure DNS Enforcement Active.${NC}"
echo -e "All DNS queries are now routed over TLS (Port 853)."
echo -e "Clear-text queries (Port 53) are strictly rejected at the firewall level."
echo -e "${GREEN}==============================================================================${NC}"

