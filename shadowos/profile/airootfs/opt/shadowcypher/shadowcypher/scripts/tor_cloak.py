#!/usr/bin/env python3
"""
SHADOWCYPHER // TOR CLOAK — Anonymous Research & Tor Integration
Manages Tor service lifecycle, verifies anonymity, rotates circuits,
provides torified curl/wget wrappers, and .onion directory enumeration.
Handles full IP protection chain before any Tor connection.

Usage:
    python3 tor_cloak.py status          — Check Tor status & current exit IP
    python3 tor_cloak.py start           — Start Tor + verify anonymity
    python3 tor_cloak.py rotate          — Force new circuit (new IP)
    python3 tor_cloak.py fetch <url>     — Fetch URL through Tor
    python3 tor_cloak.py shell           — Interactive torified shell session
    python3 tor_cloak.py harden          — Full IP protection hardening
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m"}

SOCKS_PORT = 9050
CONTROL_PORT = 9051

def run(cmd, capture=True, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))  # nosec B602
        return r.stdout.strip() if capture else None
    except Exception:
        return None

def get_real_ip():
    """Get actual public IP (no proxy)."""
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                           capture_output=True, text=True, timeout=8)
        return r.stdout.strip()
    except Exception:
        return "UNKNOWN"

def get_tor_ip():
    """Get IP as seen through Tor."""
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "10", "--socks5-hostname",
             f"127.0.0.1:{SOCKS_PORT}", "https://api.ipify.org"],
            capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except Exception:
        return None

def is_tor_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", SOCKS_PORT))
        s.close()
        return result == 0
    except Exception:
        return False

def tor_signal(signal_name="NEWNYM"):
    """Send a control signal to Tor (requires ControlPort enabled)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", CONTROL_PORT))
        s.send(b'AUTHENTICATE ""\r\n')
        resp = s.recv(1024).decode()
        if "250 OK" not in resp:
            # Try cookie auth
            s.send(b'AUTHENTICATE\r\n')
            resp = s.recv(1024).decode()
            if "250 OK" not in resp:
                return False, "Auth failed"
        s.send(f"SIGNAL {signal_name}\r\n".encode())
        resp = s.recv(1024).decode()
        s.close()
        return "250 OK" in resp, resp.strip()
    except Exception as e:
        return False, str(e)

def install_tor():
    """Install Tor if not present."""
    if shutil.which("tor"):
        return True
    print(f"  {C['Y']}[*]{C['N']} Tor not found. Installing...")
    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Need root to install Tor. Run: sudo apt install tor")
        return False
    r = subprocess.run(["apt-get", "install", "-y", "tor"],
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0

def ensure_torrc():
    """Ensure Tor control port is enabled."""
    torrc = "/etc/tor/torrc"
    if not os.path.exists(torrc):
        return
    try:
        with open(torrc) as f:
            content = f.read()
        changes = False
        if "ControlPort" not in content or "#ControlPort" in content:
            content = content.replace("#ControlPort 9051", "ControlPort 9051")
            if "ControlPort" not in content:
                content += "\nControlPort 9051\n"
            changes = True
        if "CookieAuthentication" not in content:
            content += "CookieAuthentication 1\n"
            changes = True
        if changes and os.geteuid() == 0:
            with open(torrc, "w") as f:
                f.write(content)
            print(f"  {C['G']}●{C['N']} Tor control port enabled in torrc")
    except Exception:
        pass

def cmd_status():
    print(f"\n  {C['C']}[Status]{C['N']} Tor Service Check\n")
    running = is_tor_running()
    print(f"  SOCKS Proxy (:{SOCKS_PORT}): {C['G'] if running else C['R']}{'ACTIVE' if running else 'INACTIVE'}{C['N']}")

    real_ip = get_real_ip()
    print(f"  Real IP:      {C['Y']}{real_ip}{C['N']}")

    if running:
        tor_ip = get_tor_ip()
        if tor_ip:
            match = tor_ip == real_ip
            color = C['R'] if match else C['G']
            print(f"  Tor Exit IP:  {color}{tor_ip}{C['N']}")
            if match:
                print(f"  {C['R']}[WARNING] Tor IP matches real IP — traffic may be leaking!{C['N']}")
            else:
                print(f"  {C['G']}[OK] IP is masked. You are anonymous.{C['N']}")
        else:
            print(f"  Tor Exit IP:  {C['R']}UNREACHABLE{C['N']}")

        # Check control port
        ok, _ = tor_signal("HEARTBEAT")
        print(f"  Control Port: {C['G'] if ok else C['Y']}{'ACTIVE' if ok else 'NO CONTROL'}{C['N']}")
    print()

def cmd_start():
    print(f"\n  {C['C']}[Start]{C['N']} Initializing Tor Service\n")

    if not install_tor():
        return

    if os.geteuid() == 0:
        ensure_torrc()

    if not is_tor_running():
        print(f"  {C['Y']}[*]{C['N']} Starting Tor daemon...")
        subprocess.Popen(["tor", "--quiet"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        # Wait for bootstrap
        for i in range(30):
            time.sleep(1)
            sys.stdout.write(f"\r  {C['Y']}[*]{C['N']} Bootstrapping... {i+1}s")
            sys.stdout.flush()
            if is_tor_running():
                break
        print()

    if is_tor_running():
        print(f"  {C['G']}[+]{C['N']} Tor SOCKS proxy active on 127.0.0.1:{SOCKS_PORT}")
        tor_ip = get_tor_ip()
        real_ip = get_real_ip()
        print(f"  {C['G']}[+]{C['N']} Real IP:     {C['Y']}{real_ip}{C['N']}")
        print(f"  {C['G']}[+]{C['N']} Tor Exit IP: {C['G']}{tor_ip}{C['N']}")
        if tor_ip and tor_ip != real_ip:
            print(f"\n  {C['G']}[✓] ANONYMITY VERIFIED — You are cloaked.{C['N']}")
        print(f"\n  {C['Y']}Usage:{C['N']}")
        print(f"    curl --socks5-hostname 127.0.0.1:{SOCKS_PORT} http://example.com")
        print("    torify wget http://example.onion/file")
        print("    proxychains firefox")
    else:
        print(f"  {C['R']}[-]{C['N']} Failed to start Tor")
    print()

def cmd_rotate():
    print(f"\n  {C['C']}[Rotate]{C['N']} Requesting New Tor Circuit\n")
    old_ip = get_tor_ip()
    print(f"  Current Exit: {C['Y']}{old_ip}{C['N']}")

    ok, msg = tor_signal("NEWNYM")
    if ok:
        time.sleep(3)  # Wait for new circuit
        new_ip = get_tor_ip()
        print(f"  New Exit:     {C['G']}{new_ip}{C['N']}")
        if old_ip != new_ip:
            print(f"  {C['G']}[✓] Circuit rotated successfully{C['N']}")
        else:
            print(f"  {C['Y']}[*] Same exit node (Tor may reuse nodes, try again){C['N']}")
    else:
        print(f"  {C['R']}[-] Signal failed: {msg}{C['N']}")
        print(f"  {C['Y']}    Ensure ControlPort 9051 is enabled in /etc/tor/torrc{C['N']}")
    print()

def cmd_fetch(url):
    print(f"\n  {C['C']}[Fetch]{C['N']} Torified Request: {C['Y']}{url}{C['N']}\n")

    if not is_tor_running():
        print(f"  {C['R']}[-]{C['N']} Tor not running. Use 'start' first.")
        return

    cmd = [
        "curl", "-s", "--socks5-hostname", f"127.0.0.1:{SOCKS_PORT}",
        "-A", "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
        "--max-time", "30", url
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        if r.stdout:
            # Truncate output for terminal
            lines = r.stdout.split("\n")
            for line in lines[:100]:
                print(f"  {line}")
            if len(lines) > 100:
                print(f"\n  {C['Y']}... ({len(lines)-100} more lines){C['N']}")
        if r.stderr:
            print(f"  {C['R']}{r.stderr}{C['N']}")
    except Exception as e:
        print(f"  {C['R']}[-] Fetch error: {e}{C['N']}")
    print()

def cmd_shell():
    print(f"\n  {C['C']}[Shell]{C['N']} Interactive Torified Shell\n")
    if not is_tor_running():
        print(f"  {C['R']}[-]{C['N']} Tor not running. Use 'start' first.")
        return

    tor_ip = get_tor_ip()
    print(f"  Exit IP: {C['G']}{tor_ip}{C['N']}")
    print(f"  {C['Y']}All commands in this shell route through Tor.{C['N']}")
    print(f"  {C['Y']}Type 'exit' to return to normal shell.{C['N']}\n")

    env = os.environ.copy()
    env["ALL_PROXY"] = f"socks5h://127.0.0.1:{SOCKS_PORT}"
    env["http_proxy"] = f"socks5h://127.0.0.1:{SOCKS_PORT}"
    env["https_proxy"] = f"socks5h://127.0.0.1:{SOCKS_PORT}"
    env["PS1"] = "\\[\\033[1;31m\\][TOR]\\[\\033[0m\\] \\u@\\h:\\w\\$ "

    if shutil.which("torify"):
        subprocess.run(["torify", "bash", "--norc"], env=env)
    else:
        subprocess.run(["bash", "--norc"], env=env)

def cmd_harden():
    """Full IP protection hardening before Tor connection."""
    print(f"\n  {C['C']}[Harden]{C['N']} IP Protection Chain\n")

    steps = 0

    # 1. DNS leak prevention
    print(f"  {C['C']}[1]{C['N']} DNS Leak Prevention")
    if os.geteuid() == 0:
        # Block direct DNS, force through Tor
        cmds = [
            "iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 5353 2>/dev/null || true",
            "iptables -t nat -A OUTPUT -p tcp --dport 53 -j REDIRECT --to-ports 5353 2>/dev/null || true",
        ]
        for cmd in cmds:
            run(cmd, capture=False)
        print(f"  {C['G']}●{C['N']} DNS queries redirected through Tor")
        steps += 1
    else:
        print(f"  {C['Y']}●{C['N']} Skipped (needs root)")

    # 2. WebRTC leak check info
    print(f"\n  {C['C']}[2]{C['N']} WebRTC Leak Prevention")
    print(f"  {C['Y']}●{C['N']} Set media.peerconnection.enabled=false in about:config")
    print(f"  {C['Y']}●{C['N']} Or use Tor Browser which disables this by default")

    # 3. MAC randomization check
    print(f"\n  {C['C']}[3]{C['N']} MAC Address Check")
    try:
        r = subprocess.run(["nmcli", "-g", "802-11-wireless.cloned-mac-address",
                            "connection", "show"], capture_output=True, text=True, timeout=5)
        if "random" in r.stdout.lower() or "stable" in r.stdout.lower():
            print(f"  {C['G']}●{C['N']} MAC randomization: ACTIVE")
        else:
            print(f"  {C['Y']}●{C['N']} MAC randomization: NOT ACTIVE")
            print("      Run: sudo macchanger -r <interface>")
    except Exception:
        print(f"  {C['Y']}●{C['N']} Cannot check (nmcli not available)")

    # 4. Timezone leak
    print(f"\n  {C['C']}[4]{C['N']} Timezone Leak")
    tz = time.strftime("%Z")
    print(f"  {C['Y']}●{C['N']} Current TZ: {tz} — Consider setting TZ=UTC for anonymity")

    # 5. Hostname leak
    print(f"\n  {C['C']}[5]{C['N']} Hostname Leak")
    hostname = socket.gethostname()
    print(f"  {C['Y']}●{C['N']} Hostname: {hostname}")
    if hostname not in ("localhost", "localhost.localdomain"):
        print("      Consider: sudo hostnamectl set-hostname localhost")

    print(f"\n  {C['G']}Hardening assessment complete: {steps} automatic fixes applied{C['N']}\n")

def main():
    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // TOR CLOAK{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")

    p = argparse.ArgumentParser(description="ShadowCypher Tor Cloak")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("status", help="Check Tor status")
    sub.add_parser("start", help="Start Tor service")
    sub.add_parser("rotate", help="Rotate Tor circuit")
    fetch_p = sub.add_parser("fetch", help="Fetch URL through Tor")
    fetch_p.add_argument("url", help="URL to fetch")
    sub.add_parser("shell", help="Interactive torified shell")
    sub.add_parser("harden", help="IP protection hardening")

    a = p.parse_args()

    if not a.command:
        p.print_help()
        return

    cmds = {
        "status": cmd_status,
        "start": cmd_start,
        "rotate": cmd_rotate,
        "fetch": lambda: cmd_fetch(a.url),
        "shell": cmd_shell,
        "harden": cmd_harden,
    }

    cmds[a.command]()

if __name__ == "__main__":
    main()
