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
# Preserve our launch.sh shim across rsync
cp "$SC_DST/launch.sh" /tmp/shadowos-launch.sh.bak 2>/dev/null || true
rsync -a \
    --exclude='shadowos/' \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='__pycache__/' \
    --exclude='test_venv/' \
    --exclude='.ruff_cache/' \
    --exclude='*.iso' \
    --exclude='*.log' \
    --exclude='work/' \
    --exclude='out/' \
    --exclude='releases/' \
    --exclude='wordlists/' \
    --exclude='tools/' \
    --exclude='*.png' \
    --exclude='*.jpg' \
    --include='shadowcypher/' \
    --include='shadowcypher/**' \
    --include='shadowai/' \
    --include='shadowai/**' \
    --include='agent/' \
    --include='agent/**' \
    --include='ai_engine/' \
    --include='ai_engine/**' \
    --include='shadowscript/' \
    --include='shadowscript/**' \
    --include='shadow_skills/' \
    --include='shadow_skills/**' \
    --include='launch.sh' \
    --exclude='*' \
    "$SC_SRC/" "$SC_DST/" 2>/dev/null || true

# Restore launch.sh shim
[[ -f /tmp/shadowos-launch.sh.bak ]] && cp /tmp/shadowos-launch.sh.bak "$SC_DST/launch.sh"
chmod +x "$SC_DST/launch.sh" 2>/dev/null || true

echo ">> [1/3] Building builder image ($IMAGE) ..."
docker build -t "$IMAGE" "$HERE"

echo ">> [2/3] Running mkarchiso inside container ..."
docker run --rm --privileged \
  -v "$HERE":/build \
  -w /build \
  "$IMAGE" -c '
    set -euo pipefail
    rm -rf /tmp/profile /build/work
    cp -a /usr/share/archiso/configs/releng /tmp/profile
    cp -a /build/profile/. /tmp/profile/
    mkdir -p /build/out /build/work
    mkarchiso -v -w /build/work -o /build/out /tmp/profile
  '

echo ">> [3/3] Done. ISO in: $OUT"
ls -lh "$OUT"
