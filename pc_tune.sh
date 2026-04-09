#!/bin/bash
# --- SHADOWCYPHER APEX PERFORMANCE TUNER ---
# Optimizing for Gaming, Programming, and System Smoothness.

echo "🚀 Initiating Apex Tuning Sequence..."

# 1. System Responsiveness (requires sudo)
echo "[*] Tuning Kernel parameters..."
sudo sysctl -w vm.swappiness=10
sudo sysctl -w vm.vfs_cache_pressure=50

# 2. Disk & Memory Hygiene
echo "[*] Cleaning build caches..."
rm -rf ~/.cache/pip/*

# 3. NVIDIA Screen Tearing Fix (Force Full Composition Pipeline)
echo "[*] Applying NVIDIA display optimizations..."
if command -v nvidia-settings &> /dev/null; then
    nvidia-settings --assign CurrentMetaMode="nvidia-auto-select +0+0 {ForceFullCompositionPipeline=On}"
fi

# 4. RAM Defragmentation
echo "[*] Clearing inactive memory caches..."
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# 5. Gaming Mode Check
if command -v gamemoded &> /dev/null; then
    echo "[*] GameMode is ready. Use 'gamemoderun <app>' to launch games."
fi

echo "✅ Optimization Sequence Complete."
