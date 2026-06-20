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
    # Size reduction: skip heavy non-runtime assets from the ISO
    --exclude='docs' --exclude='*.mp4' --exclude='*.mp3'
    --exclude='*.pdf' --exclude='paper'
    --exclude='autoagent-intro.svg' --exclude='autoagent-intro.png'
)
for src in shadowcypher ai_engine shadowai shadow_skills shadowscript agent; do
    if [[ -d "$SC_SRC/$src" ]]; then
        echo ">>   snapshotting $src ($(du -sh "$SC_SRC/$src" 2>/dev/null | cut -f1))"
        rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SC_SRC/$src/" "$SC_DST/$src/"
    fi
done

if [[ -d "$SC_SRC/assets" ]]; then
    echo ">>   snapshotting assets"
    rsync -a "$SC_SRC/assets/" "$SC_DST/assets/"
fi
[[ -f "$SC_SRC/config.example.json" ]] && cp -f "$SC_SRC/config.example.json" "$SC_DST/config.example.json"

BUILD_DATE="$(date +%Y.%m.%d)"
OSR="$HERE/profile/airootfs/etc/os-release"
if [[ -f "$OSR" ]]; then
    sed -i "s/^PRETTY_NAME=.*/PRETTY_NAME=\"ShadowOS 0.3 (${BUILD_DATE})\"/" "$OSR"
    sed -i "s/^BUILD_ID=.*/BUILD_ID=${BUILD_DATE}/" "$OSR"
fi

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

# Copy GRUB theme into the ISO's grub directory so it loads during live boot.
# (The airootfs copy lives at usr/share/grub/themes/shadowos/ for the installed
# system; the ISO GRUB looks in profile/grub/themes/ via ${prefix}/themes/.)
GRUB_THEME_SRC="$HERE/profile/airootfs/usr/share/grub/themes/shadowos"
GRUB_THEME_DST="$HERE/profile/grub/themes/shadowos"
if [[ -d "$GRUB_THEME_SRC" ]]; then
    mkdir -p "$GRUB_THEME_DST"
    cp -r "$GRUB_THEME_SRC/." "$GRUB_THEME_DST/"
    echo ">> GRUB theme staged → profile/grub/themes/shadowos/"
fi

echo ">> [1/3] Building builder image ($IMAGE) ..."
docker build -t "$IMAGE" "$HERE"

mkdir -p "$HERE/pkg-cache"
echo ">> [2/3] Running mkarchiso inside container ..."
docker run --rm --privileged --network=host \
  -v "$HERE":/build \
  -v "$HERE/pkg-cache":/var/cache/pacman/pkg \
  -w /build \
  "$IMAGE" -c '
    # Never exit on error — handle everything explicitly
    set +e

    echo ">> Setting up build environment..."
    rm -rf /tmp/profile /build/work
    cp -a /usr/share/archiso/configs/releng /tmp/profile
    cp -a /build/profile/. /tmp/profile/
    mkdir -p /build/out /build/work

    # Use reliable mirror
    echo "Server = https://geo.mirror.pkgbuild.com/\$repo/os/\$arch" > /etc/pacman.d/mirrorlist
    echo "Server = https://mirror.rackspace.com/archlinux/\$repo/os/\$arch" >> /etc/pacman.d/mirrorlist
    echo ">> Mirrors set."

    # Bootstrap BlackArch
    echo ">> Importing BlackArch keyring..."
    curl -fsSL --retry 3 --connect-timeout 10 -o /tmp/strap.sh https://blackarch.org/strap.sh
    if [[ $? -eq 0 && -f /tmp/strap.sh ]]; then
        chmod +x /tmp/strap.sh
        bash /tmp/strap.sh 2>&1 | tail -5
        echo ">> BlackArch done."
    else
        echo ">> WARNING: BlackArch strap download failed — skipping"
    fi

    # Bootstrap Chaotic-AUR — fetch key via HTTPS to avoid UDP keyserver hangs in Docker
    echo ">> Importing Chaotic-AUR keyring..."
    pacman-key --init 2>&1 | tail -2
    curl -fsSL --max-time 30 \
        "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3056513887B78AEB&options=mr" \
        -o /tmp/chaotic-key.asc 2>&1 && \
        pacman-key --add /tmp/chaotic-key.asc 2>&1 | tail -2 && \
        pacman-key --lsign-key 3056513887B78AEB 2>&1 | tail -2 || \
        echo ">> WARNING: could not fetch chaotic-aur key via HTTPS"
    pacman --noconfirm -U \
        "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst" \
        "https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst" \
        2>&1 | tail -5
    if [[ ! -f /etc/pacman.d/chaotic-mirrorlist ]]; then
        echo "Server = https://cdn-mirror.chaotic.cx/chaotic-aur/\$arch" > /etc/pacman.d/chaotic-mirrorlist
    fi
    echo ">> Chaotic-AUR done."

    # Refresh keyring first — stale keys cause "checking package integrity" failures
    pacman --noconfirm -Sy archlinux-keyring 2>&1 | tail -3
    pacman-key --populate archlinux 2>&1 | tail -2
    echo ">> Keyring refreshed."

    pacman --noconfirm -Sy 2>&1 | tail -3
    echo ">> Databases synced."

    # Patch mkarchiso to pass --noconfirm to pacstrap
    python3 /build/patch-mkarchiso.py

    # mkarchiso — must succeed or we have nothing
    set -e
    echo ">> Building ISO with mkarchiso..."
    mkarchiso -v -w /build/work -o /build/out /tmp/profile
  '

echo ">> [3/3] Done. ISO in: $OUT"
ls -lh "$OUT"
