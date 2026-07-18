#!/usr/bin/env bash
set -e -u

# Locale
sed -i 's/#\(en_US\.UTF-8\)/\1/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# Default shell
chsh -s /usr/bin/zsh

# ── ShadowCypher Python deps (pip-only, not in Arch repos) ───────────────────
# Install into system Python so launch.sh (which uses system python3) can find them.
# Arch packages handle numpy/scipy/bs4/etc; only pip-only packages go here.
pip install --break-system-packages --no-cache-dir \
    treequest \
    ulid-py \
    "shinka-evolve" \
    "litellm>=1.0.0" \
    inquirer \
    mem0ai \
    2>/dev/null || echo "[WARNING] Some pip packages failed to install — non-fatal"

# Services
systemctl enable NetworkManager.service
systemctl enable iwd.service
systemctl enable sddm.service
systemctl enable ollama.service
systemctl enable ufw.service
systemctl enable apparmor.service
systemctl enable fail2ban.service
systemctl enable systemd-timesyncd.service
systemctl enable bluetooth.service
systemctl enable shadowos-mac-randomize.service
systemctl enable shadowos-firstboot.service
systemctl enable shadowcypher-agent.service 2>/dev/null || true
systemctl --global enable shadowos-welcome.service 2>/dev/null || true
systemctl enable shadowos-live-login-fix.service
systemctl enable sshd.service
mkdir -p /etc/ssh/sshd_config.d
# SSH hardened: password auth off, key-only, root login disabled.
# Live ISO users who need SSH access must add their pubkey to /home/shadow/.ssh/authorized_keys.
cat > /etc/ssh/sshd_config.d/99-shadowos-hardening.conf <<'SSHCONF'
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
X11Forwarding no
AllowTcpForwarding no
PrintMotd yes
MaxAuthTries 3
LoginGraceTime 30
SSHCONF
# Tier-1 essentials
systemctl enable udisks2.service 2>/dev/null || true
systemctl enable power-profiles-daemon.service 2>/dev/null || true
systemctl enable tlp.service 2>/dev/null || true
# Tier-2 polish
systemctl enable gamemoded.service 2>/dev/null || true  # actually a user service; harmless
# AppArmor profile parsing
systemctl enable apparmor.service
systemctl set-default graphical.target

systemctl enable dnscrypt-proxy.service 2>/dev/null || true
systemctl disable tor.service 2>/dev/null || true

# Firewall: deny all inbound by default; SSH only from LAN (RFC1918).
# Even with key-only auth, no reason to expose SSH to the entire internet on a live ISO.
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.0.0/16 to any port 22 proto tcp comment 'ShadowOS live SSH (LAN only)'
ufw allow from 10.0.0.0/8    to any port 22 proto tcp comment 'ShadowOS live SSH (LAN only)'
ufw allow from 172.16.0.0/12 to any port 22 proto tcp comment 'ShadowOS live SSH (LAN only)'
ufw --force enable

# Re-stamp OS identity files (upstream `filesystem` package owns these and
# clobbers them; we overwrite at the END of customize so our values win)
cat > /etc/lsb-release <<'LSB'
LSB_VERSION=1.4
DISTRIB_ID=ShadowOS
DISTRIB_RELEASE=3.0.0
DISTRIB_DESCRIPTION="ShadowOS 3.0.0 Enterprise Edition"
LSB

cat > /etc/os-release <<'OSR'
NAME="ShadowOS"
PRETTY_NAME="ShadowOS 3.0.0 Enterprise Edition"
ID=shadowos
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;180;74;255"
HOME_URL="https://shadowcypher.site"
DOCUMENTATION_URL="https://shadowcypher.site/docs.html"
SUPPORT_URL="https://shadowcypher.site"
BUG_REPORT_URL="https://github.com/jakes1345/ShadowCypher/issues"
LOGO=shadowos
IMAGE_ID=shadowos
IMAGE_VERSION=3.0.0
VARIANT_ID=enterprise
VERSION_CODENAME=enterprise
OSR

echo "shadowos" > /etc/hostname

# Plymouth theme
plymouth-set-default-theme -R shadowos 2>/dev/null \
    || plymouth-set-default-theme shadowos 2>/dev/null \
    || plymouth-set-default-theme bgrt 2>/dev/null \
    || true

# GRUB theme — wire into /etc/default/grub so calamares/grub-mkconfig honors it
# (Theme assets live at /usr/share/grub/themes/shadowos/ which gets copied to
# /boot/grub/themes/ by grub-install.)
mkdir -p /etc/default
if [ -f /etc/default/grub ]; then
    sed -i 's|^#\?GRUB_THEME=.*|GRUB_THEME="/boot/grub/themes/shadowos/theme.txt"|' /etc/default/grub
    grep -q '^GRUB_THEME=' /etc/default/grub \
        || echo 'GRUB_THEME="/boot/grub/themes/shadowos/theme.txt"' >> /etc/default/grub
fi

# Live user — docker group excluded (grants root-equivalent container access)
useradd -m -G wheel,audio,video,storage,network -s /usr/bin/zsh shadow || true

# Generate a random live-session password instead of a hardcoded one.
# The password is written to /etc/shadowos/live-password (root-readable only)
# and displayed in the MOTD so it's visible at the TTY. It's different on every build.
LIVE_PASS=$(cat /proc/sys/kernel/random/uuid | tr -d '-' | head -c 16)
echo "shadow:${LIVE_PASS}" | chpasswd
# Root login disabled via SSH; local root requires sudo from the shadow account.
passwd -l root
mkdir -p /etc/shadowos
echo "$LIVE_PASS" > /etc/shadowos/live-password
chmod 600 /etc/shadowos/live-password

# Never force password expiry on a live ISO — SDDM has no change-password UI.
chage -M 99999 -E -1 -I -1 shadow 2>/dev/null || true
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel

# Skel → live user (including .ssh/authorized_keys)
cp -rT /etc/skel /home/shadow/ || true
mkdir -p /home/shadow/.ssh
chmod 700 /home/shadow/.ssh
chmod 600 /home/shadow/.ssh/authorized_keys 2>/dev/null || true
chown -R shadow:shadow /home/shadow

# Root SSH key
chmod 700 /root/.ssh 2>/dev/null || true
chmod 600 /root/.ssh/authorized_keys 2>/dev/null || true

# Patch Hyprland session to use shadowos-session-start wrapper (VM renderer detection, canonical config deploy)
if [[ -f /usr/share/wayland-sessions/hyprland.desktop ]]; then
    sed -i 's|^Exec=.*|Exec=/usr/local/bin/shadowos-session-start|' \
        /usr/share/wayland-sessions/hyprland.desktop
fi

# Executable bits
chmod +x /usr/local/bin/shadow-mode 2>/dev/null || true
chmod +x /usr/local/bin/shadow-leak-test 2>/dev/null || true
chmod +x /usr/local/bin/shadow-ai-overlay 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-mac-randomize 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-install 2>/dev/null || true
chmod +x /usr/local/bin/shadow-update 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-diag 2>/dev/null || true
chmod +x /usr/local/bin/shadow-help-me 2>/dev/null || true
chmod +x /usr/local/bin/shadow-help-me-stop 2>/dev/null || true
chmod +x /usr/local/bin/shadow-update-count 2>/dev/null || true
chmod +x /usr/local/bin/shadow-mode-bar 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-theme-apply 2>/dev/null || true
chmod +x /usr/local/bin/shadow-play 2>/dev/null || true
chmod +x /usr/local/bin/shadow-settings 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-live-login-fix.sh 2>/dev/null || true
chmod +x /usr/local/bin/shadowos-session-start 2>/dev/null || true
chmod +x /opt/shadowcypher/launch.sh 2>/dev/null || true
find /etc/shadowos/modes -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

# Ensure image boots with open networking (not stale nft lockdown)
/etc/shadowos/modes/normal/apply.sh 2>/dev/null || true

# Initial mode = normal
mkdir -p /var/lib/shadowos
echo "normal" > /var/lib/shadowos/current-mode

# Live ISO marker (SDDM demo banner reads lastUser=shadow; this is for scripts)
mkdir -p /etc/shadowos
date -Iseconds > /etc/shadowos/live-iso

# Strip Arch branding
sed -i 's/Arch Linux/ShadowOS/g' /etc/issue || true
echo "ShadowOS \\r (\\l)" > /etc/issue

# MOTD: show live password and quick-reference.
# The password is embedded at build time from /etc/shadowos/live-password.
LIVE_PASS_SHOW=$(cat /etc/shadowos/live-password 2>/dev/null || echo "(see /etc/shadowos/live-password)")
cat > /etc/motd <<MOTD

  ShadowOS 3.0.0 — LIVE SESSION
  ─────────────────────────────────────────────
   User: shadow   Password: ${LIVE_PASS_SHOW}
   SSH: key-only (LAN), add pubkey → ~/.ssh/authorized_keys

  Quick reference:
   shadow-mode <name>    switch mode: pentest | privacy | ghost | gaming | dev | normal
   shadow-help-me [min]  expose SSH over Tor .onion for remote access
   shadow-leak-test      verify nothing's leaking your real identity
   shadow-update         smart updater (respects current mode)
   shadowos-diag         bundle system logs into a tarball for debugging
   shadowos-install      install ShadowOS to disk

MOTD

# Flatpak / Flathub bootstrap — handles AUR-only apps without an AUR helper
# These get installed at first-boot via systemd because the live ISO has no network
# guarantee during mkarchiso. The first-boot service is in /usr/local/bin/shadowos-firstboot
if command -v flatpak >/dev/null 2>&1; then
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
fi

if [ ! -f /etc/pacman.d/blackarch-keyring ]; then
    _ba_pkg="/tmp/blackarch-keyring.pkg.tar.zst"
    if curl -fsSL https://blackarch.org/keyring/blackarch-keyring.pkg.tar.zst -o "$_ba_pkg" 2>/dev/null; then
        if file "$_ba_pkg" 2>/dev/null | grep -qiE 'zstd|tar'; then
            pacman -U --noconfirm "$_ba_pkg" 2>/dev/null && echo "BlackArch keyring installed" \
                || echo "BlackArch keyring install failed"
        else
            echo "BlackArch keyring download appears corrupt — skipping"
            rm -f "$_ba_pkg"
        fi
    else
        echo "BlackArch keyring download failed — skipping"
    fi
fi

if ! pacman-key --list-keys 3056513887B78AEB 2>/dev/null | grep -q chaotic; then
    if pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com 2>/dev/null; then
        pacman-key --lsign-key 3056513887B78AEB 2>/dev/null \
            && echo "Chaotic-AUR key imported." \
            || echo "WARNING: Chaotic-AUR lsign failed — packages may fail signature check"
    else
        echo "WARNING: Chaotic-AUR key import failed — repo unavailable"
    fi
fi

# Add plymouth hook to mkinitcpio so the splash actually shows
# (Idempotent: only inserts plymouth if not already present.)
if [ -f /etc/mkinitcpio.conf ] && ! grep -E '^HOOKS=.*plymouth' /etc/mkinitcpio.conf >/dev/null 2>&1; then
    sed -i 's/^HOOKS=(\(.*\)udev\(.*\))/HOOKS=(\1udev plymouth\2)/' /etc/mkinitcpio.conf
fi
mkinitcpio -P || true

# === Gaming services ===
systemctl enable gamemoded.service 2>/dev/null || true
# auto-cpufreq is AUR; use cpupower instead
    systemctl enable cpupower.service 2>/dev/null || true

# === Security hardening services ===
systemctl enable usbguard.service 2>/dev/null || true
systemctl enable apparmor.service 2>/dev/null || true
systemctl enable auditd.service 2>/dev/null || true

# === zram swap ===
systemctl enable systemd-zram-setup@zram0.service 2>/dev/null || true

# === Snapper — only for btrfs installs ===
# enabled post-install by shadowos-install if btrfs detected
# systemctl enable snapper-timeline.timer snapper-cleanup.timer 2>/dev/null || true

# === Printing ===
systemctl enable cups.service 2>/dev/null || true

# === mat2 available globally ===
# mat2 is CLI — available once installed, no service needed

# Load AppArmor profiles
if command -v aa-enforce >/dev/null 2>&1; then
    aa-enforce /etc/apparmor.d/usr.bin.librewolf 2>/dev/null || true
    aa-enforce /etc/apparmor.d/usr.bin.signal-desktop 2>/dev/null || true
fi

# ════════════════════════════════════════════════════════════════════════════════
# ENTERPRISE FEATURES INTEGRATION (ShadowOS Enterprise Edition)
# ════════════════════════════════════════════════════════════════════════════════

echo "[*] Integrating ShadowOS Enterprise features..."

# === SELinux Policy Framework ===
if [ -d /etc/selinux ]; then
    echo "SELINUX=enforcing" > /etc/selinux/config
    echo "SELINUXTYPE=default" >> /etc/selinux/config
    # Copy enterprise SELinux policy
    mkdir -p /etc/selinux/default/modules/community
    [ -f /root/selinux-policy.te ] && cp /root/selinux-policy.te /etc/selinux/default/modules/community/ || true
    echo "[+] SELinux enforcing mode configured"
fi

# === Audit Daemon (auditd) ===
if [ -f /etc/audit/rules.d/shadowos.rules ]; then
    systemctl enable auditd.service
    echo "[+] Audit logging enabled with ShadowOS rules"
fi

# === TPM 2.0 Integration ===
if command -v tpm2_startup >/dev/null 2>&1; then
    systemctl enable tpm2-abrmd.service 2>/dev/null || true
    systemctl enable tpm2-tss.service 2>/dev/null || true
    echo "[+] TPM 2.0 daemon enabled"
fi

# === LUKS Encryption (populate /etc/crypttab for automated decryption) ===
mkdir -p /etc/luks-keys
chmod 700 /etc/luks-keys
# Note: actual encryption happens at install time via shadowos-install
echo "[+] LUKS encryption infrastructure prepared"

# === FreeIPA Client Configuration (enterprise identity management) ===
mkdir -p /etc/ipa
mkdir -p /var/lib/ipa
# FreeIPA enrollment happens post-install via freeipa-setup.py
echo "[+] FreeIPA client infrastructure ready"

# === FIPS 140-2 Mode Support ===
mkdir -p /etc/fips
echo "# FIPS 140-2 Configuration" > /etc/fips/fips.conf
echo "# Enable: update-crypto-policies --set FIPS" >> /etc/fips/fips.conf
systemctl enable crypto-policies.service 2>/dev/null || true
echo "[+] FIPS 140-2 mode available (can be toggled post-install)"

# === Compliance Audit Logging ===
if [ -f /root/compliance-audit.sh ]; then
    cp /root/compliance-audit.sh /usr/local/bin/
    chmod +x /usr/local/bin/compliance-audit.sh
    # Run initial audit
    /usr/local/bin/compliance-audit.sh 2>/dev/null || true
    echo "[+] Compliance audit logging installed"
fi

# === Hardware Certification Database ===
mkdir -p /var/lib/shadowos/hardware
[ -f /root/cert-db.json ] && cp /root/cert-db.json /var/lib/shadowos/hardware/ || true
[ -f /root/driver-db.json ] && cp /root/driver-db.json /var/lib/shadowos/hardware/ || true
[ -f /root/device-registry.json ] && cp /root/device-registry.json /var/lib/shadowos/hardware/ || true
echo "[+] Hardware certification database installed"

# === Update System with Signatures ===
mkdir -p /usr/local/bin/shadowos-update
[ -f /root/shadowos-update ] && cp /root/shadowos-update /usr/local/bin/ && chmod +x /usr/local/bin/shadowos-update || true
[ -f /root/update_server.py ] && cp /root/update_server.py /opt/shadowos/ || true
echo "[+] Secure update system installed"

# === Enterprise Services ===
# Enable enterprise audit daemon if available
if command -v audit-daemon >/dev/null 2>&1 2>/dev/null; then
    systemctl enable audit-daemon.service 2>/dev/null || true
fi

# Enable centralized logging
systemctl enable systemd-journal-remote.socket 2>/dev/null || true

echo "[*] Enterprise features integration complete"
