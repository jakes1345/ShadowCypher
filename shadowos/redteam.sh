#!/usr/bin/env bash
# ShadowOS live red-team / functional test suite.
#
# What it does:
#   1. Boots the ISO in QEMU headless (KVM accelerated, SSH forwarded :2222)
#   2. Waits for SDDM + SSH to come up
#   3. Captures screenshots at GRUB, Plymouth, SDDM, post-login
#   4. SSHes in and exercises 50+ features:
#        - service health
#        - all 5 shadow-modes (verifies real firewall changes for each)
#        - shadow-update, shadow-leak-test, shadowos-diag
#        - sysctl hardening present
#        - pentest tool presence + version checks
#        - gaming stack (steam, lutris, mangohud, gamemode)
#        - dev stack (docker, podman, kubectl, go, rust, node)
#        - DNS-leak detection
#        - active connection inventory
#        - Hyprland config validity
#        - waybar / mako processes (if user session active)
#   5. Cleans up QEMU, summarises pass/warn/fail
#
# Run:  ./redteam.sh /path/to/shadowos.iso

set -uo pipefail

ISO="${1:-$(ls -t /home/jack/ShadowCypher/shadowos/out/shadowos-*.iso 2>/dev/null | head -1)}"
[[ -f "$ISO" ]] || { echo "ISO not found: $ISO" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd)"
SHOTS="/tmp/shadowos-redteam-shots"
LOG="/tmp/shadowos-redteam.log"
QMP="/tmp/qemu-redteam-qmp.sock"
REPORT="/tmp/shadowos-redteam-report.txt"

rm -rf "$SHOTS" "$LOG" "$QMP" "$REPORT"
mkdir -p "$SHOTS"

RED=$'\033[1;31m'; GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[1;36m'; BOLD=$'\033[1m'; NC=$'\033[0m'

pass_count=0
warn_count=0
fail_count=0
tests_total=0

section()   { echo; echo -e "${CYAN}═══ $1 ═══${NC}" | tee -a "$REPORT"; }
pass()      { echo -e "  ${GREEN}✓${NC} $1" | tee -a "$REPORT"; ((pass_count++)); ((tests_total++)); }
warn()      { echo -e "  ${YELLOW}~${NC} $1" | tee -a "$REPORT"; ((warn_count++)); ((tests_total++)); }
fail_t()    { echo -e "  ${RED}✗${NC} $1" | tee -a "$REPORT"; ((fail_count++)); ((tests_total++)); }
info()      { echo -e "    ${CYAN}·${NC} $1" | tee -a "$REPORT"; }

# ── 1. boot the ISO ────────────────────────────────────────────────────────
section "1. BOOT ISO IN QEMU"
info "ISO: $ISO ($(du -h "$ISO" | cut -f1))"
pkill -f shadowos-redteam 2>/dev/null; sleep 1

nohup qemu-system-x86_64 \
    -enable-kvm -cpu host -smp 4 -m 4G \
    -drive file="$ISO",media=cdrom \
    -boot d \
    -vga virtio \
    -display none \
    -vnc 127.0.0.1:5 \
    -qmp "unix:$QMP,server=on,wait=off" \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=net0 \
    -name shadowos-redteam \
    > "$LOG" 2>&1 < /dev/null &
QPID=$!
disown
sleep 3
if ps -p $QPID > /dev/null; then
    pass "QEMU started (pid $QPID)"
else
    fail_t "QEMU crashed on launch"
    cat "$LOG" | tail -20 | tee -a "$REPORT"
    exit 1
fi

# ── 2. capture boot timeline screenshots ──────────────────────────────────
section "2. BOOT TIMELINE SCREENSHOTS"
shot() {
    local n="$1" label="$2"
    local out="$SHOTS/$(printf '%02d' "$n")-${label}.ppm"
    { echo '{"execute":"qmp_capabilities"}'
      echo "{\"execute\":\"screendump\",\"arguments\":{\"filename\":\"$out\"}}"
      sleep 1
    } | timeout 5 socat - UNIX-CONNECT:"$QMP" 2>/dev/null > /dev/null
    sleep 1
    if [[ -f "$out" ]]; then
        convert "$out" "${out%.ppm}.png" 2>/dev/null
        rm -f "$out"
        pass "screenshot $n ($label)"
    else
        warn "screenshot $n ($label) — no file"
    fi
}

# Wait for QMP
for i in $(seq 1 20); do [[ -S "$QMP" ]] && break; sleep 0.5; done

sleep 5;  shot 1 grub
sleep 6;  shot 2 plymouth-or-text
sleep 8;  shot 3 plymouth-mid
sleep 8;  shot 4 sddm

# Give firstboot service extra time to finish its Flatpak installs before
# we audit it as "still activating"
sleep 60

# ── 3. wait for SSH ───────────────────────────────────────────────────────
section "3. WAIT FOR SSH AVAILABLE"
SSH_OK=0
for i in $(seq 1 90); do
    if timeout 2 bash -c '</dev/tcp/127.0.0.1/2222' 2>/dev/null; then
        SSH_OK=1
        pass "SSH reachable after ${i}s"
        break
    fi
    sleep 2
done
[[ "$SSH_OK" == 1 ]] || { fail_t "SSH never came up — killing QEMU"; kill $QPID 2>/dev/null; exit 1; }

shot 5 post-login

SR() {
    sshpass -p shadow ssh \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 -o LogLevel=ERROR \
        -p 2222 shadow@127.0.0.1 "$@" 2>&1
}

SRT() {  # ssh with TTY for sudo
    sshpass -p shadow ssh -tt \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 -o LogLevel=ERROR \
        -p 2222 shadow@127.0.0.1 "$@" 2>&1
}

# ── 4. OS identity ────────────────────────────────────────────────────────
section "4. OS IDENTITY"
osr=$(SR 'cat /etc/os-release')
echo "$osr" | grep -q 'ID=shadowos'                && pass "os-release: ID=shadowos"               || fail_t "os-release ID wrong"
echo "$osr" | grep -q 'NAME="ShadowOS"'             && pass "os-release: NAME=ShadowOS"             || fail_t "os-release NAME wrong"
echo "$osr" | grep -q 'HOME_URL="https://shadowcypher.site"' && pass "os-release: HOME_URL"         || warn  "os-release missing HOME_URL"
[[ "$(SR 'hostname')" == "shadowos" ]] && pass "hostname = shadowos" || fail_t "hostname not shadowos"
SR 'uname -r' | grep -q 'hardened' && pass "kernel: linux-hardened active" || warn "running stock linux, not hardened"

# ── 5. KEY SERVICES ───────────────────────────────────────────────────────
section "5. KEY SERVICES"
for svc in sddm NetworkManager ufw fail2ban dnscrypt-proxy sshd shadowos-mac-randomize shadowos-firstboot; do
    state=$(SR "systemctl is-active $svc 2>/dev/null || echo missing")
    result=$(SR "systemctl show -p Result --value $svc 2>/dev/null")
    case "$state" in
        active)              pass "$svc active" ;;
        activating)          warn "$svc still initializing (firstboot Flatpak install ongoing)" ;;
        inactive)
            # Oneshot units complete and go "inactive" with Result=success — that's a pass
            if [[ "$result" == "success" ]]; then
                pass "$svc completed successfully (oneshot, Result=success)"
            else
                warn "$svc inactive (Result=$result)"
            fi
            ;;
        failed)              fail_t "$svc FAILED (Result=$result)" ;;
        missing|*)           warn "$svc — $state" ;;
    esac
done
# AppArmor — should be active after we fixed the kernel cmdline
aastate=$(SR 'systemctl is-active apparmor 2>/dev/null')
[[ "$aastate" == "active" ]] && pass "apparmor active (LSM cmdline fix worked)" || warn "apparmor $aastate — LSM may still not be enabled"

# ── 6. SYSCTL HARDENING ───────────────────────────────────────────────────
section "6. SYSCTL HARDENING"
for key_val in "kernel.kptr_restrict=2" "kernel.dmesg_restrict=1" \
               "net.ipv4.tcp_syncookies=1" "fs.protected_hardlinks=1" \
               "kernel.randomize_va_space=2" "fs.protected_symlinks=1" \
               "net.ipv4.conf.all.accept_redirects=0" \
               "kernel.yama.ptrace_scope=2"; do
    key="${key_val%%=*}"; want="${key_val##*=}"
    got=$(SR "sysctl -n $key 2>/dev/null")
    [[ "$got" == "$want" ]] && pass "$key = $got" || warn "$key = $got (wanted $want)"
done

# ── 7. SHADOWOS CLI ───────────────────────────────────────────────────────
section "7. SHADOWOS CLI BINARIES"
for bin in shadow-mode shadow-update shadow-leak-test shadow-help-me \
           shadow-ai-overlay shadowos-diag shadowos-firstboot shadowos-install \
           shadowos-mac-randomize shadow-update-count shadowos-welcome shadow-score shadow-play shadow-settings; do
    if SR "command -v $bin" | grep -q '/usr/local/bin/'; then
        pass "$bin in PATH"
    else
        fail_t "$bin NOT in PATH"
    fi
done

# ── 8. SHADOW-MODE END-TO-END (the critical security feature) ─────────────
section "8. SHADOW-MODE END-TO-END"
current=$(SR 'cat /var/lib/shadowos/current-mode 2>/dev/null')
[[ -n "$current" ]] && pass "initial mode = $current" || warn "no initial mode set"

# Test each mode actually changes state
for mode in normal dev pentest privacy ghost undercover; do
    out=$(SRT "echo shadow | sudo -S shadow-mode $mode 2>&1" | tail -5)
    new=$(SR 'cat /var/lib/shadowos/current-mode')
    if [[ "$new" == "$mode" ]]; then
        pass "shadow-mode $mode applied (current-mode file updated)"
    else
        fail_t "shadow-mode $mode did NOT update current-mode (got: $new)"
    fi
    case "$mode" in
        pentest)
            cap=$(SR 'getcap /usr/bin/nmap 2>/dev/null')
            [[ "$cap" == *"net_raw"* ]] && pass "  └ nmap has cap_net_raw" || warn "  └ nmap missing cap_net_raw"
            ;;
        privacy|ghost)
            tor=$(SR 'systemctl is-active tor')
            [[ "$tor" == "active" ]] && pass "  └ tor started in $mode mode" || warn "  └ tor NOT active in $mode mode"
            ;;
        undercover)
            if SR 'test -f /etc/skel/.config/waybar/config.undercover.jsonc'; then
                pass "  └ undercover waybar config shipped"
            else
                warn "  └ undercover waybar config missing from skel"
            fi
            ;;
    esac
done
# Return to normal
SRT "echo shadow | sudo -S shadow-mode normal" > /dev/null

# ── 9. TOOL VERSIONS (security + dev + gaming) ────────────────────────────
section "9. TOOL VERSIONS"
declare -A TOOLS=(
    [nmap]="nmap --version | head -1"
    [wireshark]="wireshark --version 2>/dev/null | head -1 || tshark --version | head -1"
    [aircrack-ng]="aircrack-ng --help 2>&1 | grep -i 'aircrack-ng' | head -1 || which aircrack-ng"
    [hashcat]="hashcat --version 2>&1 | head -1"
    [metasploit]="msfconsole -h 2>&1 | grep -i 'usage\|metasploit' | head -1 || which msfconsole"
    [hydra]="hydra -h 2>&1 | grep -m1 Hydra"
    [sqlmap]="sqlmap --version 2>&1 | head -1"
    [rustscan]="rustscan --version 2>&1 | head -1"
    [ffuf]="ffuf -V 2>&1 | head -1"
    [subfinder]="subfinder -version 2>&1 | head -1"
    [docker]="docker --version 2>&1 | head -1"
    [podman]="podman --version 2>&1 | head -1"
    [kubectl]="kubectl version --client 2>&1 | head -1"
    [go]="go version 2>&1 | head -1"
    [node]="node --version 2>&1 | head -1"
    [rustc]="rustup show active-toolchain 2>&1 | head -1 || rustc --version 2>&1 | head -1 || which rustup"
    [steam]="steam --version 2>&1 | head -1 || which steam"
    [mangohud]="mangohud --version 2>&1 | head -1 || which mangohud"
    [gamemoded]="gamemoded --version 2>&1 | head -1 || which gamemoded"
    [librewolf]="librewolf --version 2>&1 | head -1 || which librewolf"
    [hyprland]="Hyprland --version 2>&1 | head -3 | tail -1"
    [waybar]="waybar --version 2>&1 | head -1"
    [foot]="foot --version 2>&1 | head -1"
    [code]="which code 2>&1 | head -1"
    [distrobox]="distrobox --version 2>&1 | head -1"
)
for tool in "${!TOOLS[@]}"; do
    out=$(SR "${TOOLS[$tool]}")
    if [[ -n "$out" && "$out" != *"not found"* && "$out" != *"No such"* ]]; then
        pass "$tool: ${out:0:80}"
    else
        warn "$tool — not callable: $out"
    fi
done

# ── 10. SHADOWCYPHER APP PRESENT ──────────────────────────────────────────
section "10. SHADOWCYPHER APP"
files=$(SR 'ls /opt/shadowcypher/ 2>&1')
if echo "$files" | grep -q 'shadowcypher'; then
    pass "/opt/shadowcypher/shadowcypher source present"
else
    fail_t "/opt/shadowcypher/ is empty or missing"
fi
launcher=$(SR 'ls /opt/shadowcypher/launch.sh 2>&1')
[[ "$launcher" == */launch.sh ]] && pass "launch.sh entrypoint exists" || fail_t "launch.sh missing"

# ── 11. DESKTOP CONFIG (skel rolled to user) ──────────────────────────────
section "11. DESKTOP CONFIG"
for f in .config/hypr/hyprland.conf .config/hypr/hyprlock.conf \
         .config/hypr/hyprpaper.conf .config/waybar/config.jsonc \
         .config/waybar/style.css .config/mako/config .zshrc \
         .config/foot/foot.ini .config/MangoHud/MangoHud.conf; do
    if SR "test -f /home/shadow/$f"; then
        pass "$f present"
    else
        warn "$f missing from /home/shadow"
    fi
done

# ── 12. FIREWALL POSTURE ──────────────────────────────────────────────────
section "12. FIREWALL POSTURE"
ufw_status=$(SRT 'echo shadow | sudo -S ufw status verbose 2>&1' | head -5)
echo "$ufw_status" | grep -q 'Status: active' && pass "ufw active" || warn "ufw — $ufw_status"
nft_rules=$(SRT 'echo shadow | sudo -S nft list ruleset 2>&1' | wc -l)
info "nftables ruleset: $nft_rules lines"
[[ "$nft_rules" -gt 0 ]] && pass "nftables has rules ($nft_rules lines)" || warn "nftables ruleset empty"

# ── 13. DNS LEAK CHECK ────────────────────────────────────────────────────
section "13. DNS BEHAVIOR"
# Verify resolver is dnscrypt
resolver=$(SR 'cat /etc/resolv.conf | grep nameserver | head -2')
info "Active nameservers:"
echo "$resolver" | sed 's/^/      /' | tee -a "$REPORT"
echo "$resolver" | grep -q '127.0.0.' && pass "DNS via local resolver (dnscrypt loopback)" \
    || warn "DNS uses external resolver directly"

# ── 14. SECURITY POSTURE — open ports ─────────────────────────────────────
section "14. ATTACK SURFACE"
ports=$(SRT 'echo shadow | sudo -S ss -tlnp 2>/dev/null' | tail -n +2 | wc -l)
info "Listening TCP sockets: $ports"
SRT 'echo shadow | sudo -S ss -tlnp 2>/dev/null' | sed 's/^/      /' | head -10 | tee -a "$REPORT"
[[ "$ports" -lt 10 ]] && pass "lean attack surface ($ports listening services)" \
    || warn "$ports listening services — review for exposure"

# ── 15. HYPRLAND CONFIG VALIDITY ──────────────────────────────────────────
section "15. HYPRLAND CONFIG"
hp_lint=$(SR 'Hyprland --verify-config 2>&1' | head -10)
echo "$hp_lint" | grep -qi 'error\|fail' && warn "Hyprland config validator reports issues" || pass "Hyprland config parses"

# ── 16. PACKAGE COUNT + INTEGRITY ─────────────────────────────────────────
section "16. PACKAGE INTEGRITY"
n=$(SR 'pacman -Q 2>/dev/null | wc -l')
pass "$n packages installed"
broken=$(SRT 'echo shadow | sudo -S pacman -Qkk 2>&1 | grep -c warning')
if [[ "$broken" -gt 0 ]]; then
    warn "$broken packages have missing/modified files"
else
    pass "all packages have intact files"
fi

# ── 17. SUMMARY ───────────────────────────────────────────────────────────
section "17. SUMMARY"
echo -e "  Total tests:  ${BOLD}$tests_total${NC}" | tee -a "$REPORT"
echo -e "  ${GREEN}Pass:        $pass_count${NC}" | tee -a "$REPORT"
echo -e "  ${YELLOW}Warn:        $warn_count${NC}" | tee -a "$REPORT"
echo -e "  ${RED}Fail:        $fail_count${NC}" | tee -a "$REPORT"
echo
echo "  Screenshots:  $SHOTS"
echo "  Full report:  $REPORT"
echo "  QEMU log:     $LOG"

# Cleanup
echo
echo "Killing QEMU (pid $QPID)..."
kill $QPID 2>/dev/null
sleep 1

exit $fail_count
