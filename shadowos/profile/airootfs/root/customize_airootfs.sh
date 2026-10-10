#!/usr/bin/env bash
set -e -u

# ── Locale ────────────────────────────────────────────────────────────────────
sed -i 's/#\(en_US\.UTF-8\)/\1/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# ── Default shell ─────────────────────────────────────────────────────────────
chsh -s /usr/bin/zsh

# ── ShadowCypher pip-only deps ────────────────────────────────────────────────
pip install --break-system-packages --no-cache-dir \
    "litellm>=1.0.0" \
    "argon2-cffi>=23.0.0" \
    "paramiko>=3.0.0" \
    inquirer \
    2>/dev/null || echo "[WARNING] Some pip packages failed — non-fatal"

# ── Core services ─────────────────────────────────────────────────────────────
systemctl enable NetworkManager.service
systemctl enable iwd.service
systemctl enable sddm.service
systemctl enable nftables.service
systemctl enable apparmor.service
systemctl enable fail2ban.service
systemctl enable systemd-timesyncd.service
systemctl enable bluetooth.service
systemctl enable shadowos-mac-randomize.service
systemctl enable shadowos-firstboot.service
systemctl disable sshd.service 2>/dev/null || true   # opt-in only — security OS
systemctl enable dnscrypt-proxy.service 2>/dev/null || true
systemctl disable tor.service 2>/dev/null || true
systemctl enable udisks2.service 2>/dev/null || true
systemctl enable power-profiles-daemon.service 2>/dev/null || true
systemctl enable auditd.service 2>/dev/null || true
systemctl enable usbguard.service 2>/dev/null || true
systemctl enable systemd-zram-setup@zram0.service 2>/dev/null || true
systemctl enable shadowcypher-agent.service 2>/dev/null || true
systemctl set-default graphical.target

# ── SSH hardening ─────────────────────────────────────────────────────────────
mkdir -p /etc/ssh/sshd_config.d
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

# ── OS identity ───────────────────────────────────────────────────────────────
cat > /etc/lsb-release <<'LSB'
LSB_VERSION=1.4
DISTRIB_ID=ShadowOS
DISTRIB_RELEASE=3.0.0
DISTRIB_DESCRIPTION="ShadowOS 3.0.0"
LSB

cat > /etc/os-release <<'OSR'
NAME="ShadowOS"
PRETTY_NAME="ShadowOS 3.0.0"
ID=shadowos
ID_LIKE=arch
BUILD_ID=rolling
ANSI_COLOR="38;2;0;224;164"
HOME_URL="https://shadowcypher.site"
DOCUMENTATION_URL="https://shadowcypher.site/docs.html"
SUPPORT_URL="https://shadowcypher.site"
BUG_REPORT_URL="https://github.com/jakes1345/ShadowCypher/issues"
LOGO=shadowos
IMAGE_ID=shadowos
IMAGE_VERSION=3.0.0
OSR

echo "shadowos" > /etc/hostname

# ── Plymouth theme ────────────────────────────────────────────────────────────
plymouth-set-default-theme -R shadowos 2>/dev/null \
    || plymouth-set-default-theme shadowos 2>/dev/null \
    || plymouth-set-default-theme bgrt 2>/dev/null \
    || true

# ── GRUB theme ────────────────────────────────────────────────────────────────
mkdir -p /etc/default
if [ -f /etc/default/grub ]; then
    sed -i 's|^#\?GRUB_THEME=.*|GRUB_THEME="/boot/grub/themes/shadowos/theme.txt"|' /etc/default/grub
    grep -q '^GRUB_THEME=' /etc/default/grub \
        || echo 'GRUB_THEME="/boot/grub/themes/shadowos/theme.txt"' >> /etc/default/grub
fi

# ── Live user ─────────────────────────────────────────────────────────────────
useradd -m -G wheel,audio,video,storage,network -s /usr/bin/zsh shadow || true

# Random live password
LIVE_PASS=$(cat /proc/sys/kernel/random/uuid | tr -d '-' | head -c 16)
echo "shadow:${LIVE_PASS}" | chpasswd
passwd -l root
mkdir -p /etc/shadowos
echo "$LIVE_PASS" > /etc/shadowos/live-password
chmod 600 /etc/shadowos/live-password
chage -M 99999 -E -1 -I -1 shadow 2>/dev/null || true
echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel

# ── Populate home from skel ───────────────────────────────────────────────────
cp -rT /etc/skel /home/shadow/ || true
mkdir -p /home/shadow/.ssh
chmod 700 /home/shadow/.ssh
chmod 600 /home/shadow/.ssh/authorized_keys 2>/dev/null || true
chown -R shadow:shadow /home/shadow

# ── Hyprland session → shadowos-session-start ─────────────────────────────────
if [[ -f /usr/share/wayland-sessions/hyprland.desktop ]]; then
    sed -i 's|^Exec=.*|Exec=/usr/local/bin/shadowos-session-start|' \
        /usr/share/wayland-sessions/hyprland.desktop
fi

# ── Executable bits ───────────────────────────────────────────────────────────
for bin in \
    shadow-mode shadow-mode-bar shadow-leak-test shadow-ai-overlay shadow-bios \
    shadow-help-me shadow-help-me-stop shadow-play shadow-score shadow-settings \
    shadow-stream shadow-update shadow-update-count shadow-wipe \
    shadowos-diag shadowos-firstboot shadowos-install shadowos-mac-randomize \
    shadowos-ramwipe shadowos-session-start shadowos-theme-apply shadowos-tour \
    shadowos-update-gui shadowos-vpn-killswitch shadowos-welcome shadowos-ai-setup \
    shadow-power-menu shadow-term \
    shadowcypher-autostart guardian-launch guardian-logs guardian-status guardian-stop
do
    chmod +x "/usr/local/bin/${bin}" 2>/dev/null || true
done

find /etc/shadowos/modes -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
chmod +x /opt/shadowcypher/launch.sh 2>/dev/null || true

# ── Plymouth in mkinitcpio ────────────────────────────────────────────────────
if [ -f /etc/mkinitcpio.conf ] && ! grep -E '^HOOKS=.*plymouth' /etc/mkinitcpio.conf >/dev/null 2>&1; then
    sed -i 's/^HOOKS=(\(.*\)udev\(.*\))/HOOKS=(\1udev plymouth\2)/' /etc/mkinitcpio.conf
fi
mkinitcpio -P || true

# ── Chaotic-AUR signing key ───────────────────────────────────────────────────
if ! pacman-key --list-keys 3056513887B78AEB 2>/dev/null | grep -q chaotic; then
    pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com 2>/dev/null \
        && pacman-key --lsign-key 3056513887B78AEB 2>/dev/null \
        || echo "WARNING: Chaotic-AUR key import failed"
fi

# ── Apparmor profiles ─────────────────────────────────────────────────────────
if command -v aa-enforce >/dev/null 2>&1; then
    aa-enforce /etc/apparmor.d/usr.bin.librewolf 2>/dev/null || true
    aa-enforce /etc/apparmor.d/usr.bin.signal-desktop 2>/dev/null || true
fi

# ── Flatpak / Flathub bootstrap ───────────────────────────────────────────────
if command -v flatpak >/dev/null 2>&1; then
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
fi

# ── Initial mode = normal ─────────────────────────────────────────────────────
/etc/shadowos/modes/normal/apply.sh 2>/dev/null || true
mkdir -p /var/lib/shadowos
echo "normal" > /var/lib/shadowos/current-mode

# ── Live ISO marker ───────────────────────────────────────────────────────────
mkdir -p /etc/shadowos
date -Iseconds > /etc/shadowos/live-iso

# ── Branding ─────────────────────────────────────────────────────────────────
sed -i 's/Arch Linux/ShadowOS/g' /etc/issue || true
echo "ShadowOS \\r (\\l)" > /etc/issue

# ── MOTD ─────────────────────────────────────────────────────────────────────
LIVE_PASS_SHOW=$(cat /etc/shadowos/live-password 2>/dev/null || echo "(see /etc/shadowos/live-password)")
cat > /etc/motd <<MOTD

  ShadowOS 3.0.0 — LIVE SESSION
  ─────────────────────────────────────────────
   User: shadow   Password: ${LIVE_PASS_SHOW}
   SSH: key-only (add pubkey → ~/.ssh/authorized_keys)

  Quick reference:
   shadow-mode <name>    switch mode: normal | privacy | ghost | dev | gaming
   shadow-help-me [min]  SSH over Tor .onion for remote access
   shadow-leak-test      verify no identity leaks
   shadow-update         update packages (respects current mode)
   shadowos-diag         bundle system logs for debugging
   shadowos-install      install ShadowOS to disk

MOTD
