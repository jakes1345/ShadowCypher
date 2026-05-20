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
systemctl enable sshd.service
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

# Live user
useradd -m -G wheel,audio,video,storage,network,docker,wheel -s /usr/bin/zsh shadow || true
echo "shadow:shadow" | chpasswd
echo "root:shadow"   | chpasswd
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
chmod +x /opt/shadowcypher/launch.sh 2>/dev/null || true
find /etc/shadowos/modes -name "apply.sh" -exec chmod +x {} \; 2>/dev/null || true

# Initial mode = normal
mkdir -p /var/lib/shadowos
echo "normal" > /var/lib/shadowos/current-mode

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

# BlackArch repo keyring
if [ ! -f /etc/pacman.d/blackarch-keyring ]; then
    curl -fsSL https://blackarch.org/keyring/blackarch-keyring.pkg.tar.zst \
        -o /tmp/blackarch-keyring.pkg.tar.zst 2>/dev/null \
        && pacman -U --noconfirm /tmp/blackarch-keyring.pkg.tar.zst 2>/dev/null \
        || echo "BlackArch keyring import skipped"
fi

# Chaotic-AUR keyring — needed for librewolf, mullvad-browser, freetube-bin etc.
if ! pacman-key --list-keys 3056513887B78AEB 2>/dev/null | grep -q chaotic; then
    pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com 2>/dev/null || true
    pacman-key --lsign-key 3056513887B78AEB 2>/dev/null || true
fi

# Add plymouth hook to mkinitcpio so the splash actually shows
# (Idempotent: only inserts plymouth if not already present.)
if [ -f /etc/mkinitcpio.conf ] && ! grep -E '^HOOKS=.*plymouth' /etc/mkinitcpio.conf >/dev/null 2>&1; then
    sed -i 's/^HOOKS=(\(.*\)udev\(.*\))/HOOKS=(\1udev plymouth\2)/' /etc/mkinitcpio.conf
fi
mkinitcpio -P || true
