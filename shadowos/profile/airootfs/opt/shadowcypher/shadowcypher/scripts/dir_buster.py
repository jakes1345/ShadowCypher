#!/usr/bin/env python3
"""
SHADOWCYPHER // DIR BUSTER — Async Web Directory & File Fuzzer
Pure Python, no gobuster dependency. Fuzzes web paths at high speed.

Usage:
    python3 dir_buster.py <url> [-w WORDLIST] [-t THREADS] [-x EXTENSIONS]
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","M":"\033[1;35m","N":"\033[0m","B":"\033[1m"}

STATUS_COLORS = {200:C["G"], 301:C["Y"], 302:C["Y"], 303:C["Y"], 401:C["M"], 403:C["R"], 500:C["R"]}

BUILTIN_WORDLIST = [
    "admin","administrator","login","wp-admin","wp-login.php","dashboard",
    "panel","cpanel","phpmyadmin","adminer","config","configuration",
    "setup","install","backup","backups","bak","old","temp","tmp",
    "test","testing","debug","dev","development","staging","api","api/v1",
    "api/v2","rest","graphql","swagger","docs","doc","documentation",
    "help","readme","changelog","license","robots.txt","sitemap.xml",
    ".env",".git",".git/HEAD",".git/config",".gitignore",".htaccess",
    ".htpasswd","web.config","server-status","server-info","info.php",
    "phpinfo.php","wp-config.php","wp-config.php.bak","xmlrpc.php",
    "wp-content","wp-includes","wp-json","feed","rss",
    "uploads","upload","images","img","static","assets","media","files",
    "css","js","javascript","fonts","vendor","node_modules",
    "cgi-bin","bin","scripts","shell","cmd","command","exec","run",
    "console","terminal","ssh","ftp","sftp","webdav",
    "database","db","sql","mysql","postgres","redis","mongo","elastic",
    "kibana","grafana","prometheus","jenkins","travis","gitlab",
    "register","signup","sign-up","forgot","reset","password","auth",
    "oauth","token","session","logout","signout","profile","account",
    "user","users","member","members","customer","customers",
    "search","query","find","lookup","download","export","import",
    "manage","management","monitor","monitoring","health","healthcheck",
    "status","ping","version","info","about","contact",
    "blog","news","posts","articles","pages","categories","tags",
    "shop","store","cart","checkout","payment","order","orders",
    "invoice","billing","subscription","pricing","plans",
    "email","mail","newsletter","subscribe","unsubscribe",
    "error","404","500","403","401",
    ".DS_Store","thumbs.db","desktop.ini","crossdomain.xml",
    "favicon.ico","manifest.json","service-worker.js","sw.js",
]

INTERESTING = {200, 201, 204, 301, 302, 303, 307, 308, 401, 403, 405, 500}

def probe_path(base_url, path, user_agent):
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        req = Request(url, headers={"User-Agent": user_agent}, method="GET")
        with urlopen(req, timeout=5) as resp:  # nosec B310
            status = resp.getcode()
            length = len(resp.read())
            return path, status, length
    except HTTPError as e:
        if e.code in INTERESTING:
            return path, e.code, 0
        return None
    except (URLError, Exception):
        return None

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Dir Buster")
    p.add_argument("url", help="Target URL (e.g., http://target.com)")
    p.add_argument("-w","--wordlist", help="Wordlist file")
    p.add_argument("-t","--threads", type=int, default=30)
    p.add_argument("-x","--extensions", default="", help="Extensions to append (e.g., php,html,txt)")
    p.add_argument("--ua", default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    p.add_argument("-o","--output", help="Output file")
    p.add_argument("--hide", default="404", help="Status codes to hide (comma-sep)")
    a = p.parse_args()

    hide_codes = set(int(c) for c in a.hide.split(",") if c.strip())
    extensions = [e.strip() for e in a.extensions.split(",") if e.strip()]

    words = BUILTIN_WORDLIST
    if a.wordlist:
        try:
            with open(a.wordlist) as f:
                words = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        except FileNotFoundError:
            print(f"{C['R']}[WARN]{C['N']} Wordlist not found, using built-in")

    # Build path list with extensions
    paths = list(words)
    for word in words:
        for ext in extensions:
            paths.append(f"{word}.{ext}")

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // DIR BUSTER{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Target:  {C['Y']}{a.url}{C['N']}")
    print(f"  Paths:   {len(paths)}")
    print(f"  Threads: {a.threads}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    results = []
    t0 = time.time()
    done = 0

    with ThreadPoolExecutor(max_workers=a.threads) as pool:
        futures = {pool.submit(probe_path, a.url, path, a.ua): path for path in paths}
        for future in futures:
            try:
                result = future.result(timeout=10)
                done += 1
                if result:
                    path, status, length = result
                    if status not in hide_codes:
                        color = STATUS_COLORS.get(status, C["N"])
                        print(f"  {color}[{status}]{C['N']} /{path:<45} {C['Y']}{length:>8} bytes{C['N']}")
                        results.append((path, status, length))
                # Progress
                if done % 50 == 0:
                    sys.stdout.write(f"\r  Progress: {done}/{len(paths)}")
                    sys.stdout.flush()
            except Exception:
                done += 1

    elapsed = time.time() - t0
    print(f"\n\n{C['B']}{'='*70}{C['N']}")
    print(f"  {C['G']}Scan complete:{C['N']} {len(results)} interesting paths in {elapsed:.1f}s")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    if a.output and results:
        with open(a.output, "w") as f:
            f.write(f"# Dir Buster Results — {a.url}\n")
            for path, status, length in sorted(results):
                f.write(f"[{status}] /{path}  ({length} bytes)\n")
        print(f"  Saved to: {a.output}\n")

if __name__ == "__main__":
    main()
