#!/usr/bin/env bash
# Full ShadowOS ISO build — tests first, then mkarchiso.
#   ./build-new-iso.sh              # build with sudo
#   ./build-new-iso.sh --no-test    # skip test_iso.sh (not recommended)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
SKIP_TEST=0
ARCHIVE="${SHADOWOS_ISO_ARCHIVE:-/media/jack/Liunux/shadowos-archive/isos}"

for arg in "$@"; do
    case "$arg" in
        --no-test) SKIP_TEST=1 ;;
        -h|--help)
            echo "Usage: $0 [--no-test]"
            exit 0
            ;;
        *) echo "Unknown: $arg" >&2; exit 1 ;;
    esac
done

echo "══════════════════════════════════════════════════════════"
echo "  ShadowOS full ISO build"
echo "  Repo: $REPO"
echo "══════════════════════════════════════════════════════════"

if [[ "$SKIP_TEST" -eq 0 ]]; then
    echo ">> Running profile audit (test_iso.sh)..."
    "$HERE/test_iso.sh"
fi

echo ">> Python import smoke test..."
PYTHONPATH="$REPO" python3 -c "import shadowcypher.app" 2>/dev/null || \
    PYTHONPATH="$REPO/shadowcypher" python3 -c "import shadowcypher.app"

AVAIL=$(df -Pk "$HERE/out" | awk 'NR==2 {print $4}')
if [[ "${AVAIL:-0}" -lt 15728640 ]]; then
    echo "ERROR: Need ~15GB free on out/ partition (have $(( AVAIL / 1024 / 1024 ))GB)" >&2
    exit 1
fi

# Move superseded ISOs off the NVMe if archive drive is mounted
if [[ -d "$ARCHIVE" ]]; then
    mkdir -p "$ARCHIVE"
    shopt -s nullglob
    for iso in "$HERE/out"/*.iso "$HERE/out"/*.iso.broken "$HERE/out"/*.iso.bak "$HERE/out"/*.prefix2; do
        base=$(basename "$iso")
        [[ "$base" == shadowos-0.1.0-$(date +%Y.%m.)* ]] && continue
        echo ">> Archiving old artifact: $base"
        mv -f "$iso" "$ARCHIVE/" 2>/dev/null || true
    done
fi

echo ">> Clearing stale work/ scratch (safe — mkarchiso recreates)..."
if [[ -d "$HERE/work" ]] && [[ -n "$(ls -A "$HERE/work" 2>/dev/null)" ]]; then
    if rm -rf "$HERE/work" 2>/dev/null; then
        :
    elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        docker run --rm -v "$HERE":/build alpine rm -rf /build/work
    else
        sudo rm -rf "$HERE/work"
    fi
fi
mkdir -p "$HERE/work" "$HERE/out"

if command -v mkarchiso >/dev/null 2>&1; then
    echo ">> Native archiso detected — building on host (sudo)..."
    sudo "$HERE/build.sh"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo ">> No native archiso (Mint/Ubuntu) — building via Docker/Arch container..."
    "$HERE/build-docker.sh"
else
    echo "ERROR: Need either 'archiso' (Arch) or Docker running (Mint/Ubuntu)." >&2
    echo "  Arch:  sudo pacman -S archiso && sudo $HERE/build.sh" >&2
    echo "  Other: sudo apt install docker.io && sudo usermod -aG docker \$USER  # re-login" >&2
    exit 1
fi

echo
echo ">> Build complete. Latest ISO:"
ls -lh "$HERE/out"/*.iso 2>/dev/null | tail -1
echo
echo "Verify:  ./boot-iso.sh --gui"
echo "         ./redteam.sh"
