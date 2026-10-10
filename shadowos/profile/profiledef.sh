#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="shadowos"
iso_label="SHADOWOS_$(date +%Y%m)"
iso_publisher="ShadowCypher <https://shadowcypher.site>"
iso_application="ShadowOS Live/Install Medium"
iso_version="3.0.0-$(date +%Y.%m.%d)"
install_dir="shadowos"
buildmodes=('iso')
bootmodes=('bios.syslinux' 'uefi.grub')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '3' '-b' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:0400"
  ["/root"]="0:0:0700"
  ["/root/customize_airootfs.sh"]="0:0:0755"
  ["/etc/skel/.ssh"]="0:0:0700"
  # Core scripts
  ["/usr/local/bin/shadow-stream"]="0:0:0755"
  ["/usr/local/bin/shadow-wipe"]="0:0:0755"
  ["/usr/local/bin/shadow-mode"]="0:0:0755"
  ["/usr/local/bin/shadow-mode-bar"]="0:0:0755"
  ["/usr/local/bin/shadow-term"]="0:0:0755"
  ["/usr/local/bin/shadow-power-menu"]="0:0:0755"
  ["/usr/local/bin/shadow-bios"]="0:0:0755"
  ["/usr/local/bin/shadow-score"]="0:0:0755"
  ["/usr/local/bin/shadow-ai-overlay"]="0:0:0755"
  ["/usr/local/bin/shadow-help-me"]="0:0:0755"
  ["/usr/local/bin/shadow-help-me-stop"]="0:0:0755"
  ["/usr/local/bin/shadow-leak-test"]="0:0:0755"
  ["/usr/local/bin/shadow-play"]="0:0:0755"
  ["/usr/local/bin/shadow-settings"]="0:0:0755"
  ["/usr/local/bin/shadow-update"]="0:0:0755"
  ["/usr/local/bin/shadow-update-count"]="0:0:0755"
  # ShadowOS system scripts
  ["/usr/local/bin/shadowos-firstboot"]="0:0:0755"
  ["/usr/local/bin/shadowos-session-start"]="0:0:0755"
  ["/usr/local/bin/shadowos-install"]="0:0:0755"
  ["/usr/local/bin/shadowos-welcome"]="0:0:0755"
  ["/usr/local/bin/shadowos-tour"]="0:0:0755"
  ["/usr/local/bin/shadowos-ai-setup"]="0:0:0755"
  ["/usr/local/bin/shadowos-diag"]="0:0:0755"
  ["/usr/local/bin/shadowos-update-gui"]="0:0:0755"
  ["/usr/local/bin/shadowos-vpn-killswitch"]="0:0:0755"
  ["/usr/local/bin/shadowos-mac-randomize"]="0:0:0755"
  ["/usr/local/bin/shadowos-theme-apply"]="0:0:0755"
  ["/usr/local/bin/shadowcypher-autostart"]="0:0:0755"
  # Guardian daemon
  ["/usr/local/bin/guardian-launch"]="0:0:0755"
  ["/usr/local/bin/guardian-logs"]="0:0:0755"
  ["/usr/local/bin/guardian-status"]="0:0:0755"
  ["/usr/local/bin/guardian-stop"]="0:0:0755"
  # Modes — 3 only: normal, privacy, ghost
  ["/etc/shadowos/modes/normal/apply.sh"]="0:0:0755"
  ["/etc/shadowos/modes/privacy/apply.sh"]="0:0:0755"
  ["/etc/shadowos/modes/privacy/revert.sh"]="0:0:0755"
  ["/etc/shadowos/modes/ghost/apply.sh"]="0:0:0755"
  ["/etc/shadowos/modes/ghost/revert.sh"]="0:0:0755"
  ["/etc/shadowos/modes/_network_open.sh"]="0:0:0755"
)
