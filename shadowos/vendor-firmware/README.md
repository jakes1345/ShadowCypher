# Vendor firmware

This folder is empty apart from this README. No firmware files are stored in the repo.

Firmware updates go through fwupd, using `../firmware-manager.sh`:

```bash
sudo ./firmware-manager.sh check     # refresh metadata and list available updates
sudo ./firmware-manager.sh install   # apply them (runs fwupdmgr update --allow-older)
./firmware-manager.sh list           # devices fwupd knows about
./firmware-manager.sh history        # past updates
```

Run it from the `shadowos` folder. It isn't installed into the ISO, and `fwupd` isn't in the ISO's package list, so install that first (`pacman -S fwupd`). What can be updated depends on the vendor publishing firmware to LVFS.

`install` passes `--allow-older`, so it will also accept a downgrade if one is offered.
