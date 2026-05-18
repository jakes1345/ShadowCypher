#!/usr/bin/env bash
# dev — full development environment, normal networking
set -e
systemctl stop tor 2>/dev/null || true
systemctl start docker 2>/dev/null || true
systemctl start dnscrypt-proxy 2>/dev/null || true
nft flush ruleset
ufw default deny incoming
ufw default allow outgoing
