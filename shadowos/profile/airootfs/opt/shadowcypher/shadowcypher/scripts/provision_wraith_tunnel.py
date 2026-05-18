#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // SECURE VPN PROVISIONING SERVICE
# ==============================================================================
# Deploys a WireGuard relay server and generates client configurations 
# and QR codes for remote field units.

import sys
import os
import logging

# 1. Environment Sync
sys.path.insert(0, os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

from shadowcypher.modules.sovereign_relay import sovereign_relay

# Enterprise Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | VPN_Provisioning | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("VPN_Provisioning")

def main():
    print("\n==============================================================================")
    print(" SHADOWCYPHER // SECURE VPN PROVISIONING SERVICE")
    print("==============================================================================\n")

    # Step 1: Deploy Server
    log.info("Deploying WireGuard Infrastructure (Port 51820)...")
    server_conf = sovereign_relay.deploy_server(port=51820)
    if not server_conf:
        log.error("Failed to generate server configuration.")
        return
    log.info("WireGuard server configuration generated successfully.")

    # Step 2: Provision Remote Units
    field_units = [
        {"name": "S23_ULTRA", "ip": "10.0.0.2"},
        {"name": "S7_TABLET", "ip": "10.0.0.3"}
    ]

    for unit in field_units:
        log.info(f"Provisioning client access: {unit['name']} ({unit['ip']})")
        conf_path = sovereign_relay.add_client(unit['name'], unit['ip'])
        if conf_path:
            log.info(f"Client configuration generated: {conf_path}")
            qr_path = sovereign_relay.generate_qr(conf_path)
            if qr_path:
                log.info(f"Client QR code generated: {qr_path}")
            else:
                log.warning("Could not generate QR code (qrencode utility missing).")
        else:
            log.error(f"Failed to provision client {unit['name']}")

    print("\n==============================================================================")
    print(" [SUCCESS] INFRASTRUCTURE PROVISIONING COMPLETE")
    print("==============================================================================")
    print("  -> Configuration files reside in: configs/wraith_tunnel/")
    print("  -> To activate the host tunnel interface, execute:")
    print("     sudo cp configs/wraith_tunnel/wg0.conf /etc/wireguard/ && sudo wg-quick up wg0\n")

if __name__ == "__main__":
    main()
