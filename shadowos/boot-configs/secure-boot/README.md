# Secure Boot

Notes for running ShadowOS with UEFI Secure Boot and IMA. Nothing in the build or installer uses these files; see [`../README.md`](../README.md).

## Files

- `boot.conf`: systemd-boot paths, key and certificate paths under `/etc/secureboot/`, and flags for signing the kernel, bootloader and initramfs.
- `kernel-params.txt`: IMA appraisal, module signature enforcement, AppArmor and memory-hardening options.

## Problems

- `kernel-params.txt` includes `nokaslr`, which disables kernel address randomization, and `efi=noruntime`, which stops the system from reading or changing EFI variables, including the Secure Boot ones.
- `enforce=1` is an SELinux option; ShadowOS uses AppArmor.
- `tpm=crb`, `tpm_tis=force`, `tpm2_tis=force`, `efivarfs=secure`, `efi_load_option=0` and `ima=enforce` aren't kernel parameters.
- `kernel.kptr_restrict=3` is out of range (0 to 2), and the `kernel.*` lines are sysctls in any case.
- `ima_appraise=enforce` with no signed or hashed files will block execution. Label the filesystem first or start with `ima_appraise=fix`.
- `boot.conf` asks for a signed initramfs. An initramfs isn't a PE binary, so `sbsign` can't sign it. Use a unified kernel image if you want it covered.
- The MOK workflow (`mokutil --import`) needs shim, which ShadowOS doesn't install.

## What the image has

The ISO includes `sbctl`, `mokutil`, `efibootmgr` and `tpm2-tools`. `sbctl` can create your own keys, enroll them while the firmware is in Setup Mode, and sign the kernel and bootloader, without shim. The Arch Wiki covers both the `sbctl` and the shim routes:
https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot

Check the current state with `sbctl status` or `mokutil --sb-state`.

## References

- UEFI specifications: https://uefi.org/specifications
- Kernel parameters: https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html
