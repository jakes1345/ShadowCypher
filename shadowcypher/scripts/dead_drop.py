#!/usr/bin/env python3
"""
SHADOWCYPHER // DEAD DROP — Anti-Forensics & Secure Data Handling
Ensures no recoverable evidence exists on disk. Ever.

Implements:
  1. Secure file shredding (multi-pass overwrite + unlink)
  2. Swap/hibernation sanitization
  3. Free-space wiping on mounted volumes
  4. RAM artifact scrubbing
  5. USB dead-drop creation (encrypted portable volumes)
  6. Emergency panic button (destroy everything instantly)

Usage:
    python3 dead_drop.py shred <file/dir>   — Secure delete (7-pass overwrite)
    python3 dead_drop.py swap               — Sanitize swap partition
    python3 dead_drop.py freespace <mount>  — Wipe free space on volume
    python3 dead_drop.py usb <device>       — Create encrypted USB dead drop
    python3 dead_drop.py panic              — EMERGENCY: destroy all sensitive data
"""

import argparse, os, sys, subprocess, time, random, struct

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m","D":"\033[0;37m"}

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", 1


def secure_shred_file(filepath, passes=7):
    """Multi-pass overwrite then unlink. Defeats magnetic recovery."""
    if not os.path.isfile(filepath):
        return False
    try:
        size = os.path.getsize(filepath)
        if size == 0:
            os.unlink(filepath)
            return True

        with open(filepath, "r+b") as f:
            for p in range(passes):
                f.seek(0)
                if p % 3 == 0:
                    # Pattern: all zeros
                    remaining = size
                    while remaining > 0:
                        chunk = min(remaining, 65536)
                        f.write(b"\x00" * chunk)
                        remaining -= chunk
                elif p % 3 == 1:
                    # Pattern: all ones
                    remaining = size
                    while remaining > 0:
                        chunk = min(remaining, 65536)
                        f.write(b"\xFF" * chunk)
                        remaining -= chunk
                else:
                    # Pattern: random
                    remaining = size
                    while remaining > 0:
                        chunk = min(remaining, 65536)
                        f.write(os.urandom(chunk))
                        remaining -= chunk
                f.flush()
                os.fsync(f.fileno())

        # Final: truncate to 0 then rename randomly before unlink
        with open(filepath, "w") as f:
            f.truncate(0)

        # Rename to random name to destroy directory entry
        dirname = os.path.dirname(filepath) or "."
        random_name = os.path.join(dirname, f".shred_{random.randint(10**15, 10**16)}")
        os.rename(filepath, random_name)
        os.unlink(random_name)
        return True
    except Exception:
        # Fallback: try basic unlink
        try:
            os.unlink(filepath)
        except Exception:
            pass
        return False


def cmd_shred(target):
    print(f"\n  {C['C']}[Shred]{C['N']} Secure Deletion\n")

    if not os.path.exists(target):
        print(f"  {C['R']}[-]{C['N']} Target not found: {target}")
        return

    import shutil as sh
    # Check for system shred utility first
    has_shred = sh.which("shred")

    files_destroyed = 0

    if os.path.isfile(target):
        targets = [target]
    else:
        targets = []
        for root, dirs, files in os.walk(target, topdown=False):
            for f in files:
                targets.append(os.path.join(root, f))

    total = len(targets)
    print(f"  {C['Y']}{total} files targeted for destruction{C['N']}\n")

    for i, fp in enumerate(targets, 1):
        basename = os.path.basename(fp)
        sys.stdout.write(f"\r  [{i}/{total}] Shredding: {basename[:40]:40s}")
        sys.stdout.flush()

        if has_shred:
            # Use system shred if available (handles filesystem-specific edge cases)
            run(["shred", "-vzfun", "7", fp], timeout=60)
        else:
            secure_shred_file(fp, passes=7)
        files_destroyed += 1

    # Remove empty directories
    if os.path.isdir(target):
        for root, dirs, files in os.walk(target, topdown=False):
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
        try:
            os.rmdir(target)
        except Exception:
            pass

    print(f"\n\n  {C['G']}{files_destroyed} files securely destroyed (7-pass overwrite + unlink){C['N']}\n")


def cmd_swap():
    """Sanitize swap partition — swap can contain decrypted secrets."""
    print(f"\n  {C['C']}[Swap]{C['N']} Swap Partition Sanitization\n")

    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Requires root")
        return

    # Find active swap
    out, _ = run(["swapon", "--show", "--raw", "--noheadings"])
    if not out:
        print(f"  {C['G']}●{C['N']} No active swap — nothing to sanitize")
        return

    for line in out.split("\n"):
        parts = line.split()
        if not parts:
            continue
        swap_dev = parts[0]
        swap_type = parts[1] if len(parts) > 1 else "unknown"

        print(f"  {C['Y']}[*]{C['N']} Found swap: {swap_dev} ({swap_type})")

        if swap_type == "file":
            print(f"  {C['Y']}[*]{C['N']} Turning off swap file...")
            run(["swapoff", swap_dev])
            print(f"  {C['Y']}[*]{C['N']} Overwriting swap file with zeros...")
            size = os.path.getsize(swap_dev)
            run(["dd", "if=/dev/zero", f"of={swap_dev}", "bs=1M",
                 f"count={size // (1024*1024) + 1}"], timeout=300)
            run(["mkswap", swap_dev])
            run(["swapon", swap_dev])
            print(f"  {C['G']}●{C['N']} Swap file sanitized and re-enabled")
        elif swap_type == "partition":
            print(f"  {C['Y']}[*]{C['N']} Turning off swap partition...")
            run(["swapoff", swap_dev])
            print(f"  {C['Y']}[*]{C['N']} Overwriting swap partition...")
            run(["dd", "if=/dev/urandom", f"of={swap_dev}", "bs=1M"], timeout=600)
            run(["mkswap", swap_dev])
            run(["swapon", swap_dev])
            print(f"  {C['G']}●{C['N']} Swap partition sanitized and re-enabled")

    print()


def cmd_freespace(mountpoint):
    """Wipe free space on a mounted volume to prevent deleted file recovery."""
    print(f"\n  {C['C']}[Freespace]{C['N']} Wiping free space on {mountpoint}\n")

    if not os.path.ismount(mountpoint) and mountpoint != "/":
        print(f"  {C['R']}[-]{C['N']} {mountpoint} is not a mount point")
        return

    # Get available space
    stat = os.statvfs(mountpoint)
    free_bytes = stat.f_bavail * stat.f_frsize
    free_mb = free_bytes // (1024 * 1024)
    print(f"  Free space: {free_mb:,} MB")
    print(f"  {C['Y']}This will temporarily fill the disk. Ensure enough space for OS operations.{C['N']}\n")

    fill_file = os.path.join(mountpoint, ".shadow_freespace_wipe")
    try:
        print(f"  {C['Y']}[*]{C['N']} Pass 1: Zero fill...")
        # Write zeros to fill free space
        with open(fill_file, "wb") as f:
            written = 0
            chunk = b"\x00" * (1024 * 1024)  # 1MB chunks
            try:
                while True:
                    f.write(chunk)
                    written += len(chunk)
                    if written % (100 * 1024 * 1024) == 0:
                        sys.stdout.write(f"\r  Written: {written // (1024*1024):,} MB")
                        sys.stdout.flush()
            except (OSError, IOError):
                pass  # Disk full — that's the point

        os.unlink(fill_file)
        os.sync()
        print(f"\n  {C['G']}●{C['N']} Free space wiped ({written // (1024*1024):,} MB overwritten)\n")

    except Exception as e:
        print(f"\n  {C['R']}[-]{C['N']} Error: {e}")
        if os.path.exists(fill_file):
            os.unlink(fill_file)


def cmd_usb(device):
    """Create an encrypted USB dead drop with LUKS."""
    print(f"\n  {C['C']}[USB]{C['N']} Encrypted Dead Drop Creation\n")

    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Requires root")
        return

    import shutil
    if not shutil.which("cryptsetup"):
        print(f"  {C['R']}[-]{C['N']} cryptsetup not found. Install: sudo apt install cryptsetup")
        return

    if not device.startswith("/dev/"):
        print(f"  {C['R']}[-]{C['N']} Device must be a block device (e.g., /dev/sdb1)")
        return

    if not os.path.exists(device):
        print(f"  {C['R']}[-]{C['N']} Device not found: {device}")
        return

    print(f"  {C['R']}WARNING: This will DESTROY all data on {device}{C['N']}")
    print(f"  {C['Y']}Type 'DESTROY' to confirm:{C['N']} ", end="")
    confirm = input().strip()
    if confirm != "DESTROY":
        print(f"  {C['Y']}Aborted.{C['N']}")
        return

    # Create LUKS volume
    print(f"\n  {C['Y']}[*]{C['N']} Creating LUKS encrypted volume...")
    print(f"  {C['Y']}Enter passphrase for the encrypted volume:{C['N']}")

    result = subprocess.run(
        ["cryptsetup", "luksFormat", "--type", "luks2", "--cipher",
         "aes-xts-plain64", "--key-size", "512", "--hash", "sha512",
         "--iter-time", "5000", device],
        timeout=60
    )

    if result.returncode != 0:
        print(f"  {C['R']}[-]{C['N']} LUKS format failed")
        return

    # Open and format
    dm_name = "shadow_deaddrop"
    print(f"  {C['Y']}[*]{C['N']} Opening encrypted volume...")
    result = subprocess.run(
        ["cryptsetup", "luksOpen", device, dm_name],
        timeout=30
    )

    if result.returncode != 0:
        print(f"  {C['R']}[-]{C['N']} Failed to open LUKS volume")
        return

    print(f"  {C['Y']}[*]{C['N']} Formatting with ext4...")
    run(["mkfs.ext4", f"/dev/mapper/{dm_name}"])

    # Mount
    mount_point = "/mnt/shadow_deaddrop"
    os.makedirs(mount_point, exist_ok=True)
    run(["mount", f"/dev/mapper/{dm_name}", mount_point])
    os.chmod(mount_point, 0o700)

    print(f"\n  {C['G']}●{C['N']} Encrypted dead drop created and mounted at {mount_point}")
    print(f"  {C['D']}  Cipher: AES-256-XTS | Hash: SHA-512 | LUKS2{C['N']}")
    print(f"\n  {C['Y']}To unmount and lock:{C['N']}")
    print(f"    sudo umount {mount_point}")
    print(f"    sudo cryptsetup luksClose {dm_name}\n")


def cmd_panic():
    """EMERGENCY: Destroy all sensitive data immediately."""
    print(f"\n{C['R']}")
    print(f"  ██████╗  █████╗ ███╗   ██╗██╗ ██████╗")
    print(f"  ██╔══██╗██╔══██╗████╗  ██║██║██╔════╝")
    print(f"  ██████╔╝███████║██╔██╗ ██║██║██║     ")
    print(f"  ██╔═══╝ ██╔══██║██║╚██╗██║██║██║     ")
    print(f"  ██║     ██║  ██║██║ ╚████║██║╚██████╗")
    print(f"  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝{C['N']}")
    print(f"\n  {C['R']}THIS WILL DESTROY:{C['N']}")
    print(f"  • All ShadowCypher logs, databases, configs")
    print(f"  • Shell histories, browser data, recent files")
    print(f"  • Ghost keys, mesh keys, relay tokens")
    print(f"  • RAM workspace contents")
    print(f"\n  {C['Y']}Type 'BURN IT ALL' to confirm:{C['N']} ", end="")
    confirm = input().strip()
    if confirm != "BURN IT ALL":
        print(f"  {C['Y']}Aborted.{C['N']}")
        return

    print(f"\n  {C['R']}EXECUTING PANIC PROTOCOL{C['N']}\n")
    destroyed = 0

    import shutil, glob

    # Project root
    proj = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. Destroy databases
    for pattern in [f"{proj}/projects/*.db", f"{proj}/**/*.sqlite"]:
        for f in glob.glob(pattern, recursive=True):
            secure_shred_file(f, passes=3)
            destroyed += 1
            print(f"  {C['R']}✗{C['N']} {f}")

    # 2. Destroy keys
    key_locations = [
        "/etc/shadowcypher/master.key",
        os.path.expanduser("~/.shadowcypher/mesh/node_key.bin"),
        os.path.expanduser("~/.shadowcypher/master.key"),
        f"{proj}/.relay_token",
        f"{proj}/.session-secret",
    ]
    for kp in key_locations:
        if os.path.exists(kp):
            secure_shred_file(kp, passes=7)
            destroyed += 1
            print(f"  {C['R']}✗{C['N']} {kp}")

    # 3. Destroy logs
    log_dirs = [f"{proj}/logs", f"{proj}/findings", f"{proj}/reports",
                f"{proj}/payloads", f"{proj}/projects"]
    for ld in log_dirs:
        if os.path.isdir(ld):
            for root, dirs, files in os.walk(ld):
                for f in files:
                    fp = os.path.join(root, f)
                    secure_shred_file(fp, passes=3)
                    destroyed += 1
            print(f"  {C['R']}✗{C['N']} {ld}/")

    # 4. Destroy configs
    for cf in [f"{proj}/config.json", f"{proj}/.env"]:
        if os.path.exists(cf):
            secure_shred_file(cf, passes=3)
            destroyed += 1
            print(f"  {C['R']}✗{C['N']} {cf}")

    # 5. Shell histories
    home = os.path.expanduser("~")
    for hf in [".bash_history", ".zsh_history", ".python_history",
               ".node_repl_history", ".mysql_history", ".viminfo",
               ".wget-hsts", ".lesshst"]:
        fp = os.path.join(home, hf)
        if os.path.exists(fp):
            with open(fp, "w") as f:
                f.truncate(0)
            destroyed += 1

    # 6. Browser data
    browser_dirs = [
        os.path.join(home, ".local/share/recently-used.xbel"),
        os.path.join(home, ".cache/thumbnails"),
    ]
    for bd in browser_dirs:
        if os.path.exists(bd):
            if os.path.isfile(bd):
                with open(bd, "w") as f:
                    f.truncate(0)
            elif os.path.isdir(bd):
                shutil.rmtree(bd, ignore_errors=True)
            destroyed += 1

    # 7. RAM workspace
    ram_dir = "/tmp/ghost_workspace"
    if os.path.isdir(ram_dir):
        shutil.rmtree(ram_dir, ignore_errors=True)
        destroyed += 1

    # 8. Drop caches
    if os.geteuid() == 0:
        run("sync; echo 3 > /proc/sys/vm/drop_caches")

    print(f"\n  {C['R']}{'═'*50}{C['N']}")
    print(f"  {C['R']}PANIC COMPLETE: {destroyed} items destroyed{C['N']}")
    print(f"  {C['R']}{'═'*50}{C['N']}\n")


def main():
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // DEAD DROP{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")

    p = argparse.ArgumentParser(description="ShadowCypher Dead Drop")
    sub = p.add_subparsers(dest="command")

    shred_p = sub.add_parser("shred", help="Secure delete file/directory")
    shred_p.add_argument("target", help="File or directory to shred")

    sub.add_parser("swap", help="Sanitize swap partition")

    fs_p = sub.add_parser("freespace", help="Wipe free space")
    fs_p.add_argument("mountpoint", help="Mount point to wipe")

    usb_p = sub.add_parser("usb", help="Create encrypted USB dead drop")
    usb_p.add_argument("device", help="Block device (e.g., /dev/sdb1)")

    sub.add_parser("panic", help="EMERGENCY: destroy everything")

    a = p.parse_args()

    if a.command == "shred":
        cmd_shred(a.target)
    elif a.command == "swap":
        cmd_swap()
    elif a.command == "freespace":
        cmd_freespace(a.mountpoint)
    elif a.command == "usb":
        cmd_usb(a.device)
    elif a.command == "panic":
        cmd_panic()
    else:
        p.print_help()

if __name__ == "__main__":
    main()
