#!/usr/bin/env python3
"""
ShadowCypher Namecheap Apex Sync — Sovereign DNS Orchestration.
Automates the Dynamic DNS update for shadowcypher.site.
"""

import requests
import sys
import os
import time
from typing import Optional

DOMAIN = "shadowcypher.site"
HOSTS = ["@", "www", "nexus", "api"]
PASSWORD = "9c7b940d90c745858a566ce9f3c8cffb"

def get_public_ip() -> Optional[str]:
    """Retrieves the current public IP via multiple spectral hubs."""
    endpoints = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]
    for url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.text.strip()
        except:
            continue
    return None

def update_dns(host: str, domain: str, password: str, ip: str):
    """Executes the Namecheap Dynamic DNS handshake."""
    url = "https://dynamicdns.parkengine.com/update"
    params = {
        "host": host,
        "domain": domain,
        "password": password,
        "ip": ip
    }
    
    try:
        print(f"[\033[0;34mSYNC\033[0m] Sending signal for {host}.{domain} -> {ip}...")
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            if "<ErrCount>0</ErrCount>" in response.text:
                print(f"[\033[0;32mSUCCESS\033[0m] {host}.{domain} updated successfully.")
            else:
                print(f"[\033[0;31mERROR\033[0m] Namecheap API returned internal error for {host}.")
        else:
            print(f"[\033[0;31mFAIL\033[0m] HTTP {response.status_code} on update attempt.")
    except Exception as e:
        print(f"[\033[0;31mFAIL\033[0m] Synchronisation heartbeat failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
         PASSWORD = sys.argv[1]

    if PASSWORD == "YOUR_DDNS_PASSWORD":
        print("[\033[0;33mWARN\033[0m] No DDNS password provided. Set NAMECHEAP_DDNS_PASS env or pass as arg.")
        sys.exit(1)

    print("\033[0;36mSHADOWCYPHER_DNS_SYNC: INITIATING_HANDSHAKE...\033[0m")
    
    current_ip = get_public_ip()
    if not current_ip:
        print("[\033[0;31mFATAL\033[0m] Could not resolve public IP. Signal lost.")
        sys.exit(1)
        
    for h in HOSTS:
        update_dns(h, DOMAIN, PASSWORD, current_ip)
        time.sleep(1) # Rate-limit protection

    print("\033[0;32mORCHESTRATION_COMPLETE: Domain shadowcypher.site is live on spectrum.\033[0m")
