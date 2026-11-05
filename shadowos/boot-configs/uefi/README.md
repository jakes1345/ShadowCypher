# UEFI

Notes for a plain UEFI install with systemd-boot and the ESP mounted at `/boot/efi`. Nothing in the build or installer uses these files; see [`../README.md`](../README.md).

## Files

- `boot.conf`: ESP mount point and options, systemd-boot entry directory, kernel and initramfs paths, a 10-second timeout.
- `kernel-params.txt`: root device, serial and TTY consoles, AppArmor, IOMMU and a few memory-hardening options.

## Problems in `kernel-params.txt`

- `nokaslr` disables kernel address randomization. Remove it.
- `efi=noruntime` disables EFI runtime services, which stops `efibootmgr` and `bootctl` from reading or writing boot entries.
- `kernel.kptr_restrict`, `kernel.dmesg_restrict` and `kernel.printk` are sysctls. ShadowOS already sets them in `/etc/sysctl.d/99-shadowos.conf`.
- `tpm=crb`, `amd_iommu=force` and `intel_iommu=force` aren't valid values. The usual forms are `amd_iommu=on` (or leave it unset) and `intel_iommu=on`.

## Using it

The file isn't a loader entry, so don't copy it into `/boot/efi/loader/entries/`. If you want systemd-boot, install it with `bootctl --esp-path=/boot/efi install` and write the entry by hand, with an `options` line built from the parameters you keep. The ESP should be FAT32, partition type EF00, and at least 512 MB.

## References

- UEFI specifications: https://uefi.org/specifications
- `man bootctl`, `man loader.conf`
