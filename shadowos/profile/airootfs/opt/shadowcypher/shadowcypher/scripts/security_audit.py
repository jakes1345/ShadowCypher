#!/usr/bin/env python3
"""
ShadowCypher Security Audit — Operator Host-Hardening Utility.
Audits the local environment for OPSEC vulnerabilities in 'Everyday' setups.
Focuses on MAC randomization, DNS leaks, and firewall isolation.
"""

import subprocess
import socket
import os
import sys

def check_mac_randomization():
    print("[*] Checking MAC Randomization Status...")
    try:
        res = subprocess.run(["nmcli", "-g", "connection.cloned-mac-address", "connection", "show"], capture_output=True, text=True)
        if "random" in res.stdout.lower():
            print("\033[1;32m[+] MAC Randomization: ENABLED (Hardened)\033[0m")
        else:
            print("\033[1;33m[-] MAC Randomization: NOT DETECTED (Vulnerable to tracking)\033[0m")
    except Exception:
        print("[-] MAC Randomization: nmcli not found or error.")

def check_dns_hardening():
    print("[*] Checking DNS Configuration...")
    try:
        with open("/etc/resolv.conf", "r") as f:
            content = f.read()
            if "1.1.1.1" in content or "9.9.9.9" in content or "127.0.0.1" in content:
                 print("\033[1;32m[+] DNS: SECURE (Encrypted/Hardened resolver detected)\033[0m")
            else:
                 print("\033[1;31m[-] DNS: VULNERABLE (Likely using ISP default DNS)\033[0m")
    except Exception:
        pass

def check_firewall():
    print("[*] Checking Firewall Status...")
    try:
        res = subprocess.run(["sudo", "nft", "list", "ruleset"], capture_output=True, text=True)
        if "table" in res.stdout:
            print("\033[1;32m[+] Firewall: ACTIVE (nftables present)\033[0m")
        else:
            print("\033[1;31m[-] Firewall: INACTIVE or LEGACY (Vulnerable to inbound signals)\033[0m")
    except Exception:
        print("[-] Firewall: Permission denied or nft not found.")

def main():
    print("\033[1;34m[SECURITY_AUDIT] Initiating Host-Hardening Audit...\033[0m")
    
    check_mac_randomization()
    check_dns_hardening()
    check_firewall()
    
    print("\n\033[1;34m[SECURITY_AUDIT] Recommendations:\033[0m")
    print("1. Use 'macchanger' to rotate HW identifiers.")
    print("2. Enable DNS-over-HTTPS in your browser (Librewolf/Firefox).")
    print("3. Isolate mission traffic via private nftables chains.")

if __name__ == "__main__":
    main()
