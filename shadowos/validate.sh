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
    # new_optimizations was removed in Hyprland 0.42+
    if grep -qn "new_optimizations" "$conf"; then
        err "$conf: 'new_optimizations' removed in Hyprland 0.42+ — delete the line"
    fi
    if grep -qn "tap-to-click" "$conf"; then
        err "$conf: use 'tap_to_click' not 'tap-to-click'"
    fi
done
ok "Hyprland configs checked"

# ── 3. Waybar JSON ────────────────────────────────────────────────────────────
echo "==> Checking Waybar config..."
wb="$PROFILE/etc/skel/.config/waybar/config.jsonc"
if [[ -f "$wb" ]]; then
    if ! sed 's|//.*||g' "$wb" | python3 -m json.tool > /dev/null 2>&1; then
        err "Invalid JSON in $wb"
    fi
fi
ok "Waybar config checked"

# ── 4. Systemd units ─────────────────────────────────────────────────────────
echo "==> Checking systemd units..."
while IFS= read -r -d '' f; do
    while IFS= read -r line; do
        bin=$(echo "$line" | sed 's/ExecStart=//;s/ .*//')
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
    nftables apparmor fail2ban macchanger
    networkmanager bluez pipewire wireplumber
    grim slurp swappy wl-clipboard cliphist
    polkit-kde-agent
    python python-gobject gtk3
    git curl wget jq
    calamares
)
for pkg in "${required[@]}"; do
    if ! grep -qx "$pkg" "$PKGS" 2>/dev/null; then
        err "Package missing from packages.x86_64: $pkg"
    fi
done
ok "Package list checked"

# ── 6. Mode scripts all exist ─────────────────────────────────────────────────
echo "==> Checking mode scripts..."
for mode in normal privacy ghost dev gaming; do
    dir="$PROFILE/etc/shadowos/modes/$mode"
    [[ -f "$dir/apply.sh" ]]  || err "Missing: modes/$mode/apply.sh"
    if [[ "$mode" != "normal" ]]; then
        [[ -f "$dir/revert.sh" ]] || err "Missing: modes/$mode/revert.sh"
    fi
done
ok "Mode scripts checked"

# ── 7. Critical files exist ───────────────────────────────────────────────────
echo "==> Checking critical profile files..."
critical=(
    "etc/skel/.config/hypr/hyprland.conf"
    "etc/skel/.config/waybar/config.jsonc"
    "etc/skel/.config/waybar/style.css"
    "etc/skel/.config/wofi/style.css"
    "etc/shadowos/desktop/hyprland.conf"
    "etc/systemd/system/shadowos-firstboot.service"
    "usr/local/bin/shadow-mode"
    "usr/local/bin/shadowos-session-start"
    "usr/local/bin/shadowos-firstboot"
    "usr/local/bin/shadowos-ramwipe"
)
for f in "${critical[@]}"; do
    [[ -f "$PROFILE/$f" ]] || err "Critical file missing: $f"
done
ok "Critical files checked"

# ── 8. Keybind script targets exist ──────────────────────────────────────────
echo "==> Checking hyprland keybind targets..."
while IFS= read -r script; do
    [[ -f "$PROFILE/$script" ]] || warn "Keybind target missing in profile: $script"
done < <(grep -h "exec," "$PROFILE/etc/shadowos/desktop/hyprland.conf" 2>/dev/null \
    | grep -oE '/usr/local/bin/[a-z0-9_-]+' \
    | sed 's|^/||' \
    | sort -u)
ok "Keybind targets checked"

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
