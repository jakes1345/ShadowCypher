#!/usr/bin/env bash
# Build ShadowOS ISO via Docker (host doesn't need Arch).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE="shadowos-builder:latest"
OUT="$HERE/out"
WORK="$HERE/work"

mkdir -p "$OUT" "$WORK"

# === Mirror parts of the ShadowCypher repo into the airootfs ===
# So /opt/shadowcypher/ ships preinstalled inside the ISO.
SC_SRC="$HERE/.."
SC_DST="$HERE/profile/airootfs/opt/shadowcypher"
echo ">> staging shadowcypher → /opt/shadowcypher"
mkdir -p "$SC_DST"

# Per-directory rsync — simpler and more predictable than complex filter rules
RSYNC_EXCLUDES=(
    --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo'
    --exclude='.venv' --exclude='venv' --exclude='meta-venv'
    --exclude='node_modules' --exclude='.ruff_cache' --exclude='.git'
    --exclude='logs' --exclude='outputs' --exclude='findings'
    --exclude='reports' --exclude='*.log' --exclude='build' --exclude='dist'
    --exclude='*.egg-info'
)
for src in shadowcypher ai_engine shadowai shadow_skills shadowscript agent; do
    if [[ -d "$SC_SRC/$src" ]]; then
        echo ">>   snapshotting $src ($(du -sh "$SC_SRC/$src" 2>/dev/null | cut -f1))"
        rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SC_SRC/$src/" "$SC_DST/$src/"
    fi
done

# launch.sh entrypoint at /opt/shadowcypher/launch.sh
if [[ -f "$SC_SRC/native/launch.sh" ]]; then
    cp "$SC_SRC/native/launch.sh" "$SC_DST/launch.sh"
else
    # Minimal fallback so the Hyprland exec-once doesn't fail
    cat > "$SC_DST/launch.sh" <<'LAUNCHER'
#!/usr/bin/env bash
# ShadowCypher launcher — runs the Python app from /opt/shadowcypher
export PYTHONPATH=/opt/shadowcypher
exec python3 -m shadowcypher.app "$@"
LAUNCHER
fi
chmod +x "$SC_DST/launch.sh"

echo ">> [1/3] Building builder image ($IMAGE) ..."
docker build -t "$IMAGE" "$HERE"

echo ">> [2/3] Running mkarchiso inside container ..."
docker run --rm --privileged --network=host \
  -v "$HERE":/build \
  -w /build \
  "$IMAGE" -c '
    set -euo pipefail
    rm -rf /tmp/profile /build/work
    cp -a /usr/share/archiso/configs/releng /tmp/profile
    cp -a /build/profile/. /tmp/profile/
    mkdir -p /build/out /build/work

    # Pick fast Arch mirrors — fastly.mirror.pkgbuild.com throttles us hard
    echo ">> Refreshing mirrorlist via reflector..."
    reflector --latest 20 --protocol https --sort rate \
        --save /etc/pacman.d/mirrorlist 2>&1 | tail -3 || true

    # Bootstrap BlackArch keyring + mirrorlist for [blackarch] repo
    echo ">> Importing BlackArch keyring..."
    curl -fsSL -o /tmp/strap.sh https://blackarch.org/strap.sh
    chmod +x /tmp/strap.sh
    /tmp/strap.sh 2>&1 | tail -5

    # Bootstrap Chaotic-AUR keyring + mirrorlist for [chaotic-aur] repo
    # (provides librewolf, mullvad-browser-bin, freetube-bin, heroic, etc.)
    echo ">> Importing Chaotic-AUR keyring..."
    pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com 2>&1 | tail -3
    pacman-key --lsign-key 3056513887B78AEB 2>&1 | tail -3
    pacman -U --noconfirm \
        "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst" \
        "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst" \
        2>&1 | tail -5

    pacman -Sy 2>&1 | tail -5

    mkarchiso -v -w /build/work -o /build/out /tmp/profile
  '

echo ">> [3/3] Done. ISO in: $OUT"
ls -lh "$OUT"
