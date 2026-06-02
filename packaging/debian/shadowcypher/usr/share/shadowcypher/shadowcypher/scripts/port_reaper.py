#!/usr/bin/env python3
"""
SHADOWCYPHER // PORT REAPER — Async TCP Port Scanner
Pure Python, no nmap dependency. Scans thousands of ports per second
using asyncio connection probes with banner grabbing.

Usage:
    python3 port_reaper.py <target> [-p PORTS] [-t THREADS] [--banners]

Examples:
    python3 port_reaper.py 192.168.1.1
    python3 port_reaper.py 10.0.0.1 -p 1-65535 -t 2000
    python3 port_reaper.py scanme.nmap.org -p 22,80,443,8080 --banners
"""

import asyncio
import argparse
import socket
import sys
import time
from collections import defaultdict

# Well-known service names for common ports
SERVICE_MAP = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCBind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1433: "MSSQL", 1521: "Oracle", 2049: "NFS", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
    8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 8888: "HTTP-Alt",
    27017: "MongoDB", 5353: "mDNS", 7547: "TR-069", 9200: "Elasticsearch",
    11211: "Memcached", 6667: "IRC", 1080: "SOCKS",
}

# ANSI color codes
RED = "\033[1;31m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
MAGENTA = "\033[1;35m"
NC = "\033[0m"
BOLD = "\033[1m"


def parse_ports(port_str: str) -> list[int]:
    """Parse port specification like '22,80,443' or '1-1024' or 'top100'."""
    TOP_100 = [
        21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1433,1521,
        1723,2049,2121,3306,3389,5432,5900,5985,6379,8080,8443,8888,
        9090,9200,9300,27017,11211,6667,1080,8000,8081,8888,4443,
        7547,161,162,389,636,88,464,543,544,749,2222,10000,5000,
        5001,5601,9090,9100,4444,6660,6661,6662,6663,6664,6665,
        6666,6668,6669,7000,7001,7002,8001,8002,8008,8009,8010,
        8020,8030,8040,8050,8060,8070,8090,8100,8180,8181,8200,
        8300,8400,8500,8600,8700,8800,8900,9000,9001,9002,9003,
        9080,9443,10001,10002,10003,10080,10443,49152,49153,49154,
    ]

    if port_str.lower() == "top100":
        return sorted(set(TOP_100))

    ports = set()
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.update(range(int(start), int(end) + 1))
        else:
            ports.add(int(part))
    return sorted(ports)


async def grab_banner(host: str, port: int, timeout: float = 2.0) -> str:
    """Attempt to grab a service banner from an open port."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        # Some services send banners immediately, others need a probe
        try:
            banner = await asyncio.wait_for(reader.read(1024), timeout=1.5)
        except asyncio.TimeoutError:
            # Send a generic probe for services that wait for client input
            writer.write(b"HEAD / HTTP/1.0\r\n\r\n")
            await writer.drain()
            try:
                banner = await asyncio.wait_for(reader.read(1024), timeout=1.5)
            except asyncio.TimeoutError:
                banner = b""
        writer.close()
        await writer.wait_closed()
        return banner.decode("utf-8", errors="replace").strip().split("\n")[0][:80]
    except Exception:
        return ""


async def scan_port(sem: asyncio.Semaphore, host: str, port: int,
                    timeout: float, grab: bool, results: dict):
    """Probe a single TCP port."""
    async with sem:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()

            service = SERVICE_MAP.get(port, "unknown")
            banner = ""
            if grab:
                banner = await grab_banner(host, port, timeout)

            results[port] = {"service": service, "banner": banner}
            status = f"{GREEN}OPEN{NC}"
            line = f"  {status}  {CYAN}{port:>5}/tcp{NC}  {YELLOW}{service:<16}{NC}"
            if banner:
                line += f"  {MAGENTA}{banner}{NC}"
            print(line)

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            pass


async def run_scan(host: str, ports: list[int], concurrency: int,
                   timeout: float, grab_banners: bool) -> dict:
    """Execute the full port scan."""
    results = {}
    sem = asyncio.Semaphore(concurrency)

    tasks = [
        scan_port(sem, host, port, timeout, grab_banners, results)
        for port in ports
    ]
    await asyncio.gather(*tasks)
    return results


def resolve_host(target: str) -> str:
    """Resolve hostname to IP, return original if already an IP."""
    try:
        socket.inet_aton(target)
        return target
    except socket.error:
        try:
            ip = socket.gethostbyname(target)
            return ip
        except socket.gaierror:
            print(f"{RED}[ERROR]{NC} Cannot resolve hostname: {target}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ShadowCypher Port Reaper — Async TCP Scanner"
    )
    parser.add_argument("target", help="Target IP or hostname")
    parser.add_argument("-p", "--ports", default="1-1024",
                        help="Port spec: '22,80,443' or '1-65535' or 'top100' (default: 1-1024)")
    parser.add_argument("-t", "--threads", type=int, default=500,
                        help="Concurrent connections (default: 500)")
    parser.add_argument("--timeout", type=float, default=1.0,
                        help="Connection timeout in seconds (default: 1.0)")
    parser.add_argument("--banners", action="store_true",
                        help="Grab service banners from open ports")
    parser.add_argument("-o", "--output", help="Save results to file")

    args = parser.parse_args()
    ports = parse_ports(args.ports)
    ip = resolve_host(args.target)

    print(f"\n{BOLD}{'='*70}{NC}")
    print(f" {CYAN}SHADOWCYPHER // PORT REAPER{NC}")
    print(f"{BOLD}{'='*70}{NC}")
    print(f"  Target:      {YELLOW}{args.target}{NC} ({ip})")
    print(f"  Ports:       {len(ports)} ports")
    print(f"  Concurrency: {args.threads}")
    print(f"  Banners:     {'ON' if args.banners else 'OFF'}")
    print(f"{BOLD}{'='*70}{NC}\n")

    start = time.time()
    results = asyncio.run(
        run_scan(ip, ports, args.threads, args.timeout, args.banners)
    )
    elapsed = time.time() - start

    print(f"\n{BOLD}{'='*70}{NC}")
    print(f"  {GREEN}Scan complete:{NC} {len(results)} open ports found "
          f"in {elapsed:.2f}s ({len(ports)/elapsed:.0f} ports/sec)")
    print(f"{BOLD}{'='*70}{NC}\n")

    if args.output and results:
        with open(args.output, "w") as f:
            f.write(f"# Port Reaper Results — {args.target} ({ip})\n")
            f.write(f"# Scanned {len(ports)} ports in {elapsed:.2f}s\n\n")
            for port in sorted(results.keys()):
                r = results[port]
                line = f"{port}/tcp  OPEN  {r['service']}"
                if r["banner"]:
                    line += f"  | {r['banner']}"
                f.write(line + "\n")
        print(f"  Results saved to: {args.output}\n")


if __name__ == "__main__":
    main()
