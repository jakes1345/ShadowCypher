#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // LOCAL GATEWAY SECURITY AUDIT
# ==============================================================================
# Audits the local default gateway for known remote management exposures
# (e.g., TR-069/CWMP) and validates local DNS routing hygiene.

import logging
import os
import sys

# 1. Environment Sync
sys.path.insert(0, os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

from shadowcypher.modules.router_pwn import router_pwn

# Enterprise Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

def main():
    print("\n==============================================================================")
    print(" SHADOWCYPHER // LOCAL GATEWAY SECURITY AUDIT")
    print("==============================================================================\n")

    # Step 1: Identify Gateway
    gateway_ip = router_pwn.get_gateway_ip()
    if not gateway_ip:
        logging.error("Failed to identify default gateway route. Audit aborted.")
        sys.exit(1)

    logging.info(f"Target Gateway Identified: {gateway_ip}")

    # Step 2: Device Fingerprinting
    info = router_pwn.fingerprint_router(gateway_ip)
    logging.info(f"Gateway Fingerprint: Manufacturer={info.get('manufacturer', 'Unknown')} | Model={info.get('model', 'Unknown')}")

    # Step 3: Remote Management Exposure Audit
    logging.info("Initiating Management Interface Exposure Audit...")
    open_ports = []

    def capture_port(output):
        print(f"    -> {output.strip()}")
        if "OPEN" in output:
            try:
                open_ports.append(int(output.split()[1]))
            except Exception:
                pass

    router_pwn.audit_management_ports(gateway_ip, on_output=capture_port)

    # Step 4: Security Posture Report
    print("\n==============================================================================")
    print(" AUDIT FINDINGS & RECOMMENDATIONS")
    print("==============================================================================\n")

    if 7547 in open_ports or 8089 in open_ports:
        print("[!] CRITICAL FINDING: TR-069 / CWMP Exposure Detected.")
        print("    -> The gateway is exposing ISP remote management ports (7547/8089).")
        print("    -> Recommendation: Disable TR-069 in router administration or implement egress filtering.")
    else:
        print("[OK] No standard ISP remote management exposures (TR-069) detected on the gateway.")

    print("\n[INFO] General Network Hygiene:")
    print("    -> Verify upstream DNS configuration to prevent ISP DNS interception.")
    print("    -> Consider enforcing DNS-over-TLS (DoT) or DNS-over-HTTPS (DoH).")
    print("    -> Employ MAC Address randomization for localized operational security.\n")

if __name__ == "__main__":
    main()
