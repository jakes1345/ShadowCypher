# Vendor notes

Per-vendor notes for Lenovo, Dell, HP and ASUS machines. Each folder has the same four files:

| File | Contents |
|---|---|
| `BIOS-settings.md` | Suggested firmware settings: Secure Boot, TPM, virtualization, power |
| `quirks.md` | Known hardware problems and workarounds |
| `drivers-to-install.txt` | Package names, one per line, with comments |
| `kernel-params.conf` | INI-style sections (`[cpu]`, `[io]`, `[memory]`, `[power]`, `[security]`) with tuning values |

Nothing uses these files. The ISO build, the installer and `install-drivers.sh` don't read them, and none of the content has been checked on real hardware as part of this repo. Read them as notes.

## Before you use them

- `kernel-params.conf` isn't in any format a tool understands. It isn't a sysctl file, so don't copy it into `/etc/sysctl.d/`, and it isn't a kernel command line either. Apply the values you want by hand (for example with `cpupower`, a udev rule for the I/O scheduler, or `/etc/sysctl.d/`).
- Each `kernel-params.conf` sets `selinux_mode=enforcing`. ShadowOS uses AppArmor, not SELinux.
- The `drivers-to-install.txt` lists can't be piped straight into `pacman`. Some names aren't Arch packages (`intel-microcode` should be `intel-ucode`, `megaraid_sas` is a kernel module, and several Dell, HP and ASUS management tools aren't in the official repos). They also list `pulseaudio`, which conflicts with the `pipewire-pulse` that ShadowOS ships, and `tpm2-pytss`, which is a Python library.
- The folder titles don't always match the hardware: ProBook is an HP line, not ASUS.

## Adding a vendor

Copy one of the existing folders and keep the same four file names. Say in `quirks.md` which models you actually tested on.
