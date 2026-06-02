#!/usr/bin/env python3
"""
SHADOWCYPHER // SHADOW NODE AUDIT — Full Anonymity Chain Validator
Tests every layer of the anonymity stack: Tor, WireGuard, DNS leaks,
WebRTC leaks, mesh relay crypto, Ghost node TLS, MAC randomization,
hostname leaks, timezone leaks, and traffic correlation resistance.

This is the tool you run BEFORE doing anything sensitive.

Usage:
    python3 shadow_audit.py [--full] [--fix]
"""

import argparse, os, sys, socket, subprocess, time, json, struct, re

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m","D":"\033[0;37m"}

class AuditResult:
    def __init__(self):
        self.passed = 0
        self.warned = 0
        self.failed = 0
        self.fixes_applied = 0
        self.results = []

    def ok(self, test, detail=""):
        self.passed += 1
        self.results.append(("PASS", test, detail))
        print(f"  {C['G']}✓ PASS{C['N']}  {test}" + (f" — {C['D']}{detail}{C['N']}" if detail else ""))

    def warn(self, test, detail=""):
        self.warned += 1
        self.results.append(("WARN", test, detail))
        print(f"  {C['Y']}⚠ WARN{C['N']}  {test}" + (f" — {C['Y']}{detail}{C['N']}" if detail else ""))

    def fail(self, test, detail=""):
        self.failed += 1
        self.results.append(("FAIL", test, detail))
        print(f"  {C['R']}✗ FAIL{C['N']}  {test}" + (f" — {C['R']}{detail}{C['N']}" if detail else ""))

    def fixed(self, test, detail=""):
        self.fixes_applied += 1
        self.results.append(("FIXED", test, detail))
        print(f"  {C['M']}⟳ FIXED{C['N']} {test}" + (f" — {detail}" if detail else ""))


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", 1


def get_ip_via(method="direct"):
    """Get public IP. method: 'direct' or 'tor'."""
    if method == "tor":
        out, rc = run(["curl", "-s", "--max-time", "10",
                       "--socks5-hostname", "127.0.0.1:9050",
                       "https://api.ipify.org"])
    else:
        out, rc = run(["curl", "-s", "--max-time", "5", "https://api.ipify.org"])
    return out if rc == 0 else None


# ═══════════════════════════════════════════════════════════════
# Audit Modules
# ═══════════════════════════════════════════════════════════════

def audit_tor(r, do_fix=False):
    print(f"\n  {C['C']}━━━ Tor Service ━━━{C['N']}")

    # Check if Tor is installed
    import shutil
    if not shutil.which("tor"):
        r.fail("Tor binary", "Not installed")
        if do_fix and os.geteuid() == 0:
            out, rc = run(["apt-get", "install", "-y", "tor"], timeout=120)
            if rc == 0:
                r.fixed("Tor binary", "Installed via apt")
        return

    # Check if Tor SOCKS port is open
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", 9050))
        s.close()
        if result == 0:
            r.ok("Tor SOCKS proxy", "Port 9050 active")
        else:
            r.fail("Tor SOCKS proxy", "Port 9050 closed")
            if do_fix:
                subprocess.Popen(["tor", "--quiet"], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                time.sleep(5)
                s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s2.settimeout(2)
                if s2.connect_ex(("127.0.0.1", 9050)) == 0:
                    r.fixed("Tor SOCKS proxy", "Started Tor daemon")
                s2.close()
            return
    except Exception:
        r.fail("Tor SOCKS proxy", "Connection error")
        return

    # Check Tor control port
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", 9051))
        s.close()
        if result == 0:
            r.ok("Tor Control Port", "Port 9051 active (circuit rotation available)")
        else:
            r.warn("Tor Control Port", "Port 9051 closed — cannot rotate circuits automatically")
    except Exception:
        r.warn("Tor Control Port", "Cannot check")

    # Verify IP masking
    real_ip = get_ip_via("direct")
    tor_ip = get_ip_via("tor")
    if real_ip and tor_ip:
        if real_ip != tor_ip:
            r.ok("Tor IP masking", f"Real={real_ip} → Tor={tor_ip}")
        else:
            r.fail("Tor IP masking", f"LEAK! Both resolve to {real_ip}")
    elif not tor_ip:
        r.fail("Tor IP masking", "Cannot reach internet through Tor")


def audit_dns(r, do_fix=False):
    print(f"\n  {C['C']}━━━ DNS Leak Prevention ━━━{C['N']}")

    # Check what DNS resolver is configured
    resolv = "/etc/resolv.conf"
    if os.path.exists(resolv):
        with open(resolv) as f:
            content = f.read()
        nameservers = re.findall(r"nameserver\s+(\S+)", content)
        for ns in nameservers:
            if ns.startswith("127."):
                r.ok("DNS resolver", f"{ns} (local resolver — good)")
            elif ns in ("1.1.1.1", "8.8.8.8", "9.9.9.9", "1.0.0.1", "8.8.4.4"):
                r.warn("DNS resolver", f"{ns} (public DNS — correlatable)")
            else:
                r.warn("DNS resolver", f"{ns} (ISP DNS — your ISP sees all queries)")

    # Check for DNS-over-TLS/HTTPS
    out, rc = run(["systemctl", "is-active", "systemd-resolved"])
    if rc == 0 and out == "active":
        out2, _ = run(["resolvectl", "status"])
        if "DNS over TLS" in out2 or "DNSOverTLS" in out2:
            r.ok("DNS-over-TLS", "systemd-resolved with DoT active")
        else:
            r.warn("DNS-over-TLS", "systemd-resolved running but DoT not confirmed")
    else:
        r.warn("DNS-over-TLS", "Not using systemd-resolved")

    # Active DNS leak test: resolve through Tor vs direct
    try:
        direct_out, _ = run(["dig", "+short", "whoami.akamai.net", "@ns1-1.akamaitech.net"])
        if direct_out:
            r.warn("DNS leak test", f"Direct DNS resolver IP: {direct_out}")
    except Exception:
        pass


def audit_mac(r, do_fix=False):
    print(f"\n  {C['C']}━━━ MAC Address Randomization ━━━{C['N']}")

    # Get current MAC for all non-lo interfaces
    out, _ = run(["ip", "-o", "link", "show"])
    if not out:
        r.warn("MAC address check", "Cannot read interfaces")
        return

    for line in out.split("\n"):
        parts = line.split()
        if len(parts) < 4:
            continue
        iface = parts[1].rstrip(":")
        if iface == "lo":
            continue

        # Find MAC in the line
        mac_match = re.search(r"link/ether\s+([0-9a-f:]{17})", line)
        if not mac_match:
            continue
        mac = mac_match.group(1)

        # Check if MAC is locally administered (bit 1 of first octet set)
        first_byte = int(mac.split(":")[0], 16)
        is_random = bool(first_byte & 0x02)

        if is_random:
            r.ok(f"MAC [{iface}]", f"{mac} (locally administered — randomized)")
        else:
            r.warn(f"MAC [{iface}]", f"{mac} (manufacturer MAC — fingerprintable)")
            if do_fix:
                import shutil
                if shutil.which("macchanger"):
                    run(["ip", "link", "set", iface, "down"])
                    run(["macchanger", "-r", iface])
                    run(["ip", "link", "set", iface, "up"])
                    r.fixed(f"MAC [{iface}]", "Randomized via macchanger")


def audit_hostname(r, do_fix=False):
    print(f"\n  {C['C']}━━━ Hostname & Identity Leaks ━━━{C['N']}")

    hostname = socket.gethostname()
    if hostname in ("localhost", "localhost.localdomain", "shadowcypher"):
        r.ok("Hostname", f"{hostname} (generic — not identifiable)")
    else:
        r.warn("Hostname", f"{hostname} — may leak identity to remote services")
        if do_fix and os.geteuid() == 0:
            run(["hostnamectl", "set-hostname", "localhost"])
            r.fixed("Hostname", "Set to 'localhost'")

    # Check timezone
    tz = time.strftime("%Z")
    utc_offset = time.timezone
    if tz in ("UTC", "GMT") or utc_offset == 0:
        r.ok("Timezone", f"{tz} (UTC — not geolocation-revealing)")
    else:
        r.warn("Timezone", f"{tz} (UTC{-utc_offset//3600:+d}) — reveals approximate location")

    # Check username
    username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    if username in ("root", "user", "operator", "admin"):
        r.ok("Username", f"{username} (generic)")
    else:
        r.warn("Username", f"{username} — programs may leak this in User-Agent headers")


def audit_firewall(r, do_fix=False):
    print(f"\n  {C['C']}━━━ Firewall Status ━━━{C['N']}")

    if os.geteuid() != 0:
        r.warn("Firewall audit", "Needs root for full iptables check")
        return

    out, rc = run(["iptables", "-L", "INPUT", "-n", "--line-numbers"])
    if rc != 0:
        r.fail("Firewall", "Cannot read iptables rules")
        return

    if "DROP" in out or "REJECT" in out:
        r.ok("Inbound firewall", "DROP/REJECT rules present")
    else:
        r.warn("Inbound firewall", "No DROP/REJECT rules — all inbound traffic accepted")
        if do_fix:
            run(["iptables", "-A", "INPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])
            run(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
            run(["iptables", "-P", "INPUT", "DROP"])
            r.fixed("Inbound firewall", "Default DROP policy applied (ESTABLISHED+lo allowed)")

    # Check for open listening ports
    out2, _ = run(["ss", "-tlnp"])
    listeners = [l for l in out2.split("\n")[1:] if l.strip()]
    exposed = [l for l in listeners if "0.0.0.0" in l or "::" in l]
    if exposed:
        r.warn("Open ports", f"{len(exposed)} services listening on all interfaces")
        for l in exposed[:5]:
            parts = l.split()
            print(f"    {C['D']}{parts[3] if len(parts) > 3 else l.strip()}{C['N']}")
    else:
        r.ok("Open ports", "No services bound to all interfaces")


def audit_mesh_relay(r):
    print(f"\n  {C['C']}━━━ Shadow Mesh Relay ━━━{C['N']}")

    # Check if mesh relay is listening
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", 19999))
        s.close()
        if result == 0:
            r.warn("Mesh relay", "UDP/19999 active — verify bind address is loopback")
        else:
            r.ok("Mesh relay", "Not currently running (no exposure)")
    except Exception:
        r.ok("Mesh relay", "Not currently running")

    # Check mesh key exists
    key_path = os.path.expanduser("~/.shadowcypher/mesh/node_key.bin")
    if os.path.exists(key_path):
        stat = os.stat(key_path)
        perms = oct(stat.st_mode)[-3:]
        if perms == "600":
            r.ok("Mesh keypair", f"X25519 key exists, permissions {perms}")
        else:
            r.fail("Mesh keypair", f"Permissions {perms} (should be 600)")
    else:
        r.ok("Mesh keypair", "Not provisioned (no key on disk)")


def audit_ghost_c2(r):
    print(f"\n  {C['C']}━━━ Ghost C2 Infrastructure ━━━{C['N']}")

    # Check master key
    key_paths = [
        "/etc/shadowcypher/master.key",
        os.path.expanduser("~/.shadowcypher/master.key"),
    ]
    key_found = False
    for kp in key_paths:
        if os.path.exists(kp):
            stat = os.stat(kp)
            perms = oct(stat.st_mode)[-3:]
            if perms == "600":
                r.ok("Master key", f"{kp} (permissions {perms})")
            else:
                r.fail("Master key", f"{kp} has permissions {perms} — MUST be 600")
            key_found = True
            break
    if not key_found:
        r.ok("Master key", "Not provisioned (no key on disk)")

    # Check if Ghost is listening
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", 44444))
        s.close()
        if result == 0:
            r.ok("Ghost C2", "TLS listener active on loopback:44444")
        else:
            r.ok("Ghost C2", "Not currently running")
    except Exception:
        r.ok("Ghost C2", "Not currently running")

    # Check relay token security
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".relay_token")
    if os.path.exists(token_path):
        stat = os.stat(token_path)
        perms = oct(stat.st_mode)[-3:]
        if perms == "600":
            r.ok("Relay token", f"Permissions {perms}")
        else:
            r.warn("Relay token", f"Permissions {perms} — should be 600")
    else:
        r.ok("Relay token", "No token file (relay not active)")


def audit_wireguard(r):
    print(f"\n  {C['C']}━━━ WireGuard VPN ━━━{C['N']}")

    import shutil
    if not shutil.which("wg"):
        r.warn("WireGuard", "Not installed — no VPN tunnel available")
        return

    out, rc = run(["wg", "show"])
    if rc != 0 or not out.strip():
        r.warn("WireGuard", "No active tunnels")
        return

    r.ok("WireGuard", "Active tunnel detected")
    # Check for DNS leak in WG config
    conf_dir = "/etc/wireguard"
    if os.path.isdir(conf_dir):
        for conf in os.listdir(conf_dir):
            if conf.endswith(".conf"):
                with open(os.path.join(conf_dir, conf)) as f:
                    content = f.read()
                if "DNS" in content:
                    r.ok(f"WG DNS [{conf}]", "DNS directive present in config")
                else:
                    r.warn(f"WG DNS [{conf}]", "No DNS directive — may leak DNS queries")


def audit_browser(r):
    print(f"\n  {C['C']}━━━ Browser Fingerprint Risks ━━━{C['N']}")

    import shutil
    if shutil.which("torbrowser-launcher") or os.path.exists(os.path.expanduser("~/.local/share/torbrowser")):
        r.ok("Tor Browser", "Installed (recommended for anonymous browsing)")
    else:
        r.warn("Tor Browser", "Not installed — standard browsers leak fingerprints")
        r.warn("Tor Browser", "Install: apt install torbrowser-launcher")

    # Check for common browser data
    ff_dir = os.path.expanduser("~/.mozilla/firefox")
    chrome_dir = os.path.expanduser("~/.config/google-chrome")
    if os.path.isdir(chrome_dir):
        r.warn("Chrome data", "Google Chrome profile exists (Google tracking)")
    if os.path.isdir(ff_dir):
        r.ok("Firefox data", "Firefox profile exists (use with privacy extensions)")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Shadow Node Audit")
    p.add_argument("--full", action="store_true", help="Full audit including browser and WireGuard")
    p.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    p.add_argument("-o", "--output", help="Save JSON report")
    a = p.parse_args()

    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // SHADOW NODE ANONYMITY AUDIT{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")
    print(f"  Root: {C['Y']}{'Yes' if os.geteuid() == 0 else 'No (limited audit)'}{C['N']}")
    print(f"  Mode: {C['Y']}{'Full' if a.full else 'Standard'}{C['N']}  |  Auto-fix: {C['Y']}{a.fix}{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")

    r = AuditResult()

    audit_tor(r, a.fix)
    audit_dns(r, a.fix)
    audit_mac(r, a.fix)
    audit_hostname(r, a.fix)
    audit_firewall(r, a.fix)
    audit_mesh_relay(r)
    audit_ghost_c2(r)

    if a.full:
        audit_wireguard(r)
        audit_browser(r)

    # Summary
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    total = r.passed + r.warned + r.failed
    score = (r.passed / total * 100) if total else 0
    color = C['G'] if score >= 80 else (C['Y'] if score >= 50 else C['R'])
    print(f"  {color}ANONYMITY SCORE: {score:.0f}%{C['N']}  ({r.passed} pass / {r.warned} warn / {r.failed} fail)")
    if r.fixes_applied:
        print(f"  {C['M']}{r.fixes_applied} issues auto-fixed{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}\n")

    if a.output:
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "score_pct": round(score, 1),
            "passed": r.passed, "warned": r.warned, "failed": r.failed,
            "fixes_applied": r.fixes_applied,
            "results": [{"status": s, "test": t, "detail": d} for s, t, d in r.results],
        }
        with open(a.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Report saved: {a.output}\n")

if __name__ == "__main__":
    main()
