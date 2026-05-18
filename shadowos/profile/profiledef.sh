#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="shadowos"
iso_label="SHADOWOS_$(date +%Y%m)"
iso_publisher="ShadowCypher <https://shadowcypher.site>"
iso_application="ShadowOS Live/Install Medium"
iso_version="0.1.0-$(date +%Y.%m.%d)"
install_dir="shadowos"
buildmodes=('iso')
bootmodes=('bios.syslinux.mbr' 'bios.syslinux.eltorito' 'uefi-x64.grub.esp')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '20' '-b' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:0400"
  ["/root"]="0:0:0700"
  ["/root/customize_airootfs.sh"]="0:0:0755"
  ["/usr/local/bin/shadowos-firstboot"]="0:0:0755"
)
