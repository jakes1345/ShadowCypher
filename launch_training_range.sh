#!/bin/bash
# ShadowCypher Training Range Launcher
echo "[*] Initializing Training Range..."
pip install flask --user > /dev/null 2>&1
python3 training_lab/app.py
