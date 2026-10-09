#!/usr/bin/env python3
"""
SHADOWCYPHER // GUARDIAN — Personal Device Security Scanner
Scans YOUR devices (phone, PC, tablet, router, TV) on the local network
for security vulnerabilities, open ports, weak configurations, and threats.
Acts as an autonomous AI security assistant for personal protection.

Usage:
    python3 guardian.py scan                — Scan all devices on your network
    python3 guardian.py audit               — Deep audit this machine
    python3 guardian.py router              — Audit your home router
    python3 guardian.py monitor             — Continuous threat monitoring
    python3 guardian.py harden              — Auto-harden this machine
"""

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","N":"\033[0m","B":"\033[1m","D":"\033[0;37m"}

def run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, shell=isinstance(cmd, str))  # nosec B602
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", 1

def get_gateway():
    out, _ = run(["ip", "route", "show", "default"])
    m = re.search(r"default via (\S+)", out)
    return m.group(1) if m else None

def get_local_subnet():
    out, _ = run(["ip", "-o", "-4", "addr", "show"])
    for line in out.split("\n"):
        if "127.0.0.1" in line:
            continue
        m = re.search(r"inet (\d+\.\d+\.\d+)\.\d+/(\d+)", line)
        if m:
            return f"{m.group(1)}.0/{m.group(2)}"
    return None

def arp_scan_network(subnet):
    """Discover devices on the local network via ARP."""
    devices = []

    # Method 1: nmap ping sweep
    import shutil
    if shutil.which("nmap"):
        out, rc = run(["nmap", "-sn", "-n", subnet], timeout=30)
        if rc == 0:
            current_ip = None
            current_mac = None
            for line in out.split("\n"):
                ip_m = re.search(r"Nmap scan report for (\S+)", line)
                mac_m = re.search(r"MAC Address: (\S+)\s+\((.+?)\)", line)
                if ip_m:
                    if current_ip:
                        devices.append({"ip": current_ip, "mac": current_mac or "local", "vendor": ""})
                    current_ip = ip_m.group(1)
                    current_mac = None
                if mac_m:
                    current_mac = mac_m.group(1)
                    if current_ip:
                        devices.append({"ip": current_ip, "mac": current_mac, "vendor": mac_m.group(2)})
                        current_ip = None
                        current_mac = None
            if current_ip:
                devices.append({"ip": current_ip, "mac": current_mac or "local", "vendor": ""})
            return devices

    # Method 2: ARP table
    out, _ = run(["arp", "-n"])
    for line in out.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 3 and parts[2] != "(incomplete)":
            devices.append({"ip": parts[0], "mac": parts[2], "vendor": ""})
    return devices

def fingerprint_device(ip, timeout=3):
    """Quick port scan and OS fingerprint for a single device."""
    device = {"ip": ip, "open_ports": [], "services": [], "os_guess": "Unknown", "risk": "LOW"}

    # Common ports for consumer devices
    ports_to_check = {
        22: "SSH", 23: "Telnet", 53: "DNS", 80: "HTTP", 443: "HTTPS",
        445: "SMB", 548: "AFP", 554: "RTSP", 631: "CUPS/IPP",
        1900: "UPnP", 3389: "RDP", 5000: "UPnP/Synology", 5353: "mDNS",
        7547: "TR-069", 8008: "Chromecast", 8009: "Chromecast",
        8080: "HTTP-Alt", 8443: "HTTPS-Alt", 8888: "HTTP-Alt",
        9090: "WebUI", 9100: "Printer", 49152: "UPnP",
    }

    for port, service in ports_to_check.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                device["open_ports"].append(port)
                device["services"].append(service)
                # Banner grab
                try:
                    s.send(b"HEAD / HTTP/1.0\r\n\r\n")
                    banner = s.recv(256).decode("utf-8", errors="replace")
                    if "Android" in banner or "MiCO" in banner:
                        device["os_guess"] = "Android/IoT"
                    elif "Apple" in banner or "AirPlay" in banner:
                        device["os_guess"] = "Apple Device"
                    elif "Windows" in banner or "Microsoft" in banner:
                        device["os_guess"] = "Windows"
                    elif "Linux" in banner or "lighttpd" in banner or "nginx" in banner:
                        device["os_guess"] = "Linux"
                except Exception:
                    pass
            s.close()
        except Exception:
            pass

    # Risk assessment
    dangerous_ports = {23, 445, 3389, 7547, 9100}
    if dangerous_ports.intersection(device["open_ports"]):
        device["risk"] = "HIGH"
    elif len(device["open_ports"]) > 5:
        device["risk"] = "MEDIUM"

    return device


def cmd_scan():
    print(f"\n  {C['C']}[Scan]{C['N']} Discovering devices on your network\n")

    subnet = get_local_subnet()
    gateway = get_gateway()
    if not subnet:
        print(f"  {C['R']}[-]{C['N']} Cannot determine local subnet")
        return

    print(f"  Subnet:  {C['Y']}{subnet}{C['N']}")
    print(f"  Gateway: {C['Y']}{gateway}{C['N']}\n")

    # Discover devices
    print(f"  {C['C']}[*]{C['N']} ARP scanning network...")
    devices = arp_scan_network(subnet)
    print(f"  {C['G']}[+]{C['N']} Found {len(devices)} devices\n")

    if not devices:
        print(f"  {C['Y']}No devices found. Try running with sudo.{C['N']}")
        return

    # Fingerprint each device
    print(f"  {C['C']}[*]{C['N']} Fingerprinting devices...\n")
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(fingerprint_device, d["ip"]): d for d in devices}
        for future in as_completed(futures):
            orig = futures[future]
            fp = future.result()
            fp["mac"] = orig.get("mac", "")
            fp["vendor"] = orig.get("vendor", "")
            results.append(fp)

    # Display results
    risk_colors = {"HIGH": C['R'], "MEDIUM": C['Y'], "LOW": C['G']}
    results.sort(key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x["risk"]])

    for dev in results:
        rc = risk_colors.get(dev["risk"], C['D'])
        is_gw = " (GATEWAY)" if dev["ip"] == gateway else ""
        print(f"  {rc}[{dev['risk']:6s}]{C['N']} {C['Y']}{dev['ip']:15s}{C['N']} "
              f"{dev['mac']:17s}  {dev.get('vendor',''):20s} {dev['os_guess']}{is_gw}")
        if dev["open_ports"]:
            port_str = ", ".join(f"{p}/{s}" for p, s in zip(dev["open_ports"], dev["services"]))
            print(f"           Ports: {C['D']}{port_str}{C['N']}")
        if dev["risk"] == "HIGH":
            dangerous = set(dev["open_ports"]).intersection({23, 445, 3389, 7547})
            for dp in dangerous:
                if dp == 23:
                    print(f"           {C['R']}⚠ Telnet exposed — unencrypted remote access!{C['N']}")
                elif dp == 445:
                    print(f"           {C['R']}⚠ SMB exposed — potential EternalBlue target{C['N']}")
                elif dp == 3389:
                    print(f"           {C['R']}⚠ RDP exposed — brute-force target{C['N']}")
                elif dp == 7547:
                    print(f"           {C['R']}⚠ TR-069 exposed — ISP remote management{C['N']}")

    print(f"\n  {C['B']}Summary:{C['N']} {len(results)} devices | "
          f"{C['R']}{sum(1 for d in results if d['risk']=='HIGH')} HIGH{C['N']} | "
          f"{C['Y']}{sum(1 for d in results if d['risk']=='MEDIUM')} MED{C['N']} | "
          f"{C['G']}{sum(1 for d in results if d['risk']=='LOW')} LOW{C['N']}\n")


def cmd_audit():
    print(f"\n  {C['C']}[Audit]{C['N']} Deep security audit of this machine\n")

    checks = []

    # 1. OS updates
    out, rc = run(["apt", "list", "--upgradable"], timeout=30)
    upgradable = len([ln for ln in out.split("\n") if "upgradable" in ln.lower()])
    if upgradable > 0:
        checks.append(("WARN", f"{upgradable} packages need security updates", "Run: sudo apt upgrade"))
    else:
        checks.append(("OK", "System packages up to date", ""))

    # 2. SUID binaries
    if os.geteuid() == 0:
        out, _ = run(["find", "/", "-perm", "-4000", "-type", "f"], timeout=20)
        suid_files = [f for f in out.split("\n") if f.strip()]
        suspicious = [f for f in suid_files if any(x in f for x in
                      ["python", "perl", "ruby", "node", "vim", "find", "bash", "nmap", "env"])]
        if suspicious:
            checks.append(("FAIL", f"Suspicious SUID binaries: {', '.join(suspicious[:5])}", "PrivAudit risk"))
        else:
            checks.append(("OK", f"{len(suid_files)} SUID binaries (none suspicious)", ""))

    # 3. SSH hardening
    ssh_conf = "/etc/ssh/sshd_config"
    if os.path.exists(ssh_conf):
        with open(ssh_conf) as f:
            ssh = f.read()
        if "PermitRootLogin no" in ssh or "PermitRootLogin prohibit-password" in ssh:
            checks.append(("OK", "SSH root login disabled", ""))
        else:
            checks.append(("WARN", "SSH allows root login", "Set PermitRootLogin no"))
        if "PasswordAuthentication no" in ssh:
            checks.append(("OK", "SSH password auth disabled (key-only)", ""))
        else:
            checks.append(("WARN", "SSH allows password authentication", "Use key-based auth"))

    # 4. World-writable files in sensitive dirs
    if os.geteuid() == 0:
        out, _ = run(["find", "/etc", "-type", "f", "-perm", "-o+w"], timeout=10)
        ww_files = [f for f in out.split("\n") if f.strip()]
        if ww_files:
            checks.append(("FAIL", f"{len(ww_files)} world-writable files in /etc", "Security risk"))
        else:
            checks.append(("OK", "No world-writable files in /etc", ""))

    # 5. Listening services
    out, _ = run(["ss", "-tlnp"])
    listeners = [ln for ln in out.split("\n")[1:] if ln.strip()]
    checks.append(("INFO", f"{len(listeners)} services listening", ""))

    # 6. Failed login attempts
    out, _ = run(["journalctl", "-u", "sshd", "--since", "24 hours ago", "--no-pager", "-q"])
    failed = out.count("Failed password")
    if failed > 100:
        checks.append(("FAIL", f"{failed} failed SSH logins in 24h", "Possible brute-force attack"))
    elif failed > 10:
        checks.append(("WARN", f"{failed} failed SSH logins in 24h", "Monitor closely"))
    else:
        checks.append(("OK", f"{failed} failed SSH logins in 24h", "Normal"))

    # Display
    for status, msg, detail in checks:
        if status == "OK":
            print(f"  {C['G']}✓{C['N']} {msg}")
        elif status == "WARN":
            print(f"  {C['Y']}⚠{C['N']} {msg}" + (f" — {C['Y']}{detail}{C['N']}" if detail else ""))
        elif status == "FAIL":
            print(f"  {C['R']}✗{C['N']} {msg}" + (f" — {C['R']}{detail}{C['N']}" if detail else ""))
        else:
            print(f"  {C['D']}ℹ{C['N']} {msg}")
    print()


def cmd_router():
    print(f"\n  {C['C']}[Router]{C['N']} Home Router Security Audit\n")

    gateway = get_gateway()
    if not gateway:
        print(f"  {C['R']}[-]{C['N']} Cannot detect default gateway")
        return

    print(f"  Gateway: {C['Y']}{gateway}{C['N']}\n")

    fp = fingerprint_device(gateway, timeout=5)

    # Router-specific checks
    dangerous_router_ports = {
        23: ("Telnet", "CRITICAL — disable immediately, use SSH instead"),
        7547: ("TR-069/CWMP", "ISP remote management — disable in router admin"),
        8089: ("TR-069 alt", "ISP remote management — disable in router admin"),
        80: ("HTTP Admin", "Consider switching to HTTPS-only"),
        21: ("FTP", "Disable — use SFTP if file sharing needed"),
        1900: ("UPnP", "Disable — attack vector for port-mapping abuse"),
        5000: ("UPnP alt", "Disable UPnP in router settings"),
    }

    for port in fp["open_ports"]:
        if port in dangerous_router_ports:
            name, advice = dangerous_router_ports[port]
            print(f"  {C['R']}✗{C['N']} Port {port} ({name}) — {advice}")
        else:
            print(f"  {C['D']}ℹ{C['N']} Port {port} open")

    if not fp["open_ports"]:
        print(f"  {C['G']}✓{C['N']} No dangerous ports detected on gateway")

    # DNS check
    print(f"\n  {C['C']}DNS Configuration:{C['N']}")
    out, _ = run(["nslookup", "cloudflare.com", gateway])
    if "NXDOMAIN" not in out and out:
        print(f"  {C['G']}✓{C['N']} Router resolves DNS")
    else:
        print(f"  {C['Y']}⚠{C['N']} Router DNS may be misconfigured")

    print(f"\n  {C['C']}Recommendations:{C['N']}")
    print("  • Change default admin password")
    print("  • Disable WPS (Wi-Fi Protected Setup)")
    print("  • Enable WPA3 if supported, minimum WPA2-AES")
    print("  • Disable UPnP")
    print("  • Update router firmware")
    print("  • Set custom DNS (1.1.1.1 or 9.9.9.9) or DNS-over-HTTPS\n")


def cmd_monitor():
    print(f"\n  {C['C']}[Monitor]{C['N']} Continuous Threat Monitoring\n")
    print(f"  {C['Y']}Watching for:{C['N']} new devices, port changes, ARP spoofing")
    print("  Press Ctrl+C to stop\n")

    subnet = get_local_subnet()
    if not subnet:
        print(f"  {C['R']}[-]{C['N']} Cannot determine subnet")
        return

    known_devices = {}
    cycle = 0

    try:
        while True:
            cycle += 1
            devices = arp_scan_network(subnet)
            current_ips = {d["ip"] for d in devices}

            for dev in devices:
                ip = dev["ip"]
                mac = dev.get("mac", "")
                if ip not in known_devices:
                    known_devices[ip] = {"mac": mac, "first_seen": time.time()}
                    if cycle > 1:
                        print(f"  {C['R']}⚠ NEW DEVICE{C['N']} {ip} ({mac}) — appeared at {time.strftime('%H:%M:%S')}")
                else:
                    old_mac = known_devices[ip]["mac"]
                    if mac and old_mac and mac != old_mac and mac != "local":
                        print(f"  {C['R']}⚠ ARP SPOOF DETECTED{C['N']} {ip}: MAC changed {old_mac} → {mac}")
                    known_devices[ip]["mac"] = mac

            # Check for disappeared devices
            if cycle > 1:
                for ip in list(known_devices.keys()):
                    if ip not in current_ips:
                        print(f"  {C['Y']}ℹ DEVICE LEFT{C['N']} {ip} at {time.strftime('%H:%M:%S')}")
                        del known_devices[ip]

            sys.stdout.write(f"\r  {C['D']}[{time.strftime('%H:%M:%S')}] Cycle {cycle} — {len(known_devices)} devices tracked{C['N']}    ")
            sys.stdout.flush()
            time.sleep(30)

    except KeyboardInterrupt:
        print(f"\n\n  {C['G']}Monitoring stopped. {len(known_devices)} devices tracked over {cycle} cycles.{C['N']}\n")


def cmd_harden():
    print(f"\n  {C['C']}[Harden]{C['N']} Auto-hardening this machine\n")

    if os.geteuid() != 0:
        print(f"  {C['R']}[-]{C['N']} Requires root. Run with sudo.")
        return

    fixes = 0

    # 1. Enable automatic security updates
    out, rc = run(["dpkg", "-l", "unattended-upgrades"])
    if "ii" not in out:
        print(f"  {C['C']}[1]{C['N']} Installing unattended-upgrades...")
        run(["apt-get", "install", "-y", "unattended-upgrades"], timeout=60)
        run(["dpkg-reconfigure", "-f", "noninteractive", "unattended-upgrades"])
        print(f"  {C['G']}✓{C['N']} Automatic security updates enabled")
        fixes += 1
    else:
        print(f"  {C['G']}✓{C['N']} Automatic security updates already enabled")

    # 2. SSH hardening
    ssh_conf = "/etc/ssh/sshd_config"
    if os.path.exists(ssh_conf):
        with open(ssh_conf) as f:
            content = f.read()
        modified = False
        if "PermitRootLogin yes" in content:
            content = content.replace("PermitRootLogin yes", "PermitRootLogin no")
            modified = True
        if "#PermitRootLogin" in content:
            content = content.replace("#PermitRootLogin prohibit-password", "PermitRootLogin no")
            modified = True
        if modified:
            with open(ssh_conf, "w") as f:
                f.write(content)
            run(["systemctl", "restart", "sshd"])
            print(f"  {C['G']}✓{C['N']} SSH root login disabled")
            fixes += 1

    # 3. Firewall setup
    out, _ = run(["iptables", "-L", "INPUT", "-n"])
    if "DROP" not in out and "REJECT" not in out:
        run(["iptables", "-A", "INPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])
        run(["iptables", "-A", "INPUT", "-i", "lo", "-j", "ACCEPT"])
        run(["iptables", "-A", "INPUT", "-p", "icmp", "-j", "ACCEPT"])
        run(["iptables", "-P", "INPUT", "DROP"])
        print(f"  {C['G']}✓{C['N']} Firewall: default DROP policy applied")
        fixes += 1

    # 4. Disable core dumps
    with open("/etc/security/limits.conf") as f:
        limits = f.read()
    if "core" not in limits:
        with open("/etc/security/limits.conf", "a") as f:
            f.write("\n* hard core 0\n* soft core 0\n")
        print(f"  {C['G']}✓{C['N']} Core dumps disabled")
        fixes += 1

    # 5. Set file permissions
    sensitive_files = ["/etc/shadow", "/etc/gshadow", "/etc/passwd-"]
    for sf in sensitive_files:
        if os.path.exists(sf):
            os.chmod(sf, 0o640)
    print(f"  {C['G']}✓{C['N']} Sensitive file permissions hardened")
    fixes += 1

    print(f"\n  {C['G']}{fixes} hardening fixes applied{C['N']}\n")


def main():
    print(f"\n{C['B']}{'═'*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // GUARDIAN — Personal Device Security{C['N']}")
    print(f"{C['B']}{'═'*70}{C['N']}")

    p = argparse.ArgumentParser(description="ShadowCypher Guardian")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("scan", help="Scan all network devices")
    sub.add_parser("audit", help="Deep audit this machine")
    sub.add_parser("router", help="Audit home router")
    sub.add_parser("monitor", help="Continuous threat monitoring")
    sub.add_parser("harden", help="Auto-harden this machine")
    a = p.parse_args()

    cmds = {
        "scan": cmd_scan,
        "audit": cmd_audit,
        "router": cmd_router,
        "monitor": cmd_monitor,
        "harden": cmd_harden,
    }

    if a.command:
        cmds[a.command]()
    else:
        p.print_help()

if __name__ == "__main__":
    main()
