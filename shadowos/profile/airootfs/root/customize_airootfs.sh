#!/usr/bin/env bash
set -e -u

# Locale
sed -i 's/#\(en_US\.UTF-8\)/\1/' /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

# Default shell
chsh -s /usr/bin/zsh

# Services
systemctl enable NetworkManager.service
systemctl enable sddm.service
systemctl enable ufw.service
systemctl enable apparmor.service
systemctl enable fail2ban.service
systemctl enable systemd-timesyncd.service
systemctl enable bluetooth.service
systemctl enable shadowos-mac-randomize.service
systemctl enable shadowos-firstboot.service
systemctl --global enable shadowos-welcome.service 2>/dev/null || true
systemctl enable shadowos-live-login-fix.service
systemctl enable sshd.service
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-shadowos-hardening.conf <<'SSHCONF'
PasswordAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
X11Forwarding no
AllowTcpForwarding no
PrintMotd yes
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

# Firewall: open SSH for live debug access (locked down in installed system)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'ShadowOS live SSH'
ufw --force enable

# Re-stamp OS identity files (upstream `filesystem` package owns these and
# clobbers them; we overwrite at the END of customize so our values win)
cat > /etc/lsb-release <<'LSB'
LSB_VERSION=1.4
DISTRIB_ID=ShadowOS
DISTRIB_RELEASE=0.1
DISTRIB_DESCRIPTION="ShadowOS 0.1"
LSB

cat > /etc/os-release <<'OSR'
NAME="ShadowOS"
PRETTY_NAME="ShadowOS 0.1"
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
IMAGE_VERSION=0.1.0
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
echo "shadow:shadow" | chpasswd
echo "root:shadow"   | chpasswd
# Live demo user: SDDM has no "change expired password" UI — never force expiry here.
# Installed systems set their own password via shadowos-install / archinstall.
chage -M 99999 -E -1 -I -1 shadow 2>/dev/null || true
chage -d "$(date +%F)" shadow 2>/dev/null || true
# Root may still be changed at first TTY login on installed media.
chage -d 0 root 2>/dev/null || true
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

# MOTD shown over SSH and at login TTYs
cat > /etc/motd <<'EOF'

  ShadowOS  ·  command quick-reference
  ─────────────────────────────────────────────
   shadow-mode <name>    personality switcher (pentest/privacy/dev/ghost/normal)
   shadow-help-me [min]  expose SSH over a Tor .onion for remote debugging
   shadow-leak-test      verify nothing's leaking your real identity
   shadow-update         smart updater that respects current mode
   shadowos-diag         bundle journal + hyprland + system into a tarball
   shadowos-install      install ShadowOS to disk

EOF

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
