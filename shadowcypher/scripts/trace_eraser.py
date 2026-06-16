#!/usr/bin/env python3
"""
SHADOWCYPHER // TRACE ERASER — Deep Forensic Log Cleaner
Systematically removes operator traces from system logs, shell histories,
auth records, journal entries, and filesystem metadata.
Requires root for full effectiveness.

Usage:
    sudo python3 trace_eraser.py [--deep] [--timestamps] [--user USER]
"""

import argparse
import os
import sys
import subprocess
import glob
import time
import re

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","N":"\033[0m","B":"\033[1m"}

def is_root():
    return os.geteuid() == 0

def run_silent(cmd):
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       shell=isinstance(cmd, str), timeout=10)  # nosec B602
    except Exception:
        pass

def wipe_file(path, label):
    if os.path.exists(path):
        try:
            with open(path, "w") as f:
                f.truncate(0)
            print(f"  {C['G']}●{C['N']} {label}: {path}")
            return True
        except PermissionError:
            print(f"  {C['R']}✗{C['N']} {label}: {path} (permission denied)")
    return False

def remove_files(pattern, label):
    files = glob.glob(pattern)
    count = 0
    for f in files:
        try:
            os.remove(f)
            count += 1
        except Exception:
            pass
    if count:
        print(f"  {C['G']}●{C['N']} {label}: {count} files removed ({pattern})")
    return count

def scrub_file_lines(path, patterns, label):
    """Remove lines matching any pattern from a log file."""
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        original_count = len(lines)
        filtered = [ln for ln in lines if not any(p.search(ln) for p in patterns)]
        removed = original_count - len(filtered)
        if removed > 0:
            with open(path, "w") as f:
                f.writelines(filtered)
            print(f"  {C['G']}●{C['N']} {label}: {removed} lines scrubbed from {path}")
        return removed
    except Exception:
        return 0

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Trace Eraser")
    p.add_argument("--deep", action="store_true", help="Deep scrub: journal vacuum, wtmp/btmp, lastlog")
    p.add_argument("--timestamps", action="store_true", help="Randomize file access timestamps in CWD")
    p.add_argument("--user", default=os.environ.get("SUDO_USER", os.environ.get("USER", "root")),
                   help="Target user whose traces to clean")
    p.add_argument("--ip", help="Scrub specific IP from auth logs")
    p.add_argument("--keyword", help="Scrub lines containing this keyword from logs")
    a = p.parse_args()

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // TRACE ERASER{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  User:  {C['Y']}{a.user}{C['N']}  |  Deep: {a.deep}  |  Root: {is_root()}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    ops = 0

    # ══════════════════════════════════════════════════════════════
    # Phase 1: Shell Histories
    # ══════════════════════════════════════════════════════════════
    print(f"  {C['C']}[Phase 1]{C['N']} Shell Histories")
    home = os.path.expanduser(f"~{a.user}") if a.user != "root" else "/root"
    history_files = [
        ".bash_history", ".zsh_history", ".python_history", ".node_repl_history",
        ".mysql_history", ".psql_history", ".irb_history", ".lesshst",
        ".viminfo", ".wget-hsts", ".sqlite_history",
    ]
    for hf in history_files:
        if wipe_file(os.path.join(home, hf), hf):
            ops += 1
    # Also clean root if we're running as root
    if is_root() and a.user != "root":
        for hf in history_files:
            if wipe_file(os.path.join("/root", hf), f"root/{hf}"):
                ops += 1
    # Clear in-memory history
    run_silent("history -c")

    # ══════════════════════════════════════════════════════════════
    # Phase 2: System Logs
    # ══════════════════════════════════════════════════════════════
    print(f"\n  {C['C']}[Phase 2]{C['N']} System Logs")

    # Build scrub patterns
    patterns = []
    if a.user:
        patterns.append(re.compile(re.escape(a.user), re.IGNORECASE))
    if a.ip:
        patterns.append(re.compile(re.escape(a.ip)))
    if a.keyword:
        patterns.append(re.compile(re.escape(a.keyword), re.IGNORECASE))
    patterns.append(re.compile(r"shadowcypher", re.IGNORECASE))

    log_files = [
        "/var/log/auth.log", "/var/log/syslog", "/var/log/messages",
        "/var/log/daemon.log", "/var/log/kern.log", "/var/log/user.log",
        "/var/log/secure", "/var/log/faillog",
    ]
    for lf in log_files:
        removed = scrub_file_lines(lf, patterns, os.path.basename(lf))
        if removed:
            ops += 1

    # SSH logs
    scrub_file_lines("/var/log/auth.log", patterns, "SSH auth")

    # ══════════════════════════════════════════════════════════════
    # Phase 3: Application Traces
    # ══════════════════════════════════════════════════════════════
    print(f"\n  {C['C']}[Phase 3]{C['N']} Application Traces")
    ops += remove_files("/tmp/shadowcypher_*", "ShadowCypher temp files")  # nosec B108
    ops += remove_files("/tmp/.shadow*", "Shadow temp files")  # nosec B108
    ops += remove_files("/tmp/tmp*.hash", "Hash temp files")  # nosec B108

    # Clear ShadowCypher internal logs
    sc_logs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    if os.path.isdir(sc_logs):
        ops += remove_files(os.path.join(sc_logs, "*.log"), "ShadowCypher logs")

    # ══════════════════════════════════════════════════════════════
    # Phase 4: Deep Scrub (optional)
    # ══════════════════════════════════════════════════════════════
    if a.deep and is_root():
        print(f"\n  {C['C']}[Phase 4]{C['N']} Deep Forensic Scrub")

        # wtmp (login records) — truncate
        if wipe_file("/var/log/wtmp", "wtmp (login records)"):
            ops += 1
        if wipe_file("/var/log/btmp", "btmp (failed logins)"):
            ops += 1
        if wipe_file("/var/log/lastlog", "lastlog"):
            ops += 1

        # Systemd journal vacuum
        print(f"  {C['C']}[*]{C['N']} Vacuuming systemd journal...")
        run_silent(["journalctl", "--vacuum-time=1s"])
        run_silent(["journalctl", "--rotate"])
        print(f"  {C['G']}●{C['N']} Journal vacuumed")
        ops += 1

        # Kernel ring buffer
        run_silent(["dmesg", "-C"])
        print(f"  {C['G']}●{C['N']} Kernel ring buffer cleared")
        ops += 1

        # Flush DNS cache
        run_silent(["systemd-resolve", "--flush-caches"])
        run_silent(["resolvectl", "flush-caches"])
        print(f"  {C['G']}●{C['N']} DNS cache flushed")
        ops += 1

        # Clear thumbnail cache
        thumb_dir = os.path.join(home, ".cache", "thumbnails")
        if os.path.isdir(thumb_dir):
            run_silent(f"rm -rf {thumb_dir}/*")
            print(f"  {C['G']}●{C['N']} Thumbnail cache cleared")
            ops += 1

        # recently-used.xbel
        recent = os.path.join(home, ".local", "share", "recently-used.xbel")
        if wipe_file(recent, "recently-used.xbel"):
            ops += 1

        # Trash
        trash_dir = os.path.join(home, ".local", "share", "Trash")
        if os.path.isdir(trash_dir):
            run_silent(f"rm -rf {trash_dir}/*")
            print(f"  {C['G']}●{C['N']} Trash emptied")
            ops += 1

    # ══════════════════════════════════════════════════════════════
    # Phase 5: Timestamp Obfuscation (optional)
    # ══════════════════════════════════════════════════════════════
    if a.timestamps:
        print(f"\n  {C['C']}[Phase 5]{C['N']} Timestamp Obfuscation")
        import random
        count = 0
        for root, dirs, files in os.walk("."):
            if ".git" in root:
                continue
            for f in files:
                fp = os.path.join(root, f)
                try:
                    # Randomize atime/mtime within last 30 days
                    rand_time = time.time() - random.randint(0, 30*86400)
                    os.utime(fp, (rand_time, rand_time))
                    count += 1
                except Exception:
                    pass
        print(f"  {C['G']}●{C['N']} {count} file timestamps randomized")
        ops += 1

    # ══════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════
    # Drop filesystem caches
    if is_root():
        run_silent("sync; echo 3 > /proc/sys/vm/drop_caches")

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f"  {C['G']}TRACE ERASER COMPLETE: {ops} operations performed{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

if __name__ == "__main__":
    main()
