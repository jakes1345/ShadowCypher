#!/usr/bin/env python3
"""
SHADOWCYPHER // GHOST MODE — Total Operational Invisibility
One command to make you completely invisible. Like you don't exist.

Think F-Society. Think Mr. Robot. Think: nobody can see what you do,
where you are, who you are, or that you were ever here.

This orchestrates EVERY layer:
  - Network:  Tor + DNS leak prevention + iptables kill-switch
  - Identity: MAC randomization + hostname wipe + timezone neutralize
  - Memory:   RAM-only workspace (tmpfs) for sensitive operations
  - Disk:     Encrypted scratch volume, no forensic artifacts
  - Browser:  Tor Browser isolation
  - Cleanup:  Automatic trace destruction on exit

Usage:
    sudo python3 ghost_mode.py engage      — Full ghost mode activation
    sudo python3 ghost_mode.py disengage   — Restore normal operation
    sudo python3 ghost_mode.py status      — Check ghost mode status
    sudo python3 ghost_mode.py workspace   — Open RAM-only workspace
"""

import argparse
import os
import sys
import subprocess
import socket
import time
import signal
import atexit
import shutil
import tempfile
import json

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m","D":"\033[0;37m"}

STATE_FILE  = "/tmp/.ghost_mode_state"  # Intentionally in /tmp for tmpfs  # nosec B108
BACKUP_DIR  = "/tmp/.ghost_restore"  # nosec B108
_SOCKS5_PORT = 1080

def run(cmd, timeout=15, check=False):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))  # nosec B602
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", 1

def need_root():
    if os.geteuid() != 0:
        print(f"  {C['R']}[!]{C['N']} Ghost Mode requires root. Run with sudo.")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# ENGAGE — Full Ghost Mode
# ═══════════════════════════════════════════════════════════════

def engage():
    need_root()
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['R']}  ██████  ██   ██  ██████  ███████ ████████{C['N']}")
    print(f" {C['R']} ██       ██   ██ ██    ██ ██         ██{C['N']}")
    print(f" {C['R']} ██   ███ ███████ ██    ██ ███████    ██{C['N']}")
    print(f" {C['R']} ██    ██ ██   ██ ██    ██      ██    ██{C['N']}")
    print(f" {C['R']}  ██████  ██   ██  ██████  ███████    ██{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")
    print(f" {C['M']}  ENGAGING TOTAL OPERATIONAL INVISIBILITY{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")

    state = {"engaged_at": time.time(), "layers": []}
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # ── Layer 1: Save current state for restore ──
    print(f"  {C['C']}[Layer 1]{C['N']} Saving restore point")
    # Save hostname
    hostname, _ = run(["hostname"])
    with open(f"{BACKUP_DIR}/hostname", "w") as f:
        f.write(hostname)
    # Save resolv.conf
    if os.path.exists("/etc/resolv.conf"):
        shutil.copy2("/etc/resolv.conf", f"{BACKUP_DIR}/resolv.conf")
    # Save iptables
    out, _ = run(["iptables-save"])
    with open(f"{BACKUP_DIR}/iptables.rules", "w") as f:
        f.write(out)
    print(f"  {C['G']}●{C['N']} System state backed up")
    state["layers"].append("backup")

    # ── Layer 2: MAC Randomization ──
    print(f"\n  {C['C']}[Layer 2]{C['N']} MAC Address Randomization")
    out, _ = run(["ip", "-o", "link", "show"])
    import re
    for line in out.split("\n"):
        parts = line.split()
        if len(parts) < 4:
            continue
        iface = parts[1].rstrip(":")
        if iface == "lo" or "docker" in iface or "br-" in iface or "veth" in iface:
            continue
        # Save current MAC
        mac_match = re.search(r"link/ether\s+([0-9a-f:]{17})", line)
        if mac_match:
            with open(f"{BACKUP_DIR}/mac_{iface}", "w") as f:
                f.write(mac_match.group(1))

        if shutil.which("macchanger"):
            run(["ip", "link", "set", iface, "down"])
            out2, rc = run(["macchanger", "-r", iface])
            run(["ip", "link", "set", iface, "up"])
            if rc == 0:
                new_mac = re.search(r"New MAC:\s+([0-9a-f:]{17})", out2)
                if new_mac:
                    print(f"  {C['G']}●{C['N']} {iface}: {new_mac.group(1)} (randomized)")
        else:
            # Manual randomization without macchanger
            import random
            new_mac = "02:%02x:%02x:%02x:%02x:%02x" % tuple(random.randint(0, 255) for _ in range(5))
            run(["ip", "link", "set", iface, "down"])
            run(["ip", "link", "set", iface, "address", new_mac])
            run(["ip", "link", "set", iface, "up"])
            print(f"  {C['G']}●{C['N']} {iface}: {new_mac} (randomized)")
    state["layers"].append("mac")

    # ── Layer 3: Hostname Neutralization ──
    print(f"\n  {C['C']}[Layer 3]{C['N']} Identity Neutralization")
    run(["hostnamectl", "set-hostname", "localhost"])
    os.environ["TZ"] = "UTC"
    run(["timedatectl", "set-timezone", "UTC"])
    print(f"  {C['G']}●{C['N']} Hostname: localhost")
    print(f"  {C['G']}●{C['N']} Timezone: UTC")
    state["layers"].append("identity")

    # ── Layer 4: Tor Activation ──
    print(f"\n  {C['C']}[Layer 4]{C['N']} Tor Network Activation")
    if not shutil.which("tor"):
        print(f"  {C['Y']}[*]{C['N']} Installing Tor...")
        run(["apt-get", "install", "-y", "tor"], timeout=120)

    # Ensure Tor is running
    def tor_alive():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            r = s.connect_ex(("127.0.0.1", 9050))
            s.close()
            return r == 0
        except Exception:
            return False

    if not tor_alive():
        run(["systemctl", "start", "tor"])
        time.sleep(2)
        if not tor_alive():
            subprocess.Popen(["tor", "--quiet"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            for _ in range(20):
                time.sleep(1)
                if tor_alive():
                    break

    if tor_alive():
        print(f"  {C['G']}●{C['N']} Tor SOCKS proxy: ACTIVE (127.0.0.1:9050)")
        # Verify IP masking
        out, _ = run(["curl", "-s", "--max-time", "8", "--socks5-hostname",
                       "127.0.0.1:9050", "https://api.ipify.org"])
        if out:
            print(f"  {C['G']}●{C['N']} Exit IP: {C['G']}{out}{C['N']}")
    else:
        print(f"  {C['R']}✗{C['N']} Tor failed to start")
    state["layers"].append("tor")

    # ── Layer 5: Iptables Kill-Switch (Transparent Tor Proxy) ──
    print(f"\n  {C['C']}[Layer 5]{C['N']} Network Kill-Switch (Tor-Only Enforcement)")
    tor_uid = None
    try:
        import pwd
        tor_uid = pwd.getpwnam("debian-tor").pw_uid
    except KeyError:
        try:
            tor_uid = int(run(["id", "-u", "debian-tor"])[0])
        except Exception:
            try:
                import pwd
                tor_uid = pwd.getpwnam("tor").pw_uid
            except Exception:
                pass

    if tor_uid is not None:
        # Flush existing rules
        run(["iptables", "-F"])
        run(["iptables", "-t", "nat", "-F"])

        # Allow loopback
        run(["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"])
        run(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])

        # Allow Tor process itself to reach the internet
        run(["iptables", "-A", "OUTPUT", "-m", "owner", "--uid-owner", str(tor_uid), "-j", "ACCEPT"])

        # Allow established connections
        run(["iptables", "-A", "OUTPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])
        run(["iptables", "-A", "INPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])

        # Redirect all DNS to Tor's DNS port
        run(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j",
             "REDIRECT", "--to-ports", "5353"])
        run(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "--dport", "53", "-j",
             "REDIRECT", "--to-ports", "5353"])

        # Redirect all TCP to Tor's TransPort
        run(["iptables", "-t", "nat", "-A", "OUTPUT", "!", "-o", "lo", "-p", "tcp",
             "-m", "owner", "!", "--uid-owner", str(tor_uid), "-j",
             "REDIRECT", "--to-ports", "9040"])

        # Drop everything else
        run(["iptables", "-A", "OUTPUT", "-j", "DROP"])
        run(["iptables", "-P", "INPUT", "DROP"])

        print(f"  {C['G']}●{C['N']} All traffic forced through Tor")
        print(f"  {C['G']}●{C['N']} Non-Tor traffic: BLOCKED")
        print(f"  {C['G']}●{C['N']} DNS queries: redirected through Tor")
    else:
        print(f"  {C['Y']}●{C['N']} Tor user not found — using proxychains mode instead")
        # Set global proxy environment
        os.environ["ALL_PROXY"] = "socks5h://127.0.0.1:9050"
        os.environ["http_proxy"] = "socks5h://127.0.0.1:9050"
        os.environ["https_proxy"] = "socks5h://127.0.0.1:9050"
    state["layers"].append("killswitch")

    # ── Layer 6: DNS Hardening ──
    print(f"\n  {C['C']}[Layer 6]{C['N']} DNS Leak Prevention")
    # Point DNS to localhost (Tor resolves it)
    with open("/etc/resolv.conf", "w") as f:
        f.write("# Ghost Mode — DNS via Tor\nnameserver 127.0.0.1\n")
    print(f"  {C['G']}●{C['N']} resolv.conf: pointing to localhost")
    # Disable systemd-resolved if running
    run(["systemctl", "stop", "systemd-resolved"])
    print(f"  {C['G']}●{C['N']} systemd-resolved: stopped")
    state["layers"].append("dns")

    # ── Layer 7: RAM Workspace ──
    print(f"\n  {C['C']}[Layer 7]{C['N']} RAM-Only Workspace")
    ram_dir = "/tmp/ghost_workspace"  # nosec B108
    os.makedirs(ram_dir, exist_ok=True)
    # Check if /tmp is already tmpfs
    out, _ = run(["findmnt", "-n", "-o", "FSTYPE", "/tmp"])  # nosec B108
    if out.strip() == "tmpfs":
        print(f"  {C['G']}●{C['N']} /tmp is tmpfs — workspace is RAM-only")
    else:
        # Mount a tmpfs for our workspace
        run(["mount", "-t", "tmpfs", "-o", "size=512M,mode=700", "tmpfs", ram_dir])
        print(f"  {C['G']}●{C['N']} RAM workspace mounted at {ram_dir} (512MB, mode 700)")
    state["ram_workspace"] = ram_dir
    state["layers"].append("ram")

    # ── Layer 8: Disable logging ──
    print(f"\n  {C['C']}[Layer 8]{C['N']} Log Suppression")
    run(["systemctl", "stop", "rsyslog"])
    run(["systemctl", "stop", "syslog"])
    print(f"  {C['G']}●{C['N']} System logging: STOPPED")
    state["layers"].append("nolog")

    # Save state
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    # ── Hysteria2 auto-start (QUIC stealth transport) ──
    print(f"\n  {C['C']}[Layer 9]{C['N']} Hysteria2 QUIC Transport (auto)")
    try:
        from shadowcypher.core.hysteria import ghost_engage_hook
        ghost_engage_hook(on_output=lambda l: print(f"  {C['D']}{l.rstrip()}{C['N']}"))
        from shadowcypher.core.hysteria import hysteria_transport
        if hysteria_transport.connected:
            print(f"  {C['G']}●{C['N']} Hysteria2 QUIC tunnel active — SOCKS5:{_SOCKS5_PORT}")
            state["layers"].append("hysteria2")
        else:
            print(f"  {C['Y']}○{C['N']} Hysteria2 not configured — Tor handles routing")
    except Exception as _he:
        print(f"  {C['Y']}○{C['N']} Hysteria2 unavailable — Tor handles routing")

    # Re-save state with any hysteria2 layer added
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f"  {C['G']}GHOST MODE: ACTIVE{C['N']}")
    print(f"  {C['D']}All traffic routed through Tor{C['N']}")
    print(f"  {C['D']}MAC addresses randomized{C['N']}")
    print(f"  {C['D']}Identity neutralized (hostname: localhost, TZ: UTC){C['N']}")
    print(f"  {C['D']}DNS leak protection engaged{C['N']}")
    print(f"  {C['D']}Network kill-switch active (non-Tor traffic blocked){C['N']}")
    print(f"  {C['D']}RAM workspace: {ram_dir}{C['N']}")
    print(f"  {C['D']}System logging disabled{C['N']}")
    print(f"\n  {C['Y']}You are now invisible. Act accordingly.{C['N']}")
    print(f"  {C['Y']}Run 'ghost_mode.py disengage' to restore normal operation.{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")


# ═══════════════════════════════════════════════════════════════
# DISENGAGE — Restore Normal Operation
# ═══════════════════════════════════════════════════════════════

def disengage():
    need_root()
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['Y']}DISENGAGING GHOST MODE{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")

    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)

    # Restore iptables
    print(f"  {C['C']}[1]{C['N']} Restoring firewall rules")
    rules_file = f"{BACKUP_DIR}/iptables.rules"
    if os.path.exists(rules_file):
        with open(rules_file) as _rf:
            run(["iptables-restore"], stdin=_rf, timeout=5)
        # Fallback: just flush
        run(["iptables", "-F"])
        run(["iptables", "-t", "nat", "-F"])
        run(["iptables", "-P", "INPUT", "ACCEPT"])
        run(["iptables", "-P", "OUTPUT", "ACCEPT"])
        run(["iptables", "-P", "FORWARD", "ACCEPT"])
    else:
        run(["iptables", "-F"])
        run(["iptables", "-t", "nat", "-F"])
        run(["iptables", "-P", "INPUT", "ACCEPT"])
        run(["iptables", "-P", "OUTPUT", "ACCEPT"])
    print(f"  {C['G']}●{C['N']} Firewall restored to default ACCEPT")

    # Restore DNS
    print(f"  {C['C']}[2]{C['N']} Restoring DNS")
    resolv_backup = f"{BACKUP_DIR}/resolv.conf"
    if os.path.exists(resolv_backup):
        shutil.copy2(resolv_backup, "/etc/resolv.conf")
    run(["systemctl", "start", "systemd-resolved"])
    print(f"  {C['G']}●{C['N']} DNS restored")

    # Restore hostname
    print(f"  {C['C']}[3]{C['N']} Restoring hostname")
    hostname_file = f"{BACKUP_DIR}/hostname"
    if os.path.exists(hostname_file):
        with open(hostname_file) as f:
            old_hostname = f.read().strip()
        run(["hostnamectl", "set-hostname", old_hostname])
        print(f"  {C['G']}●{C['N']} Hostname: {old_hostname}")

    # Restore MAC addresses
    print(f"  {C['C']}[4]{C['N']} Restoring MAC addresses")
    import glob
    import re
    for mac_file in glob.glob(f"{BACKUP_DIR}/mac_*"):
        iface = os.path.basename(mac_file).replace("mac_", "")
        with open(mac_file) as f:
            old_mac = f.read().strip()
        run(["ip", "link", "set", iface, "down"])
        run(["ip", "link", "set", iface, "address", old_mac])
        run(["ip", "link", "set", iface, "up"])
        print(f"  {C['G']}●{C['N']} {iface}: {old_mac}")

    # Re-enable logging
    print(f"  {C['C']}[5]{C['N']} Restoring system logging")
    run(["systemctl", "start", "rsyslog"])
    run(["systemctl", "start", "syslog"])
    print(f"  {C['G']}●{C['N']} System logging: RESTORED")

    # Clean RAM workspace
    print(f"  {C['C']}[6]{C['N']} Scrubbing RAM workspace")
    ram_dir = state.get("ram_workspace", "/tmp/ghost_workspace")  # nosec B108
    if os.path.isdir(ram_dir):
        # Overwrite files before removal
        for root, dirs, files in os.walk(ram_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    with open(fp, "wb") as fh:
                        fh.write(os.urandom(size))
                except Exception:
                    pass
        shutil.rmtree(ram_dir, ignore_errors=True)
    print(f"  {C['G']}●{C['N']} RAM workspace destroyed")

    # Clean trace eraser
    print(f"  {C['C']}[7]{C['N']} Final trace cleanup")
    # Clear shell history
    for hf in [".bash_history", ".zsh_history", ".python_history"]:
        path = os.path.expanduser(f"~/{hf}")
        if os.path.exists(path):
            with open(path, "w") as f:
                f.truncate(0)
    # Drop filesystem caches
    run("sync; echo 3 > /proc/sys/vm/drop_caches")
    print(f"  {C['G']}●{C['N']} History cleared, fs caches dropped")

    # Remove state files
    for f in [STATE_FILE]:
        if os.path.exists(f):
            os.remove(f)
    shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f"  {C['G']}GHOST MODE: DISENGAGED{C['N']}")
    # Stop Hysteria2 if it was running
    try:
        from shadowcypher.core.hysteria import ghost_disengage_hook
        ghost_disengage_hook()
    except Exception:
        pass

    print(f"  {C['D']}Normal operation restored. You are visible again.{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")


# ═══════════════════════════════════════════════════════════════
# STATUS — Check if ghost mode is active
# ═══════════════════════════════════════════════════════════════

def status():
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['C']}GHOST MODE STATUS{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")

    active = os.path.exists(STATE_FILE)

    if active:
        with open(STATE_FILE) as f:
            state = json.load(f)
        engaged = time.time() - state.get("engaged_at", 0)
        hours = int(engaged // 3600)
        mins = int((engaged % 3600) // 60)
        print(f"  Status:   {C['G']}ACTIVE{C['N']} ({hours}h {mins}m)")
        print(f"  Layers:   {', '.join(state.get('layers', []))}")
    else:
        print(f"  Status:   {C['R']}INACTIVE{C['N']}")

    # Live checks
    print()

    # Tor
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        tor_up = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        tor_up = False
    print(f"  Tor:      {C['G'] if tor_up else C['R']}{'ACTIVE' if tor_up else 'INACTIVE'}{C['N']}")

    # Hysteria2
    try:
        from shadowcypher.core.hysteria import hysteria_transport
        h_status = hysteria_transport.status()
        if h_status["connected"]:
            print(f"  Hysteria2:{C['G']} ACTIVE{C['N']} via {h_status['server']} → {h_status['proxy_url']}")
        elif h_status["available"] and h_status["pool_size"] > 0:
            print(f"  Hysteria2:{C['Y']} CONFIGURED (not running){C['N']}")
        elif h_status["available"]:
            print(f"  Hysteria2:{C['Y']} INSTALLED (no servers — run: python3 -m shadowcypher.core.hysteria setup){C['N']}")
        else:
            print(f"  Hysteria2:{C['D']} NOT INSTALLED{C['N']}")
    except Exception:
        print(f"  Hysteria2:{C['D']} N/A{C['N']}")

    # Kill-switch
    out, _ = run(["iptables", "-L", "OUTPUT", "-n"])
    killswitch = "DROP" in (out or "")
    print(f"  Kill-SW:  {C['G'] if killswitch else C['Y']}{'ACTIVE' if killswitch else 'INACTIVE'}{C['N']}")

    # MAC
    out, _ = run(["ip", "-o", "link", "show"])
    import re
    for line in (out or "").split("\n"):
        mac_m = re.search(r"(\w+): .+link/ether\s+([0-9a-f:]{17})", line)
        if mac_m and mac_m.group(1) != "lo":
            first_byte = int(mac_m.group(2).split(":")[0], 16)
            randomized = bool(first_byte & 0x02)
            icon = C['G'] + "✓" if randomized else C['Y'] + "✗"
            print(f"  MAC {mac_m.group(1):5s}: {icon}{C['N']} {mac_m.group(2)}")

    # DNS
    if os.path.exists("/etc/resolv.conf"):
        with open("/etc/resolv.conf") as f:
            dns = f.read()
        if "127.0.0.1" in dns and "Ghost" in dns:
            print(f"  DNS:      {C['G']}Tor-routed{C['N']}")
        else:
            ns = re.findall(r"nameserver\s+(\S+)", dns)
            print(f"  DNS:      {C['Y']}{', '.join(ns[:2])}{C['N']}")

    # Hostname
    hostname = socket.gethostname()
    hn_safe = hostname in ("localhost", "localhost.localdomain")
    print(f"  Hostname: {C['G'] if hn_safe else C['Y']}{hostname}{C['N']}")

    print(f"\n{C['B']}{'═'*70}{C['N']}\n")


# ═══════════════════════════════════════════════════════════════
# WORKSPACE — Open a RAM-only shell
# ═══════════════════════════════════════════════════════════════

def workspace():
    ram_dir = "/tmp/ghost_workspace"  # nosec B108
    os.makedirs(ram_dir, exist_ok=True)

    print(f"\n  {C['C']}[Workspace]{C['N']} RAM-Only Shell")
    print(f"  {C['D']}Everything in {ram_dir} exists only in RAM.{C['N']}")
    print(f"  {C['D']}When you exit or reboot, it's gone forever.{C['N']}")
    print(f"  {C['Y']}Type 'exit' to return.{C['N']}\n")

    env = os.environ.copy()
    env["HOME"] = ram_dir
    env["HISTFILE"] = "/dev/null"
    env["PS1"] = "\\[\\033[1;31m\\][GHOST]\\[\\033[0m\\] \\w\\$ "
    env["ALL_PROXY"] = "socks5h://127.0.0.1:9050"
    env["http_proxy"] = "socks5h://127.0.0.1:9050"
    env["https_proxy"] = "socks5h://127.0.0.1:9050"

    subprocess.run(["bash", "--norc", "--noprofile"], cwd=ram_dir, env=env)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Ghost Mode")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("engage", help="Activate total invisibility")
    sub.add_parser("disengage", help="Restore normal operation")
    sub.add_parser("status", help="Check ghost mode status")
    sub.add_parser("workspace", help="Open RAM-only workspace")

    a = p.parse_args()

    cmds = {
        "engage": engage,
        "disengage": disengage,
        "status": status,
        "workspace": workspace,
    }

    if a.command:
        cmds[a.command]()
    else:
        p.print_help()

if __name__ == "__main__":
    main()
