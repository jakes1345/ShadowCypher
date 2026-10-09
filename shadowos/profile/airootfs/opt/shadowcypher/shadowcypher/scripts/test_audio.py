#!/usr/bin/env python3
import os
import sys
import time

# 1. Environment Sync
sys.path.insert(0, os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

from shadowcypher.core.logger import logger


def test_sounds():
    print("[*] Testing 8-bit signal alerts...")

    logger.info("hub", "RELAY_BRIDGE: Secure signal link established.")
    time.sleep(1)

    logger.info("mission", "WEAPON_SYNTHESIS: Success.")
    time.sleep(1)

    logger.error("firewall", "PACKET_DROP_FAILURE: Critical overflow.")
    time.sleep(1)

    logger.info("swarm", "SHADOW_SWARM_HUB_TERMINATED")
    print("[+] Test complete.")

if __name__ == "__main__":
    test_sounds()
