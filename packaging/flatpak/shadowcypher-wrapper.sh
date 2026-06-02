#!/usr/bin/env bash
export PYTHONPATH=/app/lib/python3/site-packages
export SUDO_ASKPASS=/app/share/shadowcypher/native/shadowcypher-askpass
exec python3 -m shadowcypher.app "$@"
