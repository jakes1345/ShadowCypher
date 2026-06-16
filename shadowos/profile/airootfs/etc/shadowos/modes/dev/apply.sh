#!/usr/bin/env bash
# dev — full development environment, normal networking
set -e
# shellcheck source=/dev/null
source /etc/shadowos/modes/_network_open.sh
shadowos_network_open
systemctl start docker 2>/dev/null || true
