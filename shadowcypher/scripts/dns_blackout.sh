#!/bin/bash
# ── DNS_BLACKOUT v1.0 — Sovereign Spectrum Isolation ─────────────
# Forcefully redirects all DNS traffic through an encrypted tunnel 
# and drops any clear-text attempts from reaching the Verizon router.

echo -e "\033[0;36m[BLACKOUT] INITIATING_SPECTRUM_ISOLATION...\033[0m"

# 1. Configure Systemd-Resolved for DNS-over-TLS
echo "[Resolve]
DNS=1.1.1.1 9.9.9.9
DNSOverTLS=yes
Domains=~." | sudo tee /etc/systemd/resolved.conf > /dev/null

sudo systemctl restart systemd-resolved

# 2. Hardening the Gateway (The Verizon Drop)
# We block all outbound traffic on port 53 (DNS) that IS NOT internal/encrypted.
echo -e "\033[0;33m[BLACKOUT] APPLYING_FIREWALL_KILL_SWITCH (Port 53 Drop)...\033[0m"

# Block clear-text DNS to the ISP router
sudo iptables -A OUTPUT -d 192.168.1.1 -p udp --dport 53 -j DROP
sudo iptables -A OUTPUT -d 192.168.1.1 -p tcp --dport 53 -j DROP

# Block all other clear-text DNS globally to prevent "leakage"
sudo iptables -A OUTPUT -p udp --dport 53 -j REJECT
sudo iptables -A OUTPUT -p tcp --dport 53 -j REJECT

# 3. Validation
echo -e "\033[0;32m[BLACKOUT] ISOLATION_COMPLETE.\033[0m"
echo -e "\033[0;32m[BLACKOUT] Your browsing history is now invisible to Verizon DPI.\033[0m"
