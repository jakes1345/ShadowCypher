#!/usr/bin/env python3
"""
SHADOWCYPHER // SUBDOMAIN RECON — Multi-Source Subdomain Enumerator
Combines DNS brute-force, crt.sh CT logs, and HackerTarget API.

Usage:
    python3 subdomain_recon.py <domain> [-w WORDLIST] [-t THREADS] [--resolve]
"""

import argparse
import socket
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen, Request

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","M":"\033[1;35m","N":"\033[0m","B":"\033[1m"}

BUILTIN_WORDS = [
    "www","mail","ftp","webmail","smtp","pop","ns1","ns2","ns3","ns4","dns",
    "mx","mx1","api","dev","staging","stage","test","beta","demo","app",
    "admin","portal","vpn","remote","secure","login","sso","auth","gateway",
    "proxy","cdn","static","assets","media","img","images","upload","files",
    "docs","wiki","help","support","status","monitor","git","gitlab","jenkins",
    "ci","build","deploy","registry","docker","grafana","prometheus","kibana",
    "elastic","redis","mongo","mysql","db","postgres","ldap","exchange","owa",
    "autodiscover","jira","confluence","vault","consul","backup","old","new",
    "v1","v2","api-v1","api-v2","internal","intranet","corp","store","shop",
    "blog","news","forum","mobile","m","cms","crm","erp","cloud","sandbox",
    "uat","qa","preprod","prod","live","panel","cpanel","whm","webmin",
]

def query_crtsh(domain):
    subs = set()
    try:
        req = Request(f"https://crt.sh/?q=%25.{domain}&output=json", headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:  # nosec B310
            for e in json.loads(resp.read().decode()):
                for line in e.get("name_value","").split("\n"):
                    line = line.strip().lower().lstrip("*.")
                    if line.endswith(f".{domain}"):
                        subs.add(line)
    except Exception:
        pass
    return subs

def query_hackertarget(domain):
    subs = set()
    try:
        req = Request(f"https://api.hackertarget.com/hostsearch/?q={domain}", headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:  # nosec B310
            for line in resp.read().decode().strip().split("\n"):
                parts = line.split(",")
                if parts and parts[0].endswith(f".{domain}"):
                    subs.add(parts[0].strip().lower())
    except Exception:
        pass
    return subs

def dns_resolve(sub):
    try:
        return sub, socket.gethostbyname(sub)
    except socket.gaierror:
        return sub, None

def dns_bruteforce(domain, wordlist, threads=50):
    found = set()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        for sub, ip in pool.map(dns_resolve, [f"{w}.{domain}" for w in wordlist]):
            if ip:
                found.add(sub)
    return found

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Subdomain Recon")
    p.add_argument("domain", help="Target domain")
    p.add_argument("-w","--wordlist", help="Wordlist file path")
    p.add_argument("-t","--threads", type=int, default=50)
    p.add_argument("--resolve", action="store_true", help="Resolve all to IPs")
    p.add_argument("--no-passive", action="store_true")
    p.add_argument("-o","--output", help="Output file")
    a = p.parse_args()
    domain = a.domain.lower().strip()

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // SUBDOMAIN RECON{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Target: {C['Y']}{domain}{C['N']}\n")

    all_subs = set()
    t0 = time.time()

    if not a.no_passive:
        print(f"  {C['C']}[1]{C['N']} crt.sh CT logs...")
        ct = query_crtsh(domain)
        all_subs.update(ct)
        print(f"    {C['G']}→{C['N']} {len(ct)} subdomains")

        print(f"  {C['C']}[2]{C['N']} HackerTarget API...")
        ht = query_hackertarget(domain)
        all_subs.update(ht)
        print(f"    {C['G']}→{C['N']} {len(ht)} subdomains")

    words = BUILTIN_WORDS
    if a.wordlist:
        try:
            with open(a.wordlist) as f:
                words = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        except FileNotFoundError:
            print(f"  {C['R']}[WARN]{C['N']} Wordlist not found, using built-in")
    print(f"  {C['C']}[3]{C['N']} DNS brute-force ({len(words)} words)...")
    bf = dns_bruteforce(domain, words, a.threads)
    all_subs.update(bf)
    print(f"    {C['G']}→{C['N']} {len(bf)} subdomains")

    elapsed = time.time() - t0
    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['G']}FOUND: {len(all_subs)} subdomains{C['N']} ({elapsed:.1f}s)\n")

    if a.resolve and all_subs:
        with ThreadPoolExecutor(max_workers=a.threads) as pool:
            for sub, ip in sorted(pool.map(dns_resolve, sorted(all_subs))):
                if ip:
                    print(f"  {C['G']}●{C['N']} {sub:<50} {C['Y']}{ip}{C['N']}")
                else:
                    print(f"  {C['R']}✗{C['N']} {sub}")
    else:
        for s in sorted(all_subs):
            print(f"  {C['G']}●{C['N']} {s}")

    if a.output and all_subs:
        with open(a.output,"w") as f:
            for s in sorted(all_subs):
                f.write(s+"\n")
        print(f"\n  Saved to: {a.output}")
    print()

if __name__ == "__main__":
    main()
