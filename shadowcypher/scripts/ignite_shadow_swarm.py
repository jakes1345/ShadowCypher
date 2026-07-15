#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // RELAY NODE PROVISIONING SERVICE
# ==============================================================================
# Initializes the encrypted UDP relay hub and provisions connection identities
# for authorized external client devices.

import logging
import os
import sys
import time

# 1. Environment Sync
sys.path.insert(0, os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

from shadowcypher.modules.shadow_swarm import shadow_swarm

# Enterprise Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | ProvisioningService | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
log = logging.getLogger("Relay_Provisioning")

def main():
    print("\n==============================================================================")
    print(" SHADOWCYPHER // RELAY NODE PROVISIONING SERVICE")
    print("==============================================================================\n")

    log.info("Starting Encrypted UDP Hub Interface...")
    try:
        shadow_swarm.start_hub()
    except Exception as e:
        log.error(f"Failed to bind UDP Hub interface: {e}")
        sys.exit(1)

    log.info("UDP Hub interface bound successfully.")

    # Client Provisioning
    authorized_clients = ["S23_ULTRA", "S7_TABLET"]
    for client_id in authorized_clients:
        log.info(f"Provisioning identity for client: {client_id}")
        try:
            prov_file = shadow_swarm.get_mobile_provision(client_id)
            log.info(f"Identity generated successfully. Path: {prov_file}")
        except Exception as e:
            log.error(f"Failed to provision identity for {client_id}: {e}")

    print("\n==============================================================================")
    print(" [SUCCESS] PROVISIONING SERVICE ACTIVE")
    print("==============================================================================")
    print("  -> Service is currently listening for encrypted UDP payloads.")
    print("  -> Client connections do not establish standard VPN tunnels.")
    print("  -> All traffic is encapsulated within randomized UDP datagrams.")
    print("  -> Press Ctrl+C to gracefully terminate the hub service.\n")

    # Keep alive loop
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Termination signal received. Shutting down Hub Interface...")
        shadow_swarm.stop_hub()
        log.info("Hub Service terminated cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
