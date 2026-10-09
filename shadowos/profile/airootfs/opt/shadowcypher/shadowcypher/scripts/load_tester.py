#!/usr/bin/env python3
# ==============================================================================
# SHADOWCYPHER // NETWORK BENCHMARK UTILITY
# ==============================================================================
# Professional CLI utility for measuring network latency and throughput capacity
# against specified endpoints.

import argparse
import logging
import socket
import statistics
import sys
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

def tcp_latency_test(target, port, iterations=10):
    logging.info(f"Initiating TCP latency benchmark against {target}:{port}")
    latencies = []

    for i in range(iterations):
        try:
            start_time = time.time()
            with socket.create_connection((target, port), timeout=2.0):
                end_time = time.time()
                rtt = (end_time - start_time) * 1000
                latencies.append(rtt)
                sys.stdout.write(f"\r  -> Probe {i+1}/{iterations} | RTT: {rtt:.2f} ms")
                sys.stdout.flush()
            time.sleep(0.1)
        except Exception as e:
            sys.stdout.write(f"\r  -> Probe {i+1}/{iterations} | FAILED ({e})")
            sys.stdout.flush()

    print()
    if latencies:
        avg = statistics.mean(latencies)
        logging.info(f"Benchmark Complete | Avg: {avg:.2f}ms | Max: {max(latencies):.2f}ms")
    else:
        logging.error("Benchmark failed: Target unreachable.")

def main():
    parser = argparse.ArgumentParser(description="ShadowCypher Network Benchmark Utility")
    parser.add_argument("target", help="Target IP or Hostname")
    parser.add_argument("-p", "--port", type=int, default=80, help="Target Port (default: 80)")
    parser.add_argument("-c", "--count", type=int, default=20, help="Number of probes (default: 20)")

    args = parser.parse_args()

    print("\n==============================================================================")
    print(" SHADOWCYPHER // NETWORK BENCHMARK")
    print("==============================================================================\n")

    tcp_latency_test(args.target, args.port, iterations=args.count)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        logging.warning("Benchmark interrupted by user.")
        sys.exit(0)
