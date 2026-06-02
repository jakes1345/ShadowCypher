#!/usr/bin/env bash
# gaming — auto-tune CPU, GPU, RAM, scheduler for maximum performance
# Reads actual hardware and applies optimal settings. No BIOS required.
set -e
source /etc/shadowos/modes/_network_open.sh
shadowos_network_open

echo "⚡ ShadowOS Gaming Mode — Auto-tuning hardware..."

# ── CPU: detect and set performance governor ─────────────────────────────────
CPU_COUNT=$(nproc)
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
echo "  CPU: $CPU_MODEL ($CPU_COUNT cores)"

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
    echo performance > "$cpu" 2>/dev/null || true
done
echo "  ✓ CPU governor → performance"

# Boost: enable turbo/boost on Intel and AMD
if [[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
    echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
    echo "  ✓ Intel Turbo Boost → enabled"
fi
if [[ -f /sys/devices/system/cpu/cpufreq/boost ]]; then
    echo 1 > /sys/devices/system/cpu/cpufreq/boost
    echo "  ✓ AMD Core Boost → enabled"
fi

# CPU energy preference: performance (works on modern Intel/AMD)
for ep in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
    echo performance > "$ep" 2>/dev/null || true
done

# ── CPU scheduler tuning ─────────────────────────────────────────────────────
# Reduce scheduling latency for low-latency interactive workloads
sysctl -qw kernel.sched_latency_ns=4000000          2>/dev/null || true
sysctl -qw kernel.sched_min_granularity_ns=500000   2>/dev/null || true
sysctl -qw kernel.sched_migration_cost_ns=500000    2>/dev/null || true
sysctl -qw kernel.sched_wakeup_granularity_ns=25000 2>/dev/null || true
echo "  ✓ CFS scheduler → low-latency tuned"

# ── RAM: gaming-optimized ────────────────────────────────────────────────────
sysctl -qw vm.swappiness=10
sysctl -qw vm.dirty_ratio=20
sysctl -qw vm.dirty_background_ratio=5
sysctl -qw vm.vfs_cache_pressure=50
sysctl -qw vm.max_map_count=2147483642  # required by some AAA games (Elden Ring, etc.)
# Transparent hugepages: madvise = apps opt-in (best for gaming)
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true
echo "  ✓ RAM → gaming-optimized (swappiness=10, hugepages=madvise)"

# ── GPU: detect AMD / NVIDIA / Intel ─────────────────────────────────────────
GPU_INFO=$(lspci | grep -i "vga\|3d\|display" || true)
echo "  GPU: $GPU_INFO"

# AMD: set performance power profile
if echo "$GPU_INFO" | grep -qi "amd\|radeon\|amdgpu"; then
    for card in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
        echo high > "$card" 2>/dev/null || true
    done
    for card in /sys/class/drm/card*/device/power_dpm_state; do
        echo performance > "$card" 2>/dev/null || true
    done
    # AMD GPU clock levels — max out if possible
    for card in /sys/class/drm/card*/device/pp_power_profile_mode; do
        # Profile 5 = COMPUTE (high clocks), 4 = VIDEO, 3 = VR, 1 = POWER_SAVING
        echo 5 > "$card" 2>/dev/null || true
    done
    echo "  ✓ AMD GPU → high performance DPM"
fi

# NVIDIA: use nvidia-smi if available
if echo "$GPU_INFO" | grep -qi "nvidia"; then
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --persistence-mode=1 2>/dev/null || true
        nvidia-smi --compute-mode=0 2>/dev/null || true
        # Set power limit to maximum TDP
        MAX_POWER=$(nvidia-smi --query-gpu=power.limit --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
        if [[ -n "$MAX_POWER" ]]; then
            nvidia-smi --power-limit="$MAX_POWER" 2>/dev/null || true
        fi
        echo "  ✓ NVIDIA GPU → persistence on, max power limit"
    fi
fi

# Intel iGPU: set to max frequency
for intel_gpu in /sys/class/drm/card*/gt_max_freq_mhz /sys/class/drm/card*/gt_boost_freq_mhz; do
    [[ -f "$intel_gpu" ]] || continue
    MAX=$(cat "${intel_gpu/boost/max}" 2>/dev/null || cat "$intel_gpu")
    echo "$MAX" > "${intel_gpu/max/min}" 2>/dev/null || true
done

# ── Storage: I/O scheduler tuning ───────────────────────────────────────────
for dev in /sys/block/sd* /sys/block/nvme* /sys/block/vd*; do
    [[ -f "$dev/queue/scheduler" ]] || continue
    # nvme: none (already fast), sata: mq-deadline
    if echo "$dev" | grep -q nvme; then
        echo none > "$dev/queue/scheduler" 2>/dev/null || true
    else
        echo mq-deadline > "$dev/queue/scheduler" 2>/dev/null || true
    fi
    echo 0 > "$dev/queue/add_random" 2>/dev/null || true
    echo 2 > "$dev/queue/rq_affinity" 2>/dev/null || true
done
echo "  ✓ I/O scheduler → tuned per device"

# ── Network: reduce latency ──────────────────────────────────────────────────
sysctl -qw net.core.netdev_max_backlog=16384  2>/dev/null || true
sysctl -qw net.ipv4.tcp_fastopen=3            2>/dev/null || true
sysctl -qw net.ipv4.tcp_mtu_probing=1         2>/dev/null || true
sysctl -qw net.core.rmem_max=16777216         2>/dev/null || true
sysctl -qw net.core.wmem_max=16777216         2>/dev/null || true
echo "  ✓ Network → low-latency gaming tuned"

# ── GameMode daemon ───────────────────────────────────────────────────────────
if command -v gamemoded >/dev/null 2>&1; then
    systemctl --user start gamemoded 2>/dev/null || \
    gamemoded -d 2>/dev/null || true
    echo "  ✓ GameMode daemon → started"
fi

# ── Power: disable sleep/suspend while gaming ────────────────────────────────
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target 2>/dev/null || true
# Keep screen on
if command -v xset >/dev/null 2>&1; then
    xset s off -dpms 2>/dev/null || true
fi
echo "  ✓ Sleep/suspend → disabled"

# ── Waybar: switch to gaming layout ──────────────────────────────────────────
CONFIG_DIR="${HOME:-/root}/.config/waybar"
if [[ -f "$CONFIG_DIR/config.gaming.jsonc" ]]; then
    cp "$CONFIG_DIR/config.gaming.jsonc" "$CONFIG_DIR/config.jsonc"
fi
if [[ -f "$CONFIG_DIR/style.gaming.css" ]]; then
    cp "$CONFIG_DIR/style.gaming.css" "$CONFIG_DIR/style.css"
fi
pkill -SIGUSR2 waybar 2>/dev/null || true

SCORE_FILE=/var/lib/shadowos/gaming-score.txt
{
  echo "ShadowOS Gaming Mode Active"
  echo "CPU: $CPU_MODEL ($CPU_COUNT cores) → performance governor"
  echo "RAM: swappiness=10, hugepages=madvise, max_map_count=2147483642"
  echo "GPU: $(echo "$GPU_INFO" | head -1)"
  echo "Tuned: $(date)"
} > "$SCORE_FILE"

echo ""
echo "✓ Gaming Mode fully active. Launch games with: gamemoderun %command%"
echo "  CoreCtrl available for additional GPU tuning (search app launcher)"
