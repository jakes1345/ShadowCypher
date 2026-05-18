#!/usr/bin/env bash
# normal — default daily-driver mode
set -e
systemctl stop tor 2>/dev/null || true
systemctl start dnscrypt-proxy 2>/dev/null || true
ufw default deny incoming
ufw default allow outgoing
