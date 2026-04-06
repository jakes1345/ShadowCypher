#!/bin/bash
cd "/home/jack/ShadowCypher"
source venv/bin/activate
DISPLAY=:0 python3 -m shadowcypher.app
