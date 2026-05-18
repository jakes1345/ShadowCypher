#!/usr/bin/env bash
# Build ShadowOS ISO via archiso.
# Requires: sudo pacman -S archiso
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE="$HERE/profile"
WORK="$HERE/work"
OUT="$HERE/out"

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

echo ">> Building ShadowOS ISO"
mkarchiso -v -w "$WORK" -o "$OUT" "$PROFILE"

echo ">> Done. ISO in: $OUT"
ls -lh "$OUT"
