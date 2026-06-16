#!/usr/bin/env bash
# Restore normal outbound networking after ghost/privacy lockdown modes.
# Sourced by normal/dev/pentest/undercover apply.sh — do not execute directly.

shadowos_network_open() {
    systemctl stop tor 2>/dev/null || true
    systemctl start NetworkManager 2>/dev/null || true
    conntrack -F 2>/dev/null || true
    nft flush ruleset 2>/dev/null || true
    ufw default deny incoming
    ufw default allow outgoing
    ufw --force enable 2>/dev/null || true
    systemctl restart NetworkManager 2>/dev/null || true
    if systemctl is-enabled --quiet dnscrypt-proxy 2>/dev/null; then
        systemctl restart dnscrypt-proxy 2>/dev/null || true
    fi
}
