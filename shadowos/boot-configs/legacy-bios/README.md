# Legacy BIOS Boot Configuration

This directory contains boot configuration files for systems using traditional BIOS firmware.

## Overview

Legacy BIOS is the original firmware standard predating UEFI. It provides:

- Master Boot Record (MBR) bootloader support
- GRUB2 bootloader configuration
- Compatibility with older hardware
- Traditional partition table support (MBR or GPT BIOS mode)
- Serial console support for remote access

## Files

### boot.conf
GRUB2 configuration for legacy BIOS systems. Includes:
- GRUB bootloader installation settings
- MBR configuration
- Boot partition mount options
- BIOS boot partition settings for GPT
- Boot menu configuration

### kernel-params.txt
Kernel command-line parameters optimized for legacy BIOS. Includes:
- Console settings for serial and TTY
- Security parameters (AppArmor)
- Memory settings appropriate for older systems
- ACPI and PCI compatibility flags
- Legacy feature support (noapic, nolapic)

## Usage

1. Create boot partition:
```bash
mkfs.ext4 /dev/sda1
mount /dev/sda1 /boot
```

2. Install GRUB to MBR:
```bash
grub-install --target=i386-pc --boot-directory=/boot /dev/sda
```

3. Generate GRUB configuration:
```bash
grub-mkconfig -o /boot/grub/grub.cfg
```

4. Copy kernel parameters:
```bash
cp kernel-params.txt /etc/default/grub
```

## Partition Table Considerations

### MBR (Master Boot Record)
- Maximum 4 primary partitions
- Bootable flag must be set on boot partition
- Partition addresses stored in first 512 bytes
- Limited to 2TB drives

### GPT with BIOS Mode
- Modern partition table with MBR compatibility
- Requires 1MB BIOS boot partition (EF02)
- Supports larger drives and more partitions
- Firmware boots via MBR, kernel via GPT

## GRUB Configuration

Example /boot/grub/grub.cfg entry:
```
menuentry 'ShadowOS' {
    search --no-floppy --label shadowos --set root
    linux /vmlinuz root=/dev/mapper/shadowos-root $(cat /proc/cmdline)
    initrd /initramfs.img
}
```

## Serial Console (Optional)

For remote access via serial console:
1. Connect serial port to system
2. Configure GRUB: `serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1`
3. Add `console=ttyS0,115200n8` to kernel parameters

## Troubleshooting

### GRUB fails to install
- Verify /dev/sda is correct boot device
- Ensure boot partition is mounted
- Check GRUB modules exist: `ls /usr/lib/grub/i386-pc/`
- Install GRUB again: `grub-install --recheck /dev/sda`

### MBR corrupted
- Restore MBR without wiping partition table: `grub-install --force-file-system-type=ext4 /dev/sda`
- Use recovery boot media if needed

### System doesn't recognize GPT
- Verify hybrid MBR exists: `gdisk /dev/sda`
- Check BIOS boot partition: `parted /dev/sda set 1 bios_grub on`

## References

- GRUB2 documentation: https://www.gnu.org/software/grub/manual/
- Linux Kernel documentation
- Arch Linux BIOS boot wiki
