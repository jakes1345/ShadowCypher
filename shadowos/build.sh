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

# ── Snapshot live ShadowCypher source into the ISO airootfs ─────────────────
# These dirs (ai_engine, shadowai, shadowcypher, shadow_skills) are gitignored
# at the repo root (they're tracked elsewhere or rebuilt locally).
# We rsync them in fresh at build time so the ISO ships current code without
# duplicating it in git.
REPO_ROOT="$(cd "$HERE/.." && pwd)"
ISO_OPT="$PROFILE/airootfs/opt/shadowcypher"
mkdir -p "$ISO_OPT"

RSYNC_EXCLUDES=(
  --exclude=__pycache__ --exclude='*.pyc' --exclude='*.pyo'
  --exclude=meta-venv --exclude=venv --exclude=.venv
  --exclude=logs --exclude=outputs --exclude=findings --exclude=reports
  --exclude='*.log' --exclude=.ruff_cache --exclude=test_venv
  --exclude='node_modules' --exclude=build --exclude=dist --exclude='*.egg-info'
)

for src in shadowcypher ai_engine shadowai shadow_skills shadowscript; do
  if [[ -d "$REPO_ROOT/$src" ]]; then
    echo ">> Snapshotting $src → ISO airootfs"
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$REPO_ROOT/$src/" "$ISO_OPT/$src/"
  fi
done

# Also snapshot the launch entrypoint + agent
[[ -f "$REPO_ROOT/native/launch.sh" ]] && cp "$REPO_ROOT/native/launch.sh" "$ISO_OPT/launch.sh"

echo ">> Building ShadowOS ISO"
mkarchiso -v -w "$WORK" -o "$OUT" "$PROFILE"

echo ">> Done. ISO in: $OUT"
ls -lh "$OUT"
