#!/usr/bin/env bash
# ShadowCypher launcher — runs the Python app from /opt/shadowcypher
export PYTHONPATH=/opt/shadowcypher
exec python3 -m shadowcypher.app "$@"
