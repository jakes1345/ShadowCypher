#!/usr/bin/env bash
# Build ShadowOS ISO via Docker (host doesn't need Arch).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE="shadowos-builder:latest"
OUT="$HERE/out"
WORK="$HERE/work"

mkdir -p "$OUT" "$WORK"

# The ShadowCypher desktop app (Qt6 C++, shadowcypher-qt/) is built and
# installed into the image inside the container below. The image used to carry
# a snapshot of the old Python app in /opt/shadowcypher; make sure none is left.
REPO_ROOT="$(cd "$HERE/.." && pwd)"
rm -rf "$HERE/profile/airootfs/opt/shadowcypher"

BUILD_DATE="$(date +%Y.%m.%d)"
OSR="$HERE/profile/airootfs/etc/os-release"
if [[ -f "$OSR" ]]; then
    sed -i "s/^PRETTY_NAME=.*/PRETTY_NAME=\"ShadowOS 0.3 (${BUILD_DATE})\"/" "$OSR"
    sed -i "s/^BUILD_ID=.*/BUILD_ID=${BUILD_DATE}/" "$OSR"
fi

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
  -v "$REPO_ROOT/shadowcypher-qt":/src/shadowcypher-qt:ro \
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

    # Build the ShadowCypher desktop app and install it into the image
    # (/usr/bin/shadowcypher, shadowcypher-daemon, the Ghost mode privacy helper
    # and its polkit policy, menu entry and icon). No app means no ISO.
    set -e
    pacman --noconfirm -S --needed cmake make gcc pkgconf qt6-base qt6-websockets 2>&1 | tail -3
    cmake -S /src/shadowcypher-qt -B /tmp/qt-build -DCMAKE_BUILD_TYPE=Release \
          -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_TESTING=OFF -Wno-dev
    cmake --build /tmp/qt-build --parallel "$(nproc)"
    DESTDIR=/tmp/profile/airootfs cmake --install /tmp/qt-build --strip
    test -x /tmp/profile/airootfs/usr/bin/shadowcypher
    test -x /tmp/profile/airootfs/usr/libexec/shadowcypher/shadowcypher-privacy-helper
    echo ">> ShadowCypher desktop app installed into the image."
    set +e

    # Patch mkarchiso to pass --noconfirm to pacstrap
    python3 /build/patch-mkarchiso.py

    # mkarchiso — must succeed or we have nothing
    set -e
    echo ">> Building ISO with mkarchiso..."
    mkarchiso -v -w /build/work -o /build/out /tmp/profile
  '

echo ">> [3/3] Done. ISO in: $OUT"
ls -lh "$OUT"
