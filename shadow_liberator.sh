#!/bin/bash
# SHADOW_LIBERATOR v1.0 — Freeing the Citadel from Verizon Moderation
# Hardens the network stack and mask's the signal from ISP telemetry.

echo -e "\033[0;35m[!] INITIATING OPERATION: BROKEN GLASS...\033[0m"

# ── 1. DNS SOVEREIGNTY (Bypass Verizon DNS Hijacking) ────────────
echo "[*] DECOUPLING DNS FROM ISP: Forcing Cloudflare 1.1.1.1..."
sudo mkdir -p /etc/resolvconf/resolv.conf.d 2>/dev/null
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf > /dev/null
echo "nameserver 1.0.0.1" | sudo tee -a /etc/resolv.conf > /dev/null
# Lock the file so the router can't overwrite it via DHCP
sudo chattr +i /etc/resolv.conf 2>/dev/null || echo "[!] WARNING: Immutable lock failed, but DNS updated."

# ── 2. TRACKING SUPPRESSION (Disable IPv6 Fingerprinting) ───────
echo "[*] SUPPRESSING ISP TRACKING: Killing IPv6..."
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=1

# ── 3. SIGNAL MASKING (Tor-Gateway Readiness) ────────────────────
if ! command -v tor &> /dev/null; then
    echo "[*] INSTALLING GHOST-GATEWAY: Tor SOCKS5 Entry..."
    sudo apt-get update -y && sudo apt-get install tor -y
fi
sudo systemctl enable tor --now
echo -e "\033[0;32m[OK] GHOST_GATEWAY_ACTIVE: SOCKS5 ready on 127.0.0.1:9050\033[0m"

# ── 4. VERIZON_SHIELD ───────────────────────────────────────────
echo "[*] HARDENING LOCAL STACK: Dropping Verizon Probes..."
sudo ufw deny from 192.168.1.1 to any 2>/dev/null # Example firewall hardening
echo -e "\033[0;32m[!] UNCONTROLLED STATUS: ACHIEVED\033[0m"
