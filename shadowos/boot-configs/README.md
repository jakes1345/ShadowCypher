# Boot configuration notes

Reference settings for four boot setups: UEFI, legacy BIOS, Secure Boot and TPM 2.0. Each folder has a `boot.conf`, a `kernel-params.txt` and a README.

Nothing reads these files. The ISO build doesn't use them (the live ISO boots with `profile/grub/grub.cfg` on UEFI and `profile/syslinux/` on BIOS), and neither the installer nor any script applies them. Treat them as notes, not as configs you can drop in.

Before using anything from here, know that:

- `boot.conf` is a list of `KEY=value` settings that no bootloader or tool understands. Some values are placeholders, such as the attestation server in `tpm/boot.conf`.
- `kernel-params.txt` puts one parameter per line with comments, so it isn't a kernel command line you can paste. Several entries are sysctl names (`kernel.kptr_restrict=…` and similar), which belong in `/etc/sysctl.d/`, and ShadowOS already sets them in `99-shadowos.conf`. Others aren't real kernel parameters at all. Each folder's README lists what to look out for.
- The UEFI, Secure Boot and TPM files include `nokaslr`, which turns kernel address randomization off. That works against the hardening these files are meant for.
- All four assume a root device of `/dev/mapper/shadowos-root`.

## Picking a folder

`../detect-hardware.sh` reports the boot mode, CPU, GPU, TPM, Secure Boot state, RAM and disks, and prints a recommendation: `uefi`, `legacy-bios`, `secure-boot`, `tpm` or `secure-boot-tpm`. There is no `secure-boot-tpm` folder. Add `--json` for machine-readable output.

```bash
cd shadowos
./detect-hardware.sh --verbose
```

## See also

- `../enterprise/SECURE_BOOT.md` and `../enterprise/TPM2_INTEGRATION.md`
- Kernel parameters: https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html
