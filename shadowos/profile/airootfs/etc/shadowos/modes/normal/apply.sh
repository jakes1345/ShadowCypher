#!/usr/bin/env bash
# normal — default daily-driver mode (full internet, encrypted DNS optional)
set -e
# shellcheck source=/dev/null
source /etc/shadowos/modes/_network_open.sh
shadowos_network_open
