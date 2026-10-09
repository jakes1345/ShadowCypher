#!/usr/bin/env bash
# Restore normal outbound networking after ghost/privacy lockdown modes.
# Sourced by normal/dev/pentest/undercover apply.sh — do not execute directly.

shadowos_network_open() {
    systemctl stop tor 2>/dev/null || true
    systemctl start NetworkManager 2>/dev/null || true
    conntrack -F 2>/dev/null || true
    # Remove only our mode-specific overlay tables; then reload the base firewall.
    # Never flush the entire ruleset — that leaves the machine with zero protection.
    nft delete table inet anonsurf 2>/dev/null || true
    nft delete table ip6 anonsurf_v6 2>/dev/null || true
    nft delete table inet shadow_privacy 2>/dev/null || true
    nft delete table ip6 shadow_ipv6_block 2>/dev/null || true
    nft -f /etc/nftables.conf
    systemctl restart NetworkManager 2>/dev/null || true
    if systemctl is-enabled --quiet dnscrypt-proxy 2>/dev/null; then
        systemctl restart dnscrypt-proxy 2>/dev/null || true
    fi
}
