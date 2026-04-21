#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // DYNAMIC DNS CONFIGURATION UTILITY
# ==============================================================================
# Automates the Dynamic DNS update sequence for Namecheap domains.
# Ensures the specified domain records point to the current public IP address.

import requests
import sys
import os
import time
import logging
from typing import Optional

# Enterprise Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

DOMAIN = "shadowcypher.site"
HOSTS = ["@", "www", "nexus", "api"]
PASSWORD = os.environ.get("NAMECHEAP_DDNS_PASS", "YOUR_NAMECHEAP_DDNS_PASSWORD")

def get_public_ip() -> Optional[str]:
    """Retrieves the current public IP using standard resolution endpoints."""
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
    """Executes the Namecheap Dynamic DNS update."""
    url = "https://dynamicdns.parkengine.com/update"
    params = {
        "host": host,
        "domain": domain,
        "password": password,
        "ip": ip
    }
    
    try:
        logging.info(f"Synchronizing record: {host}.{domain} -> {ip}")
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            if "<ErrCount>0</ErrCount>" in response.text:
                logging.info(f"Success: {host}.{domain} updated.")
            else:
                logging.error(f"Namecheap API Error for {host}. Details: {response.text}")
        else:
            logging.error(f"HTTP {response.status_code} received during update for {host}.")
    except Exception as e:
        logging.error(f"Network error during synchronization: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
         PASSWORD = sys.argv[1]

    print("\n==============================================================================")
    print(" SHADOWCYPHER // DYNAMIC DNS CONFIGURATION UTILITY")
    print("==============================================================================\n")

    if PASSWORD == "YOUR_NAMECHEAP_DDNS_PASSWORD":
        logging.warning("No DDNS password provided. Export NAMECHEAP_DDNS_PASS or pass as argument.")
        sys.exit(1)

    logging.info("Initiating DNS synchronization sequence...")
    
    current_ip = get_public_ip()
    if not current_ip:
        logging.error("Failed to resolve public IP address. Aborting.")
        sys.exit(1)
        
    for h in HOSTS:
        update_dns(h, DOMAIN, PASSWORD, current_ip)
        time.sleep(1) # Rate-limit protection

    print("\n==============================================================================")
    print(" [SUCCESS] DNS SYNCHRONIZATION COMPLETE")
    print("==============================================================================\n")
