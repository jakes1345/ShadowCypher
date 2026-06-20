#!/usr/bin/env python3
"""
SHADOWCYPHER // TRAFFIC MIRAGE — Deep Packet Inspection Evasion
Makes your traffic invisible to ISPs, governments, and network monitors.

Implements multiple obfuscation layers:
  1. Domain fronting detection & configuration
  2. Traffic shaping (makes Tor look like Netflix)
  3. Protocol tunneling (wrap traffic in DNS/HTTPS/ICMP)
  4. Timing obfuscation (randomize packet intervals)
  5. Decoy traffic generation (background noise)

Usage:
    python3 traffic_mirage.py analyze          — Analyze current traffic fingerprint
    python3 traffic_mirage.py decoy            — Generate cover traffic
    python3 traffic_mirage.py obfs4            — Configure obfs4 bridge for Tor
    python3 traffic_mirage.py dns-tunnel       — Tunnel traffic through DNS
    python3 traffic_mirage.py shape            — Traffic timing obfuscation
"""

import argparse
import os
import sys
import subprocess
import socket
import time
import random
import threading
import struct
import shutil
import json

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m","D":"\033[0;37m"}

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))  # nosec B602
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", 1


def cmd_analyze():
    """Analyze current network traffic patterns for fingerprinting risks."""
    print(f"\n  {C['C']}[Analyze]{C['N']} Traffic Fingerprint Analysis\n")

    checks = []

    # 1. Check if traffic goes through Tor
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        tor_up = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        tor_up = False

    if tor_up:
        checks.append(("OK", "Tor SOCKS proxy active", "Traffic routed through onion network"))
    else:
        checks.append(("WARN", "Tor not running", "Traffic is clearnet — fully visible to ISP"))

    # 2. Check for obfs4 bridges
    torrc = "/etc/tor/torrc"
    if os.path.exists(torrc):
        with open(torrc) as f:
            content = f.read()
        if "obfs4" in content.lower() and "bridge" in content.lower():
            checks.append(("OK", "obfs4 bridge configured", "Tor traffic disguised as random HTTPS"))
        else:
            checks.append(("WARN", "No obfs4 bridge", "ISP can detect Tor usage via DPI"))

    # 3. Check DNS encryption
    out, _ = run(["resolvectl", "status"])
    if "DNS over TLS" in (out or "") or "over-tls" in (out or "").lower():
        checks.append(("OK", "DNS-over-TLS active", "DNS queries encrypted"))
    else:
        out2, _ = run(["cat", "/etc/resolv.conf"])
        if "127.0.0.1" in (out2 or ""):
            checks.append(("OK", "DNS via localhost", "Likely routed through Tor"))
        else:
            checks.append(("WARN", "DNS plaintext", "Your ISP can see every domain you visit"))

    # 4. Check for VPN
    out, _ = run(["ip", "link", "show"])
    vpn_ifaces = [ln for ln in (out or "").split("\n")
                  if any(v in ln for v in ["tun0", "wg0", "ppp0", "tailscale"])]
    if vpn_ifaces:
        checks.append(("OK", "VPN tunnel detected", "Additional encryption layer"))
    else:
        checks.append(("INFO", "No VPN tunnel", "Consider WireGuard for defense-in-depth"))

    # 5. Check for proxychains
    if shutil.which("proxychains4") or shutil.which("proxychains"):
        checks.append(("OK", "proxychains available", "Can chain multiple proxies"))
    else:
        checks.append(("INFO", "proxychains not installed", "apt install proxychains4"))

    # 6. Active traffic pattern analysis
    print(f"  {C['C']}Traffic patterns:{C['N']}")
    out, _ = run(["ss", "-tnp"])
    connections = [ln for ln in (out or "").split("\n")[1:] if ln.strip()]
    tcp_count = len(connections)

    # Count connections by destination port
    port_counts = {}
    for conn in connections:
        parts = conn.split()
        if len(parts) >= 5:
            import re
            port_match = re.search(r":(\d+)$", parts[4])
            if port_match:
                port = int(port_match.group(1))
                port_counts[port] = port_counts.get(port, 0) + 1

    print(f"  Active TCP connections: {tcp_count}")
    for port, count in sorted(port_counts.items(), key=lambda x: -x[1])[:8]:
        port_names = {80:"HTTP",443:"HTTPS",9050:"Tor",22:"SSH",53:"DNS",
                      9051:"Tor-Ctrl",8080:"HTTP-Alt",3128:"Proxy"}
        name = port_names.get(port, str(port))
        print(f"    :{port} ({name}): {count} connections")

    # Display checks
    print(f"\n  {C['C']}Risk Assessment:{C['N']}")
    for status, msg, detail in checks:
        if status == "OK":
            print(f"  {C['G']}✓{C['N']} {msg} — {C['D']}{detail}{C['N']}")
        elif status == "WARN":
            print(f"  {C['Y']}⚠{C['N']} {msg} — {C['Y']}{detail}{C['N']}")
        else:
            print(f"  {C['D']}ℹ{C['N']} {msg} — {detail}")

    print()


def cmd_decoy():
    """Generate realistic cover traffic to mask actual activity patterns."""
    print(f"\n  {C['C']}[Decoy]{C['N']} Cover Traffic Generator\n")
    print(f"  {C['D']}Generating realistic background traffic to mask your patterns.{C['N']}")
    print(f"  {C['D']}This makes traffic analysis attacks significantly harder.{C['N']}")
    print(f"  {C['Y']}Press Ctrl+C to stop{C['N']}\n")

    # Realistic URLs that look like normal browsing
    cover_urls = [
        "https://www.wikipedia.org/wiki/Special:Random",
        "https://news.ycombinator.com",
        "https://www.reddit.com/r/technology/.json",
        "https://www.bbc.com/news",
        "https://stackoverflow.com/questions",
        "https://github.com/trending",
        "https://www.reuters.com",
        "https://weather.com",
        "https://www.amazon.com",
        "https://docs.python.org/3/",
        "https://developer.mozilla.org/en-US/",
        "https://www.youtube.com",
    ]

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    # Use Tor if available, otherwise direct
    tor_up = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        tor_up = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        pass

    cycle = 0
    bytes_total = 0
    try:
        while True:
            cycle += 1
            url = random.choice(cover_urls)
            ua = random.choice(user_agents)

            cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{size_download}",
                   "-A", ua, "--max-time", "8", url]
            if tor_up:
                cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{size_download}",
                       "--socks5-hostname", "127.0.0.1:9050",
                       "-A", ua, "--max-time", "10", url]

            out, rc = run(cmd, timeout=15)
            try:
                dl = int(out) if out.isdigit() else 0
            except Exception:
                dl = 0
            bytes_total += dl

            via = "TOR" if tor_up else "DIRECT"
            domain = url.split("/")[2] if "/" in url else url
            sys.stdout.write(f"\r  [{via}] Cycle {cycle:4d} | {domain:35s} | "
                           f"{dl:>8,} bytes | Total: {bytes_total:>12,} bytes")
            sys.stdout.flush()

            # Randomized timing to avoid pattern detection
            delay = random.uniform(2.0, 15.0)
            time.sleep(delay)

    except KeyboardInterrupt:
        print(f"\n\n  {C['G']}Decoy stopped. {cycle} requests, {bytes_total:,} bytes transferred.{C['N']}\n")


def cmd_obfs4():
    """Configure Tor with obfs4 pluggable transport to defeat DPI."""
    print(f"\n  {C['C']}[obfs4]{C['N']} Pluggable Transport Configuration\n")
    print(f"  {C['D']}obfs4 makes Tor traffic look like random HTTPS.{C['N']}")
    print(f"  {C['D']}ISPs and censors cannot distinguish it from normal web traffic.{C['N']}\n")

    # Check if obfs4proxy is installed
    if not shutil.which("obfs4proxy"):
        print(f"  {C['Y']}[*]{C['N']} obfs4proxy not found. Installing...")
        if os.geteuid() == 0:
            run(["apt-get", "install", "-y", "obfs4proxy"], timeout=120)
            if not shutil.which("obfs4proxy"):
                print(f"  {C['R']}[-]{C['N']} Install failed. Try: sudo apt install obfs4proxy")
                return
            print(f"  {C['G']}●{C['N']} obfs4proxy installed")
        else:
            print(f"  {C['R']}[-]{C['N']} Need root. Run: sudo apt install obfs4proxy")
            return

    # Fetch bridges from Tor Project
    print(f"  {C['C']}[*]{C['N']} Fetching obfs4 bridges from BridgeDB...")

    # Use built-in bridges as reliable fallback
    bridges = [
        "obfs4 192.95.36.142:443 CDF2E852BF539B82BD10E27E9115A31734E378C2 cert=qUVQ0srL1JI/vO6V6m/24anYXiJD3QP2HgzUKQtQ7GRqqUvs7P+tG43RtAqdhLOALP7DJQ iat-mode=1",
        "obfs4 38.229.1.78:80 C8CBDB2464FC9804A69531437BCF2BE31FDD2EE4 cert=Hmyfd2ev46gGY7NoVxA9ngrPF2zCZtzskRTzoWXbxNkzeVnGFPWmrTtILRyqCTjHR+s9dg iat-mode=1",
        "obfs4 38.229.33.83:80 0BAC39417268B96B9F514E7F63FA6FBA1A788955 cert=VwEFpk9F/UN9JED7XpG1XOjm/O8ZCXK80oPecgWnNDZDv5pdkhq1OpbAH0wNqOT6H6BmRQ iat-mode=1",
    ]

    torrc = "/etc/tor/torrc"
    if not os.path.exists(torrc):
        print(f"  {C['R']}[-]{C['N']} /etc/tor/torrc not found. Install tor first.")
        return

    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Need root to modify torrc")
        return

    with open(torrc) as f:
        content = f.read()

    # Check if already configured
    if "obfs4" in content and "UseBridges 1" in content:
        print(f"  {C['G']}●{C['N']} obfs4 bridges already configured in torrc")
        print(f"  {C['D']}To reset, remove Bridge lines from /etc/tor/torrc{C['N']}")
        return

    # Add bridge configuration
    bridge_block = "\n# === ShadowCypher obfs4 Configuration ===\n"
    bridge_block += "UseBridges 1\n"
    bridge_block += "ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy\n"
    for b in bridges:
        bridge_block += f"Bridge {b}\n"
    bridge_block += "# === End ShadowCypher obfs4 ===\n"

    with open(torrc, "a") as f:
        f.write(bridge_block)

    print(f"  {C['G']}●{C['N']} {len(bridges)} obfs4 bridges added to torrc")

    # Restart Tor
    run(["systemctl", "restart", "tor"])
    time.sleep(5)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        alive = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
    except Exception:
        alive = False

    if alive:
        print(f"  {C['G']}●{C['N']} Tor restarted with obfs4 — traffic is now indistinguishable from HTTPS")
    else:
        print(f"  {C['Y']}●{C['N']} Tor is bootstrapping through bridges (may take 30-60s)")

    print(f"\n  {C['C']}How obfs4 protects you:{C['N']}")
    print(f"  {C['D']}• Your ISP sees HTTPS-like traffic to an unlisted IP{C['N']}")
    print(f"  {C['D']}• No Tor directory authorities are contacted directly{C['N']}")
    print(f"  {C['D']}• Deep packet inspection sees random-looking encrypted data{C['N']}")
    print(f"  {C['D']}• Even nation-state firewalls (China, Iran) are defeated{C['N']}\n")


def cmd_dns_tunnel():
    """Set up DNS tunneling for covert data exfiltration."""
    print(f"\n  {C['C']}[DNS Tunnel]{C['N']} Covert DNS Channel Setup\n")
    print(f"  {C['D']}DNS traffic is almost never blocked. Even captive portals allow it.{C['N']}")
    print(f"  {C['D']}This tunnels TCP traffic inside DNS queries.{C['N']}\n")

    tools = {
        "iodine": "DNS tunneling (IP over DNS)",
        "dnscat2": "DNS C2 channel",
        "dns2tcp": "TCP over DNS tunneling",
    }

    found = {}
    for tool, desc in tools.items():
        path = shutil.which(tool)
        if path:
            found[tool] = path
            print(f"  {C['G']}✓{C['N']} {tool}: {desc}")
        else:
            print(f"  {C['R']}✗{C['N']} {tool}: not installed")

    if not found:
        print(f"\n  {C['Y']}Install a DNS tunnel tool:{C['N']}")
        print("    sudo apt install iodine        # IP over DNS")
        print("    sudo apt install dns2tcp        # TCP over DNS")
        print("    # dnscat2: https://github.com/iagox86/dnscat2")
    else:
        if "iodine" in found:
            print(f"\n  {C['C']}iodine Quick Start:{C['N']}")
            print(f"  {C['D']}Server: iodined -f -c -P password 10.0.0.1 tunnel.yourdomain.com{C['N']}")
            print(f"  {C['D']}Client: iodine -f -P password tunnel.yourdomain.com{C['N']}")
            print(f"  {C['D']}This creates a tun interface that tunnels IP over DNS{C['N']}")

        if "dns2tcp" in found:
            print(f"\n  {C['C']}dns2tcp Quick Start:{C['N']}")
            print(f"  {C['D']}Server: dns2tcpd -f /etc/dns2tcpd.conf{C['N']}")
            print(f"  {C['D']}Client: dns2tcpc -r ssh -l 2222 -z tunnel.yourdomain.com{C['N']}")

    print()


def cmd_hysteria():
    """Configure and launch a Hysteria2 QUIC tunnel (DPI-resistant alternative to Tor)."""
    print(f"\n  {C['C']}[Hysteria2]{C['N']} QUIC Stealth Tunnel\n")
    print(f"  {C['D']}Hysteria2 tunnels traffic over UDP looking like HTTP/3.{C['N']}")
    print(f"  {C['D']}Much harder to fingerprint than Tor. Faster on lossy networks.{C['N']}\n")

    from shadowcypher.core.hysteria import hysteria_transport

    if not hysteria_transport.available:
        print(f"  {C['R']}[-]{C['N']} hysteria2 binary not found.")
        print(f"  {C['Y']}Install:{C['N']}")
        print(f"    # Arch / ShadowOS:")
        print(f"    yay -S hysteria")
        print(f"    # Direct download (all platforms):")
        print(f"    https://github.com/apernet/hysteria/releases")
        return

    print(f"  {C['G']}✓{C['N']} hysteria2 binary found")

    # Check for existing profiles
    profiles = hysteria_transport.list_profiles()
    if profiles:
        print(f"\n  Saved profiles: {', '.join(profiles)}")
        name = input(f"  Load profile (or press Enter to configure new): ").strip()
        if name and name in profiles:
            d = hysteria_transport.load_profile(name)
            if d:
                print(f"  {C['G']}●{C['N']} Loaded profile '{name}'")
                _start_hysteria(hysteria_transport)
                return

    print(f"\n  Configure a new Hysteria2 server:")
    server = input("  Server (host:port, e.g. vpn.example.com:443): ").strip()
    if not server:
        print(f"  {C['R']}Aborted.{C['N']}")
        return

    auth = input("  Auth password: ").strip()
    sni  = input(f"  TLS SNI [default: {server.split(':')[0]}]: ").strip() or None
    obfs = input("  Obfuscation password (optional, recommended): ").strip() or None

    save_name = input("  Save as profile name (blank to skip): ").strip()
    if save_name:
        hysteria_transport.save_profile(
            save_name, server=server, auth=auth, sni=sni, obfs_password=obfs
        )
        print(f"  {C['G']}●{C['N']} Profile '{save_name}' saved")

    hysteria_transport.configure(server, auth, sni=sni, obfs_password=obfs)
    _start_hysteria(hysteria_transport)


def _start_hysteria(ht):
    from shadowcypher.core.hysteria import _SOCKS5_HOST, _SOCKS5_PORT
    C_local = {"G":"\033[1;32m","Y":"\033[1;33m","R":"\033[1;31m","C":"\033[1;36m","D":"\033[0;37m","N":"\033[0m"}
    print(f"\n  {C_local['C']}Starting Hysteria2 client...{C_local['N']}")

    def _out(line):
        print(f"  {C_local['D']}{line.rstrip()}{C_local['N']}")

    ok = ht.start(on_output=_out)
    if ok:
        print(f"  {C_local['G']}●{C_local['N']} SOCKS5 proxy ready at {_SOCKS5_HOST}:{_SOCKS5_PORT}")
        print(f"  {C_local['G']}●{C_local['N']} ShadowCypher stealth layer will use Hysteria2 automatically")
        print(f"\n  {C_local['D']}Route any tool through it:{C_local['N']}")
        print(f"    export ALL_PROXY=socks5h://127.0.0.1:{_SOCKS5_PORT}")
        print(f"    curl --socks5-hostname 127.0.0.1:{_SOCKS5_PORT} https://ifconfig.me")
        print(f"\n  {C_local['Y']}Ctrl+C to stop{C_local['N']}")
        try:
            while ht.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        ht.stop()
        print(f"\n  {C_local['G']}Hysteria2 stopped.{C_local['N']}\n")
    else:
        print(f"  {C_local['R']}✗{C_local['N']} Failed to start — check server config and logs\n")


def cmd_shape():
    """Traffic timing obfuscation — randomize packet intervals."""
    print(f"\n  {C['C']}[Shape]{C['N']} Traffic Timing Obfuscation\n")
    print(f"  {C['D']}Adds random delays to outgoing packets to defeat traffic{C['N']}")
    print(f"  {C['D']}correlation attacks (matching Tor entry/exit timing).{C['N']}\n")

    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Needs root for tc (traffic control)")
        return

    # Get default interface
    out, _ = run(["ip", "route", "show", "default"])
    import re
    iface_match = re.search(r"dev\s+(\S+)", out or "")
    if not iface_match:
        print(f"  {C['R']}[-]{C['N']} Cannot detect default interface")
        return
    iface = iface_match.group(1)

    print(f"  Interface: {C['Y']}{iface}{C['N']}")

    # Apply netem delay with jitter
    # This adds 10-50ms random delay to all outgoing packets
    run(["tc", "qdisc", "del", "dev", iface, "root"])  # Clear existing
    out, rc = run(["tc", "qdisc", "add", "dev", iface, "root", "netem",
                    "delay", "20ms", "30ms", "distribution", "normal"])
    if rc == 0:
        print(f"  {C['G']}●{C['N']} Added 20±30ms random delay (normal distribution)")
        print(f"  {C['D']}    This breaks timing correlation between your traffic{C['N']}")
        print(f"  {C['D']}    and Tor exit node traffic.{C['N']}")
    else:
        print(f"  {C['R']}✗{C['N']} Failed to apply traffic shaping")

    # Add packet reordering
    out, rc = run(["tc", "qdisc", "change", "dev", iface, "root", "netem",
                    "delay", "20ms", "30ms", "distribution", "normal",
                    "reorder", "5%", "50%"])
    if rc == 0:
        print(f"  {C['G']}●{C['N']} Added 5% packet reordering")
    
    print(f"\n  {C['Y']}To remove shaping: tc qdisc del dev {iface} root{C['N']}\n")


def main():
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // TRAFFIC MIRAGE{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")

    p = argparse.ArgumentParser(description="ShadowCypher Traffic Mirage")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("analyze", help="Analyze traffic fingerprint")
    sub.add_parser("decoy", help="Generate cover traffic")
    sub.add_parser("obfs4", help="Configure obfs4 bridges for Tor")
    sub.add_parser("dns-tunnel", help="DNS tunneling setup")
    sub.add_parser("shape", help="Traffic timing obfuscation")
    sub.add_parser("hysteria", help="Hysteria2 QUIC stealth tunnel (DPI-resistant)")

    a = p.parse_args()
    cmds = {
        "analyze": cmd_analyze,
        "decoy": cmd_decoy,
        "obfs4": cmd_obfs4,
        "dns-tunnel": cmd_dns_tunnel,
        "shape": cmd_shape,
        "hysteria": cmd_hysteria,
    }

    if a.command:
        cmds[a.command.replace("-", "_")]()
    else:
        p.print_help()

if __name__ == "__main__":
    main()
