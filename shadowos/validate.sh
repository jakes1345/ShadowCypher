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
# Hyprland's own check (Hyprland --verify-config) runs in the package build,
# packaging/arch/build-repo.sh, which has Hyprland installed.
echo "==> Checking Hyprland configs..."
skel_conf="$PROFILE/etc/skel/.config/hypr/hyprland.lua"
canon_conf="$PROFILE/etc/shadowos/desktop/hyprland.lua"
for conf in "$skel_conf" "$canon_conf"; do
    [[ -f "$conf" ]] || { err "Missing: $conf"; continue; }
    # Hyprland reads hyprland.lua only. A hyprland.conf beside it is never read.
    [[ -e "${conf%.lua}.conf" ]] && err "${conf%.lua}.conf: Hyprland no longer reads this format — move its settings to hyprland.lua"
done
# shadowos-session-start copies the canonical file over the user's at every login.
if [[ -f "$skel_conf" && -f "$canon_conf" ]] && ! cmp -s "$skel_conf" "$canon_conf"; then
    err "hyprland.lua differs between etc/skel/.config/hypr and etc/shadowos/desktop"
fi
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
    qt6-base qt6-wayland qt6-websockets tor iptables polkit
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
    "etc/skel/.config/hypr/hyprland.lua"
    "etc/skel/.config/waybar/config.jsonc"
    "etc/skel/.config/waybar/style.css"
    "etc/skel/.config/wofi/style.css"
    "etc/shadowos/desktop/hyprland.lua"
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
done < <(grep -ohE '/usr/local/bin/[a-z0-9_-]+' "$PROFILE/etc/shadowos/desktop/hyprland.lua" 2>/dev/null | sed 's|^/||' | sort -u)
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
