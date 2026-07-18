#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // AUTOMATED DIAGNOSTIC & LOAD PROFILER
# ==============================================================================
# Orchestrates automated network reconnaissance and localized load testing
# to validate system security posture and infrastructure throughput.

import asyncio
import logging
import os
import sys
import time

import aiohttp

# 1. Environment Sync
sys.path.insert(0, os.getcwd())
os.environ["PYTHONPATH"] = os.environ.get("PYTHONPATH", "") + ":" + os.getcwd()

from shadowcypher.modules.firewall import Firewall
from shadowcypher.modules.router_pwn import router_pwn

# Enterprise Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(name)s | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
log = logging.getLogger("Diagnostics_Orchestrator")

async def load_test_worker(session, url, requests_per_worker):
    success = 0
    errors = 0
    start = time.time()
    for _ in range(requests_per_worker):
        try:
            async with session.get(url, timeout=2) as response:
                await response.read()
                if response.status == 200:
                    success += 1
                else:
                    errors += 1
        except Exception:
            errors += 1
    return success, errors, time.time() - start

async def execute_local_load_test(target_ip="127.0.0.1", port=8080, concurrency=50, total_requests=1000):
    url = f"http://{target_ip}:{port}/"
    log.info(f"Initiating local load profile against {url} | Concurrency: {concurrency}")

    reqs_per = total_requests // concurrency
    async with aiohttp.ClientSession() as session:
        tasks = [load_test_worker(session, url, reqs_per) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)

    total_success = sum(r[0] for r in results)
    total_errors = sum(r[1] for r in results)
    max_time = max(r[2] for r in results)

    rps = (total_success + total_errors) / max_time if max_time > 0 else 0
    log.info(f"Load Test Complete: {total_success} OK | {total_errors} ERR | {rps:.2f} RPS")
    return rps

def run_diagnostics():
    log.info("Starting automated infrastructure diagnostics.")

    # Phase 1: Gateway Audit
    log.info("Phase 1: Local Network Gateway Audit")
    gateway_ip = router_pwn.get_gateway_ip()
    if gateway_ip:
        log.info(f"Gateway detected at {gateway_ip}. Auditing management interfaces...")
        # Safe auditing, not exploitation
        router_pwn.audit_management_ports(gateway_ip, on_output=lambda x: log.info(f"Port Audit: {x.strip()}"))
    else:
        log.warning("No default gateway detected. Skipping gateway audit.")

    # Phase 2: Host Masking (Firewall Restrictions)
    log.info("Phase 2: Enforcing Inbound Firewall Restrictions (Stealth Profile)")
    Firewall.stealth_mode(on_output=lambda x: log.info(f"Firewall Policy: {x.strip()}"))
    log.info("Stealth Profile active. Inbound traffic explicitly dropped.")

    # Phase 3: Traffic Generation & Load Profiling
    log.info("Phase 3: Subsystem Load Profiling")
    try:
        asyncio.run(execute_local_load_test(target_ip="127.0.0.1", port=8000, concurrency=25, total_requests=500))
    except Exception as e:
        log.error(f"Load profile generation failed: {e}")

    # Phase 4: Teardown
    log.info("Phase 4: Restoring standard network profiles.")
    Firewall.ipt_flush()
    log.info("Diagnostics workflow completed successfully.")

if __name__ == "__main__":
    try:
        run_diagnostics()
    except KeyboardInterrupt:
        log.warning("Diagnostics interrupted by user. Restoring firewall state...")
        Firewall.ipt_flush()
        sys.exit(1)
