#!/usr/bin/env bash
# Pre-build ISO validator — run before every build to catch errors without wasting build time.
set -euo pipefail

PROFILE="$(dirname "$0")/profile/airootfs"
PKGS="$(dirname "$0")/profile/packages.x86_64"
ERRORS=0
WARNINGS=0

err()  { echo "  [ERROR] $*"; ERRORS=$((ERRORS+1)); }
warn() { echo "  [WARN]  $*"; WARNINGS=$((WARNINGS+1)); }
ok()   { echo "  [OK]    $*"; }

# ── 1. Shell script syntax ────────────────────────────────────────────────────
echo "==> Checking shell script syntax..."
while IFS= read -r -d '' f; do
    head=$(head -1 "$f")
    if [[ "$head" != *bash* && "$head" != *sh* ]]; then
        warn "No shebang: $f"
    fi
    if ! bash -n "$f" 2>/tmp/sh_err; then
        err "Syntax error in $f: $(cat /tmp/sh_err)"
    fi
done < <(find "$PROFILE" -name "*.sh" -print0)
ok "Shell scripts checked"

# ── 2. Hyprland config ────────────────────────────────────────────────────────
echo "==> Checking Hyprland configs..."
for conf in \
    "$PROFILE/etc/skel/.config/hypr/hyprland.conf" \
    "$PROFILE/etc/shadowos/desktop/hyprland.conf"; do
    [[ -f "$conf" ]] || { err "Missing: $conf"; continue; }
    if grep -qn "windowrulev2" "$conf"; then
        err "$conf: 'windowrulev2' is deprecated — use 'windowrule'"
    fi
    if grep -qn "new_optimizations" "$conf"; then
        err "$conf: 'new_optimizations' removed in Hyprland 0.42+ — delete the line"
    fi
    if grep -qn "tap-to-click" "$conf"; then
        err "$conf: 'tap-to-click' must be 'tap_to_click'"
    fi
    if grep -qn "windowrule1\b" "$conf"; then
        err "$conf: 'windowrule' v1 syntax (no filter) is deprecated"
    fi
done
ok "Hyprland configs checked"

# ── 3. Waybar JSON ────────────────────────────────────────────────────────────
echo "==> Checking Waybar config..."
wb="$PROFILE/etc/skel/.config/waybar/config.jsonc"
if [[ -f "$wb" ]]; then
    # Strip // comments before parsing
    if ! sed 's|//.*||g' "$wb" | python3 -m json.tool > /dev/null 2>&1; then
        err "Invalid JSON in $wb"
    fi
fi
ok "Waybar config checked"

# ── 4. Systemd units ─────────────────────────────────────────────────────────
echo "==> Checking systemd units..."
while IFS= read -r -d '' f; do
    # Check ExecStart paths exist inside profile tree
    while IFS= read -r line; do
        bin=$(echo "$line" | sed 's/ExecStart=//;s/ .*//')
        # Only check absolute paths that aren't standard system paths
        if [[ "$bin" == /opt/* || "$bin" == /usr/local/* ]]; then
            rel="${PROFILE}${bin}"
            [[ -f "$rel" ]] || warn "Unit $f: ExecStart path missing in profile: $bin"
        fi
    done < <(grep "^ExecStart=" "$f" 2>/dev/null || true)
done < <(find "$PROFILE" -name "*.service" -print0)
ok "Systemd units checked"

# ── 5. Critical packages ──────────────────────────────────────────────────────
echo "==> Checking package list..."
required=(
    hyprland waybar foot mako hypridle hyprlock hyprpaper wofi
    nftables conntrack-tools ufw apparmor fail2ban macchanger
    networkmanager bluez blueman pipewire wireplumber
    grim slurp swappy wl-clipboard cliphist
    polkit-gnome
    python python-gobject gtk3
    git curl wget
)
for pkg in "${required[@]}"; do
    if ! grep -qx "$pkg" "$PKGS" 2>/dev/null; then
        err "Package missing from packages.x86_64: $pkg"
    fi
done
ok "Package list checked"

# ── 6. Critical files exist ───────────────────────────────────────────────────
echo "==> Checking critical profile files..."
critical=(
    "etc/skel/.config/hypr/hyprland.conf"
    "etc/skel/.config/waybar/config.jsonc"
    "etc/skel/.config/waybar/style.css"
    "etc/skel/.config/wofi/style.css"
    "etc/shadowos/desktop/hyprland.conf"
    "etc/systemd/system/shadowos-firstboot.service"
    "opt/shadowcypher/agent/install.sh"
)
for f in "${critical[@]}"; do
    [[ -f "$PROFILE/$f" ]] || err "Critical file missing: $f"
done
ok "Critical files checked"

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo "  Errors:   $ERRORS"
echo "  Warnings: $WARNINGS"
echo "────────────────────────────────────────"
if (( ERRORS > 0 )); then
    echo "  BUILD BLOCKED — fix errors above first"
    exit 1
else
    echo "  All checks passed — safe to build"
    exit 0
fi
