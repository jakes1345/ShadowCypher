#!/usr/bin/env bash
# dev revert — stop docker that was started by apply.sh
set -e

systemctl stop docker 2>/dev/null || true
echo "  ✓ dev: docker stopped"
