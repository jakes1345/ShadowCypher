#!/usr/bin/env python3
"""
ShadowCypher Integrity Baseline Updater.
Recalculates SHA-256 hashes for all core modules and updates integrity.json.
Use this after performing verified upgrades to the Citadel.
"""

import hashlib
import json
import os

CORE_PATHS = [
    "shadowcypher/core",
    "shadowcypher/modules",
    "shadowcypher/ui",
    "shadowcypher/ai"
]

def get_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def update_baseline():
    print("[*] Recalculating Integrity Baseline...")
    hashes = {}
    for path in CORE_PATHS:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, os.getcwd())
                    hashes[rel_path] = get_hash(full_path)

    with open("integrity.json", "w") as f:
        json.dump(hashes, f, indent=4)

    print(f"[+] Integrity Baseline Updated: {len(hashes)} files indexed.")

if __name__ == "__main__":
    update_baseline()
