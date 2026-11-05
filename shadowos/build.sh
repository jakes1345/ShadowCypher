#!/usr/bin/env bash
# Build ShadowOS ISO via archiso.
# Requires: sudo pacman -S archiso
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE="$HERE/profile"
WORK="$HERE/work"
OUT="$HERE/out"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
ISO_OPT="$PROFILE/airootfs/opt/shadowcypher"
BUILD_DATE="$(date +%Y.%m.%d)"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if ! command -v mkarchiso >/dev/null 2>&1; then
  echo "archiso not installed. Run: pacman -S archiso" >&2
  exit 1
fi

mkdir -p "$WORK" "$OUT"

# Copy releng base if profile is incomplete (first run helper)
if [[ ! -f "$PROFILE/pacman.conf" ]]; then
  echo "Seeding profile from /usr/share/archiso/configs/releng ..."
  cp -rn /usr/share/archiso/configs/releng/. "$PROFILE/"
fi

# The ISO used to carry a snapshot of the old Python/GTK app in
# /opt/shadowcypher. The desktop app is now Qt6 C++ (shadowcypher-qt), built
# and installed into the image below; make sure no stale copy is left behind.
rm -rf "$ISO_OPT"

# Stamp build metadata into os-release (visible in neofetch / welcome)
OSR="$PROFILE/airootfs/etc/os-release"
if [[ -f "$OSR" ]]; then
  sed -i "s/^PRETTY_NAME=.*/PRETTY_NAME=\"ShadowOS 0.3 (${BUILD_DATE})\"/" "$OSR"
  sed -i "s/^BUILD_ID=.*/BUILD_ID=${BUILD_DATE}/" "$OSR"
fi

# Stage GRUB theme into the ISO grub directory for live-boot display
GRUB_THEME_SRC="$PROFILE/airootfs/usr/share/grub/themes/shadowos"
GRUB_THEME_DST="$PROFILE/grub/themes/shadowos"
if [[ -d "$GRUB_THEME_SRC" ]]; then
  mkdir -p "$GRUB_THEME_DST"
  cp -r "$GRUB_THEME_SRC/." "$GRUB_THEME_DST/"
  echo ">> GRUB theme staged → profile/grub/themes/shadowos/"
fi

# ── Build the Qt6 desktop app and install it into airootfs ───────────────
# Installs /usr/bin/shadowcypher (+ shadowcypher-daemon, shadowcypher-runtime),
# the Ghost mode root helper in /usr/libexec/shadowcypher, its polkit policy,
# the menu entry and icon. The ISO is pointless without it, so a failed build
# stops here instead of producing an image with no app.
QT_APP_SRC="$REPO_ROOT/shadowcypher-qt"
QT_APP_BUILD="$QT_APP_SRC/_build"
AIROOTFS="$PROFILE/airootfs"

if ! command -v cmake >/dev/null 2>&1 || ! pkg-config --exists Qt6Widgets 2>/dev/null; then
  echo "cmake and Qt6 are required: pacman -S cmake make gcc pkgconf qt6-base qt6-websockets" >&2
  exit 1
fi
echo ">> Building ShadowCypher desktop app (shadowcypher-qt)"
cmake -S "$QT_APP_SRC" -B "$QT_APP_BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr \
  -DBUILD_TESTING=OFF \
  -Wno-dev
cmake --build "$QT_APP_BUILD" --parallel "$(nproc)"
DESTDIR="$AIROOTFS" cmake --install "$QT_APP_BUILD" --strip
for f in /usr/bin/shadowcypher /usr/bin/shadowcypher-daemon \
         /usr/libexec/shadowcypher/shadowcypher-privacy-helper; do
  [[ -x "$AIROOTFS$f" ]] || { echo "   missing after install: $f" >&2; exit 1; }
done
echo "   Installed into airootfs: shadowcypher, shadowcypher-daemon, privacy helper"

# ── Build Qt6 installer binary and stage it into airootfs ──────────────────
INSTALLER_SRC="$REPO_ROOT/shadowos/installer"
INSTALLER_BIN="$PROFILE/airootfs/usr/local/bin/shadowos-installer"

if [[ -d "$INSTALLER_SRC/src" ]]; then
  echo ">> Compiling Qt6 installer..."
  INSTALLER_BUILD="$INSTALLER_SRC/_build"
  mkdir -p "$INSTALLER_BUILD"

  if ! command -v cmake >/dev/null 2>&1; then
    echo "   cmake not found — skipping installer build" >&2
  elif ! pkg-config --exists Qt6Widgets 2>/dev/null; then
    echo "   Qt6 not found — skipping installer build (install qt6-base)" >&2
  else
    cmake -S "$INSTALLER_SRC" -B "$INSTALLER_BUILD" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr \
      -Wno-dev -DCMAKE_VERBOSE_MAKEFILE=OFF 2>&1 | tail -5

    make -C "$INSTALLER_BUILD" -j"$(nproc)" 2>&1 | tail -10

    if [[ -f "$INSTALLER_BUILD/shadowos-installer" ]]; then
      cp -f "$INSTALLER_BUILD/shadowos-installer" "$INSTALLER_BIN"
      chmod +x "$INSTALLER_BIN"
      strip --strip-unneeded "$INSTALLER_BIN" 2>/dev/null || true
      echo "   Installer staged → $INSTALLER_BIN ($(du -sh "$INSTALLER_BIN" | cut -f1))"
    else
      echo "   WARNING: installer binary not produced — check cmake output" >&2
    fi
  fi
else
  echo "   Installer source not found at $INSTALLER_SRC — skipping" >&2
fi

echo ">> Building ShadowOS ISO (mkarchiso)"
mkarchiso -v -w "$WORK" -o "$OUT" "$PROFILE"

echo ">> Done. ISO in: $OUT"
ls -lh "$OUT"/*.iso 2>/dev/null || ls -lh "$OUT"
