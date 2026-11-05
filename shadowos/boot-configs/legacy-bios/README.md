# Legacy BIOS

Notes for installing GRUB on a BIOS machine, on either an MBR disk or a GPT disk with a BIOS boot partition. Nothing in the build or installer uses these files; see [`../README.md`](../README.md). The live ISO boots BIOS machines with syslinux, not GRUB.

## Files

- `boot.conf`: GRUB paths, `/dev/sda1` as `/boot` and `/dev/sda` as the install target, a 1 MB BIOS boot partition (type EF02) for GPT, a 10-second timeout.
- `kernel-params.txt`: root device, serial and TTY consoles, AppArmor and some compatibility options.

## Problems in `kernel-params.txt`

- `mem=exact` isn't valid; `mem=` takes a size.
- `nohz_full=` is empty.
- `iommu=force` and `acpi=force` can stop older machines from booting, which is the hardware this folder is for. Only add them if you need them.
- `kernel.kptr_restrict`, `kernel.dmesg_restrict` and `kernel.printk` are sysctls, already set in `/etc/sysctl.d/99-shadowos.conf`.

## Using it

Don't copy `kernel-params.txt` over `/etc/default/grub`; that replaces the whole GRUB config. Put the parameters you keep in `GRUB_CMDLINE_LINUX_DEFAULT` instead, then:

```bash
grub-install --target=i386-pc /dev/sdX
grub-mkconfig -o /boot/grub/grub.cfg
```

For a serial console, add `console=ttyS0,115200n8` to the kernel parameters and set `GRUB_TERMINAL` and `GRUB_SERIAL_COMMAND` in `/etc/default/grub`.

## References

- GRUB manual: https://www.gnu.org/software/grub/manual/
