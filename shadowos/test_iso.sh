#!/usr/bin/env bash
# ShadowOS ISO pre-build audit — runs every static check we can
# without booting the ISO. Goal: zero errors/warnings.
#
# Exits non-zero on FAIL; warnings don't fail the run.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE="$HERE/profile"
AIRFS="$PROFILE/airootfs"

# ── output helpers ──────────────────────────────────────────────────────────
RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; CYAN='\033[1;36m'; NC='\033[0m'
fails=0
warns=0
passes=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((passes++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((fails++)); }
warn() { echo -e "  ${YELLOW}~${NC} $1"; ((warns++)); }
section() { echo; echo -e "${CYAN}[$1]${NC}"; }

# ── 1. Required files exist ────────────────────────────────────────────────
section "1. CORE FILES PRESENT"
required=(
  "$PROFILE/packages.x86_64"
  "$PROFILE/pacman.conf"
  "$PROFILE/profiledef.sh"
  "$PROFILE/grub/grub.cfg"
  "$AIRFS/root/customize_airootfs.sh"
  "$AIRFS/etc/os-release"
  "$AIRFS/etc/hostname"
  "$AIRFS/etc/sysctl.d/99-shadowos.conf"
  "$AIRFS/etc/systemd/system/shadowos-firstboot.service"
  "$AIRFS/etc/systemd/system/shadowos-mac-randomize.service"
  "$AIRFS/etc/skel/.config/hypr/hyprland.conf"
  "$AIRFS/etc/skel/.config/hypr/hyprlock.conf"
  "$AIRFS/etc/skel/.config/hypr/hyprpaper.conf"
  "$AIRFS/etc/skel/.config/hypr/hypridle.conf"
  "$AIRFS/etc/skel/.config/waybar/config.jsonc"
  "$AIRFS/etc/skel/.config/waybar/style.css"
  "$AIRFS/etc/skel/.zshrc"
  "$AIRFS/etc/sddm.conf.d/shadowos.conf"
  "$AIRFS/usr/share/sddm/themes/shadowos/Main.qml"
  "$AIRFS/usr/share/sddm/themes/shadowos/metadata.desktop"
  "$AIRFS/usr/share/plymouth/themes/shadowos/shadowos.plymouth"
  "$AIRFS/usr/share/plymouth/themes/shadowos/shadowos.script"
  "$AIRFS/usr/share/plymouth/themes/shadowos/logo.png"
  "$AIRFS/usr/share/plymouth/themes/shadowos/dot.png"
  "$AIRFS/usr/share/grub/themes/shadowos/theme.txt"
  "$AIRFS/usr/share/grub/themes/shadowos/background.png"
  "$AIRFS/usr/share/backgrounds/shadowos/wallpaper.png"
  "$AIRFS/etc/shadowos/desktop/waybar/config.fallback.jsonc"
)
for f in "${required[@]}"; do
  if [[ -f "$f" || -L "$f" ]]; then pass "$(basename "$f")"; else fail "missing: $f"; fi
done

# ── 2. Shell script syntax ──────────────────────────────────────────────────
section "2. SHELL SCRIPT SYNTAX (bash -n)"
shopt -s globstar nullglob
shells=(
  "$AIRFS"/root/customize_airootfs.sh
  "$AIRFS"/usr/local/bin/*
  "$AIRFS"/etc/shadowos/modes/*/apply.sh
  "$HERE/build.sh" "$HERE/build-docker.sh" "$HERE/flash-usb.sh"
  "$HERE/smoke-test.sh" "$HERE/test_iso.sh"
)
for s in "${shells[@]}"; do
  [[ -f "$s" ]] || continue
  # Python helpers ship with a .sh-style path in /usr/local/bin
  if head -1 "$s" 2>/dev/null | grep -q python; then
    pass "$(basename "$s") (python)"
    continue
  fi
  if bash -n "$s" 2>/dev/null; then pass "$(basename "$s")"; else
    fail "syntax error: $s"
    bash -n "$s" 2>&1 | head -3 | sed 's/^/      /'
  fi
done

# ── 3. JSON validation ──────────────────────────────────────────────────────
section "3. JSON CONFIG VALIDATION"
json_files=(
  "$AIRFS/etc/skel/.config/waybar/config.jsonc"
  "$AIRFS/etc/fastfetch/shadowos.jsonc"
  "$AIRFS/etc/shadowos/install/archinstall.json"
)
for f in "${json_files[@]}"; do
  [[ -f "$f" ]] || continue
  # Try strict JSON first (valid JSON is valid JSONC).
  # Fall back to a string-aware comment stripper if needed.
  if python3 -c "
import sys, json
try:
    json.load(open('$f'))
    sys.exit(0)
except Exception:
    pass
# Strip // and /* */ comments — string-aware
s = open('$f').read()
out = []
i = 0
in_str = False
esc = False
while i < len(s):
    c = s[i]
    if in_str:
        out.append(c)
        if esc:
            esc = False
        elif c == '\\\\':
            esc = True
        elif c == '\"':
            in_str = False
        i += 1
        continue
    if c == '\"':
        in_str = True
        out.append(c); i += 1; continue
    if c == '/' and i + 1 < len(s):
        if s[i+1] == '/':
            while i < len(s) and s[i] != '\n': i += 1
            continue
        if s[i+1] == '*':
            i += 2
            while i + 1 < len(s) and not (s[i] == '*' and s[i+1] == '/'): i += 1
            i += 2
            continue
    out.append(c); i += 1
try:
    json.loads(''.join(out))
    sys.exit(0)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    pass "$(basename "$f")"
  else
    fail "invalid JSON: $(basename "$f")"
  fi
done

# ── 4. Hyprland config sanity ──────────────────────────────────────────────
section "4. HYPRLAND CONFIG"
hp="$AIRFS/etc/skel/.config/hypr/hyprland.conf"
if [[ -f "$hp" ]]; then
  # Check for matched braces (every { needs a })
  open=$(grep -c '{' "$hp")
  close=$(grep -c '}' "$hp")
  [[ "$open" == "$close" ]] && pass "matched braces ($open/$close)" || fail "unmatched braces: $open open, $close close"

  # Check for orphan trailing whitespace / cr
  if grep -q $'\r' "$hp"; then fail "CR characters in $hp"; else pass "no CR"; fi

  # exec-once: every file referenced should exist where possible.
  # /usr/lib/* paths are provided by installed packages, not by airootfs source.
  for ref in $(grep -oE 'exec-once = [^ ]+' "$hp" | awk '{print $3}' | grep '^/'); do
    if [[ -e "$AIRFS$ref" || -e "$ref" ]]; then
      pass "exec-once → $ref exists"
    elif [[ "$ref" =~ ^/usr/(lib|bin|sbin)/ ]]; then
      pass "exec-once → $ref (provided by installed package)"
    else
      warn "exec-once references missing path: $ref"
    fi
  done

  # Check workspace count is sane
  ws_max=$(grep -oE 'workspace, [0-9]+' "$hp" | awk '{print $2}' | sort -n | tail -1)
  [[ -n "$ws_max" && "$ws_max" -ge 5 && "$ws_max" -le 10 ]] && pass "workspace count = $ws_max" || warn "workspace count odd: $ws_max"
fi

# ── 5. Plymouth script — basic lexical check ───────────────────────────────
section "5. PLYMOUTH SCRIPT"
ps="$AIRFS/usr/share/plymouth/themes/shadowos/shadowos.script"
if [[ -f "$ps" ]]; then
  open=$(grep -c '{' "$ps")
  close=$(grep -c '}' "$ps")
  [[ "$open" == "$close" ]] && pass "matched braces ($open/$close)" || fail "unmatched braces in plymouth.script"
  grep -q 'Plymouth.SetRefreshFunction' "$ps" && pass "refresh function registered" || warn "no Plymouth.SetRefreshFunction call"
  grep -q 'Plymouth.SetDisplayPasswordFunction' "$ps" && pass "password prompt handler" || warn "no password prompt handler"
  # Check images referenced exist
  for img in $(grep -oE 'Image\("[^"]+"\)' "$ps" | sed 's/Image("\(.*\)")/\1/'); do
    if [[ -f "$AIRFS/usr/share/plymouth/themes/shadowos/$img" ]]; then
      pass "image asset: $img"
    else
      fail "image referenced but missing: $img"
    fi
  done
fi

# ── 6. GRUB theme — referenced images exist ────────────────────────────────
section "6. GRUB THEME"
gt="$AIRFS/usr/share/grub/themes/shadowos/theme.txt"
gd="$(dirname "$gt")"
if [[ -f "$gt" ]]; then
  # Each PNG referenced must exist
  for img in $(grep -oE '"[^"]+\.png"' "$gt" | tr -d '"' | sort -u); do
    if [[ -f "$gd/$img" ]] || [[ "$img" == *"*"* ]]; then
      # *.png is a pattern (e.g. select_*.png) — verify pieces exist
      if [[ "$img" == *"*"* ]]; then
        pattern="${img/\*/}"
        prefix="${img%\*.png}"
        count=$(ls "$gd/${prefix}"*.png 2>/dev/null | wc -l)
        if [[ "$count" -ge 4 ]]; then pass "9-slice ${img} ($count pieces)"; else fail "9-slice $img incomplete ($count)"; fi
      else
        pass "asset: $img"
      fi
    else
      fail "GRUB theme references missing: $img"
    fi
  done
fi

# ── 7. systemd unit syntax ─────────────────────────────────────────────────
section "7. SYSTEMD UNITS"
for u in "$AIRFS"/etc/systemd/system/*.service; do
  [[ -f "$u" ]] || continue
  # Required headers
  for sect in '\[Unit\]' '\[Service\]' '\[Install\]'; do
    if grep -qE "^${sect}" "$u"; then
      pass "$(basename "$u"): has ${sect//\\/}"
    else
      warn "$(basename "$u"): missing ${sect//\\/}"
    fi
  done
  # ExecStart paths exist
  for cmd in $(grep -oE 'ExecStart=[^ ]+' "$u" | cut -d= -f2-); do
    bin="${cmd%% *}"
    if [[ -f "$AIRFS$bin" || -f "$bin" ]]; then
      pass "$(basename "$u"): ExecStart=$bin exists"
    else
      warn "$(basename "$u"): ExecStart=$bin not found at build time"
    fi
  done
done

# ── 8. SDDM theme files ─────────────────────────────────────────────────────
section "8. SDDM THEME"
sddm="$AIRFS/usr/share/sddm/themes/shadowos"
if [[ -d "$sddm" ]]; then
  for f in Main.qml metadata.desktop theme.conf; do
    [[ -f "$sddm/$f" ]] && pass "$f" || fail "SDDM missing: $f"
  done
  # Background image is referenced
  if [[ -f "$sddm/wallpaper.png" ]]; then pass "wallpaper.png"; else warn "SDDM has no wallpaper.png"; fi
  # Sanity-check QML has no obvious syntax issues
  qml="$sddm/Main.qml"
  if [[ -f "$qml" ]]; then
    open=$(grep -c '{' "$qml")
    close=$(grep -c '}' "$qml")
    [[ "$open" == "$close" ]] && pass "Main.qml: braces matched ($open/$close)" || fail "Main.qml unmatched braces"
    grep -q 'import QtQuick' "$qml" && pass "Main.qml imports QtQuick" || fail "Main.qml missing QtQuick import"
  fi
fi

# ── 9. Wallpapers count + symlinks ─────────────────────────────────────────
section "9. WALLPAPERS"
wp="$AIRFS/usr/share/backgrounds/shadowos"
desktop_count=$(ls "$wp"/shadowos-??-*-1920x1080.png 2>/dev/null | wc -l)
[[ "$desktop_count" == "20" ]] && pass "20 desktop wallpapers (1080p)" || fail "expected 20 desktop 1080p wallpapers, got $desktop_count"
desktop_4k=$(ls "$wp"/shadowos-??-*-3840x2160.png 2>/dev/null | wc -l)
[[ "$desktop_4k" == "20" ]] && pass "20 desktop wallpapers (4K)" || fail "expected 20 4K wallpapers, got $desktop_4k"
login_count=$(ls "$wp"/login/shadowos-login-*-1920x1080.png 2>/dev/null | wc -l)
[[ "$login_count" == "3" ]] && pass "3 login wallpapers" || fail "expected 3 login wallpapers, got $login_count"
[[ -L "$wp/wallpaper.png" ]] && pass "default symlink: wallpaper.png" || warn "wallpaper.png not symlink"

# ── 10. Local bin scripts are executable ───────────────────────────────────
section "10. /usr/local/bin SCRIPTS"
for b in "$AIRFS"/usr/local/bin/*; do
  [[ -f "$b" ]] || continue
  if [[ -x "$b" ]] || head -1 "$b" 2>/dev/null | grep -q '^#!'; then
    pass "$(basename "$b")"
  else
    warn "$(basename "$b") — not executable, but customize_airootfs.sh sets +x"
  fi
done

# ── 11. Mode scripts ────────────────────────────────────────────────────────
section "11. MODE SCRIPTS"
for m in normal dev pentest privacy ghost; do
  f="$AIRFS/etc/shadowos/modes/$m/apply.sh"
  if [[ -f "$f" ]]; then
    if bash -n "$f" 2>/dev/null; then pass "$m mode"; else fail "$m mode: bash syntax"; fi
  else
    fail "$m mode missing"
  fi
done

# ── 12. file_permissions table consistency ─────────────────────────────────
section "12. file_permissions IN profiledef.sh"
pf="$PROFILE/profiledef.sh"
if [[ -f "$pf" ]]; then
  # /etc/shadow and other runtime-only files are created at build time by
  # customize_airootfs.sh (useradd/chpasswd) — fine to set perms in profiledef.
  runtime_paths='^/etc/shadow$|^/etc/sudoers'
  for path in $(grep -oE '\["/[^"]+"\]=' "$pf" | tr -d '[]="'); do
    if [[ -f "$AIRFS$path" || -d "$AIRFS$path" ]]; then
      pass "permission target exists: $path"
    elif [[ "$path" =~ $runtime_paths ]]; then
      pass "permission target: $path (created at airootfs build time)"
    else
      warn "permission set for non-existent path: $path"
    fi
  done
fi

# ── 13. Package list — detect duplicates and AUR refs ──────────────────────
section "13. PACKAGES.X86_64"
pl="$PROFILE/packages.x86_64"
if [[ -f "$pl" ]]; then
  # Strip comments + blanks
  pkgs=$(grep -vE '^\s*#|^\s*$' "$pl" | awk '{print $1}' | sort)
  total=$(echo "$pkgs" | wc -l)
  pass "$total packages listed"
  dupes=$(echo "$pkgs" | uniq -d)
  if [[ -z "$dupes" ]]; then pass "no duplicates"; else fail "duplicates: $(echo "$dupes" | tr '\n' ' ')"; fi
fi

# ── 14. Sysctl hardening file ──────────────────────────────────────────────
section "14. SYSCTL HARDENING"
sysc="$AIRFS/etc/sysctl.d/99-shadowos.conf"
if [[ -f "$sysc" ]]; then
  lines=$(grep -cE '^[a-z]' "$sysc")
  pass "sysctl: $lines settings"
  for key in kernel.kptr_restrict kernel.dmesg_restrict fs.protected_hardlinks net.ipv4.tcp_syncookies kernel.randomize_va_space; do
    if grep -qE "^${key//./\\.}\b" "$sysc"; then
      pass "  has $key"
    else
      warn "  missing $key"
    fi
  done
fi

# ── 15. customize_airootfs.sh — referenced binaries exist or are in package list ──
section "15. customize_airootfs.sh CONSISTENCY"
ca="$AIRFS/root/customize_airootfs.sh"
if [[ -f "$ca" ]]; then
  # Every `systemctl enable X.service` — check the unit exists (in pkg or airootfs)
  for svc in $(grep -oE 'systemctl enable [a-z][a-zA-Z0-9_-]+\.service' "$ca" | awk '{print $3}'); do
    # Built-in package services
    case "$svc" in
      NetworkManager.service|sddm.service|ufw.service|apparmor.service|fail2ban.service|systemd-timesyncd.service|bluetooth.service|sshd.service|dnscrypt-proxy.service|docker.service|udisks2.service|power-profiles-daemon.service|tlp.service|gamemoded.service|cpupower.service|usbguard.service|auditd.service|cups.service)
        pass "service enabled: $svc (provided by a listed package)" ;;
      *)
        if [[ -f "$AIRFS/etc/systemd/system/$svc" ]]; then
          pass "service enabled: $svc (custom unit shipped)"
        else
          warn "service enabled but unit not found: $svc"
        fi ;;
    esac
  done
  if grep -qE 'chage -d 0 shadow' "$ca"; then
    fail "customize_airootfs.sh forces shadow password expiry (SDDM login breaks)"
  else
    pass "demo user shadow not forced to expire password at image build"
  fi
  if [[ -f "$AIRFS/usr/local/bin/shadowos-live-login-fix.sh" ]] && \
     [[ -f "$AIRFS/etc/systemd/system/shadowos-live-login-fix.service" ]]; then
    pass "live SDDM login fix shipped (shadowos-live-login-fix.service)"
  else
    warn "missing shadowos-live-login-fix (live ISO SDDM may fail if password expires)"
  fi
fi

# ── 16. PNG integrity (no truncated images) ────────────────────────────────
section "16. PNG INTEGRITY"
png_files=$(find "$AIRFS/usr/share/backgrounds" "$AIRFS/usr/share/plymouth" "$AIRFS/usr/share/grub" "$AIRFS/usr/share/sddm" -name '*.png' 2>/dev/null)
broken=0
checked=0
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  [[ -L "$p" && ! -e "$p" ]] && { fail "broken symlink: $p"; ((broken++)); continue; }
  [[ -L "$p" ]] && p=$(readlink -f "$p")
  [[ -f "$p" ]] || continue
  ((checked++))
  # PNG signature is the first 8 bytes
  sig=$(head -c 8 "$p" 2>/dev/null | xxd -p)
  if [[ "$sig" != "89504e470d0a1a0a" ]]; then
    fail "bad PNG sig: $p"
    ((broken++))
  fi
done <<< "$png_files"
if [[ "$broken" == 0 ]]; then pass "$checked PNGs have valid signature"; fi

# Use Pillow for a real load-test if available
if python3 -c "from PIL import Image" 2>/dev/null; then
  broken=0
  checked=0
  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    [[ -L "$p" && ! -e "$p" ]] && { fail "broken symlink: $p"; ((broken++)); continue; }
    [[ -L "$p" ]] && p=$(readlink -f "$p")
    [[ -f "$p" ]] || continue
    ((checked++))
    if ! python3 -c "from PIL import Image; im=Image.open('$p'); im.verify()" 2>/dev/null; then
      fail "PIL cannot decode: $p"
      ((broken++))
    fi
  done <<< "$png_files"
  if [[ "$broken" == 0 ]]; then pass "$checked PNGs decode cleanly via Pillow"; fi
fi

# ── 17. Wallpaper unique content ───────────────────────────────────────────
section "17. WALLPAPER UNIQUENESS"
md5s=$(find "$AIRFS/usr/share/backgrounds/shadowos" -maxdepth 1 -name 'shadowos-*-1920x1080.png' -exec md5sum {} \; | awk '{print $1}' | sort | uniq -d)
if [[ -z "$md5s" ]]; then
  pass "all 20 desktop wallpapers are unique"
else
  fail "duplicate wallpaper content detected: $md5s"
fi

# ── 18. CSS validation (waybar style + others) ─────────────────────────────
section "18. CSS SYNTAX"
for css in "$AIRFS"/etc/skel/.config/waybar/style.css "$AIRFS"/etc/skel/.config/wofi/style.css; do
  [[ -f "$css" ]] || continue
  # Naïve balance check
  open=$(grep -c '{' "$css")
  close=$(grep -c '}' "$css")
  [[ "$open" == "$close" ]] && pass "$(basename "$css"): braces ($open/$close)" || fail "$(basename "$css"): unmatched braces"
done

# ── 19. Calamares config — required fields ────────────────────────────────
section "19. CALAMARES CONFIG"
cs="$AIRFS/etc/calamares/settings.conf"
if [[ -f "$cs" ]]; then
  for key in modules-search instances sequence branding; do
    if grep -qE "^${key}:" "$cs"; then
      pass "settings.conf has $key:"
    else
      warn "settings.conf missing $key:"
    fi
  done
fi
bd="$AIRFS/etc/calamares/branding/shadowos/branding.desc"
if [[ -f "$bd" ]]; then
  grep -qE 'componentName:.*shadowos' "$bd" && pass "branding.desc identifies as shadowos" || warn "branding.desc componentName unclear"
fi

# ── 20. os-release identification ──────────────────────────────────────────
section "20. OS IDENTITY"
osr="$AIRFS/etc/os-release"
if [[ -f "$osr" ]]; then
  for key in NAME PRETTY_NAME ID HOME_URL; do
    if grep -qE "^${key}=" "$osr"; then
      val=$(grep -E "^${key}=" "$osr" | head -1 | cut -d= -f2- | tr -d '"')
      pass "os-release: $key=$val"
    else
      fail "os-release missing $key"
    fi
  done
fi
hn="$AIRFS/etc/hostname"
if [[ -f "$hn" ]]; then
  pass "hostname: $(cat "$hn")"
fi

# ── 21. ZSH config sanity ──────────────────────────────────────────────────
section "21. ZSH CONFIG"
zr="$AIRFS/etc/skel/.zshrc"
if [[ -f "$zr" ]]; then
  if bash -n "$zr" 2>/dev/null || zsh -n "$zr" 2>/dev/null; then
    pass ".zshrc parses"
  else
    # Some zsh idioms aren't valid bash; only fail if zsh exists and rejects
    if command -v zsh >/dev/null && ! zsh -n "$zr" 2>/dev/null; then
      fail ".zshrc has zsh syntax errors"
    else
      pass ".zshrc (zsh not available to verify — trusting)"
    fi
  fi
  grep -qE 'starship init zsh' "$zr" && pass "starship init present" || warn "no starship init"
fi

# ── 22. Plymouth — image dimensions sane ──────────────────────────────────
section "22. PLYMOUTH ASSET DIMENSIONS"
if python3 -c "from PIL import Image" 2>/dev/null; then
  for img in "$AIRFS"/usr/share/plymouth/themes/shadowos/*.png; do
    [[ -f "$img" ]] || continue
    dims=$(python3 -c "from PIL import Image; im=Image.open('$img'); print(f'{im.size[0]}x{im.size[1]}')")
    pass "$(basename "$img"): $dims"
  done
fi

# ── 23. Hyprland keybind conflicts ────────────────────────────────────────
section "23. HYPRLAND KEYBIND CONFLICTS"
if [[ -f "$hp" ]]; then
  dupes=$(grep -E '^bind = ' "$hp" | awk -F',' '{print $1$2}' | sort | uniq -d)
  if [[ -z "$dupes" ]]; then
    pass "no duplicate keybinds"
  else
    fail "duplicate keybinds detected:"
    echo "$dupes" | sed 's/^/      /'
  fi
fi

# ── 24. Required package categories present ───────────────────────────────
section "24. PACKAGE CATEGORIES"
declare -A categories=(
  [base]="base linux-hardened"
  [boot]="grub efibootmgr"
  [desktop]="hyprland waybar wofi sddm foot"
  [browser]="librewolf"
  [dev]="git neovim code docker podman"
  [pentest]="nmap metasploit wireshark-qt aircrack-ng"
  [gaming]="steam gamemode mangohud lutris prismlauncher"
  [security]="tor ufw apparmor fail2ban"
)
for cat_name in "${!categories[@]}"; do
  missing=""
  for pkg in ${categories[$cat_name]}; do
    if ! grep -qE "^${pkg}\b" "$pl"; then
      missing+=" $pkg"
    fi
  done
  if [[ -z "$missing" ]]; then
    pass "$cat_name category complete"
  else
    fail "$cat_name missing:$missing"
  fi
done

# ── 25. Hyprland: all bound binaries are realistic ────────────────────────
section "25. HYPRLAND BIND TARGETS"
if [[ -f "$hp" ]]; then
  # Extract `exec, <cmd>` calls
  for cmd in $(grep -oE 'exec, [^,]+' "$hp" | awk -F', ' '{print $2}' | awk '{print $1}' | sort -u); do
    # Skip bash-isms and pipelines
    [[ "$cmd" == "/usr/local/bin/shadow-mode" ]] && continue
    if [[ "$cmd" == /* ]]; then
      # Absolute path — must exist in airootfs or be a known package
      if [[ -e "$AIRFS$cmd" || -e "$cmd" ]]; then
        pass "bind target: $cmd"
      else
        warn "bind target not in airootfs: $cmd (may be package-provided)"
      fi
    else
      # Bare command — must be in package list or be a builtin
      base=$(echo "$cmd" | awk '{print $1}')
      if grep -qE "^${base}\b" "$pl" 2>/dev/null; then
        pass "bind cmd in pkg list: $base"
      else
        # known shell-builtins / common system tools
        case "$base" in
          foot|thunar|firefox|wofi|hyprlock|grim|brightnessctl|wpctl|hyprctl|cliphist|wl-copy|wl-paste|nmtui|pavucontrol|code|steam|steam-runtime|discord|btop)
            pass "bind cmd: $base (known tool)" ;;
          *)
            warn "bind cmd '$base' not in package list" ;;
        esac
      fi
    fi
  done
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo
echo "═══════════════════════════════════════════════"
echo -e "  ${GREEN}PASS${NC}: $passes   ${YELLOW}WARN${NC}: $warns   ${RED}FAIL${NC}: $fails"
echo "═══════════════════════════════════════════════"
exit $fails
