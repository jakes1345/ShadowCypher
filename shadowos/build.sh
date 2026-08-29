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

mkdir -p "$WORK" "$OUT" "$ISO_OPT"

# Copy releng base if profile is incomplete (first run helper)
if [[ ! -f "$PROFILE/pacman.conf" ]]; then
  echo "Seeding profile from /usr/share/archiso/configs/releng ..."
  cp -rn /usr/share/archiso/configs/releng/. "$PROFILE/"
fi

RSYNC_EXCLUDES=(
  --exclude=__pycache__ --exclude='*.pyc' --exclude='*.pyo'
  --exclude=meta-venv --exclude=venv --exclude=.venv
  --exclude=logs --exclude=outputs --exclude=findings --exclude=reports
  --exclude='*.log' --exclude=.ruff_cache --exclude=test_venv
  --exclude='node_modules' --exclude=build --exclude=dist --exclude='*.egg-info'
)

echo ">> Snapshotting ShadowCypher sources → ISO airootfs/opt/shadowcypher"
for src in shadowcypher ai_engine shadowai shadow_skills shadowscript agent; do
  if [[ -d "$REPO_ROOT/$src" ]]; then
    echo "   rsync $src"
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$REPO_ROOT/$src/" "$ISO_OPT/$src/"
  fi
done

# Assets (war map, icons) — live at /opt/shadowcypher/assets on the image
if [[ -d "$REPO_ROOT/assets" ]]; then
  echo "   rsync assets → opt/shadowcypher/assets"
  rsync -a "$REPO_ROOT/assets/" "$ISO_OPT/assets/"
fi

# Native icons + launch entrypoint
if [[ -d "$REPO_ROOT/native/icons" ]]; then
  mkdir -p "$ISO_OPT/native/icons"
  rsync -a "$REPO_ROOT/native/icons/" "$ISO_OPT/native/icons/"
fi
[[ -f "$REPO_ROOT/native/launch.sh" ]] && cp -f "$REPO_ROOT/native/launch.sh" "$ISO_OPT/launch.sh"
[[ -f "$ISO_OPT/launch.sh" ]] || cp -f "$PROFILE/airootfs/opt/shadowcypher/launch.sh" "$ISO_OPT/launch.sh" 2>/dev/null || true
[[ -f "$REPO_ROOT/config.example.json" ]] && cp -f "$REPO_ROOT/config.example.json" "$ISO_OPT/config.example.json"

chmod +x "$ISO_OPT/launch.sh" 2>/dev/null || true

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

echo ">> Building ShadowOS ISO (mkarchiso)"
mkarchiso -v -w "$WORK" -o "$OUT" "$PROFILE"

echo ">> Done. ISO in: $OUT"
ls -lh "$OUT"/*.iso 2>/dev/null || ls -lh "$OUT"
