"""
Real security tool functions for AgentLoop.
Each function shells out to an actual binary or makes a real network call.
Tools that send active traffic to the target are marked requires_approval=True.
"""

import json
import shutil
import socket
import subprocess
import urllib.request
from typing import Optional
from urllib.parse import urlparse

from shadowcypher.ai.tool_loop import AgentTool
from shadowcypher.core.stealth import stealth

# ── Helpers ───────────────────────────────────────────────────────────────────

def _tor_proxy() -> Optional[tuple]:
    """Return (host, port) of the active SOCKS5 proxy, or None if stealth is off."""
    if not stealth.active:
        return None
    proxy_url = stealth.proxy_url or "socks5h://127.0.0.1:9050"
    try:
        p = urlparse(proxy_url)
        return (p.hostname or "127.0.0.1", p.port or 9050)
    except Exception:
        return ("127.0.0.1", 9050)


def _proxy_socket() -> socket.socket:
    """
    Return a socket routed through the Tor SOCKS5 proxy when stealth is active.
    Falls back to a plain socket when Tor is not running.
    """
    proxy = _tor_proxy()
    if proxy:
        try:
            import socks  # PySocks
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, proxy[0], proxy[1])
            return s
        except ImportError:
            pass  # PySocks not installed — fall through to plain socket
    return socket.socket()


def _run(cmd: list, timeout: int = 90) -> str:
    """Run a command, routing through proxychains/torsocks when Tor is active."""
    binary = cmd[0]
    if not shutil.which(binary):
        return f"NOT_INSTALLED: {binary} — install it first (e.g. apt install {binary})"
    try:
        wrapped = stealth.wrap_command(cmd)
        proc = subprocess.run(wrapped, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout + proc.stderr).strip()
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: {binary} exceeded {timeout}s"
    except Exception as e:
        return f"EXEC_ERROR: {e}"


# ── Tool Functions ────────────────────────────────────────────────────────────

_NMAP_BLOCKED = ("--script", "--script-args", "--script-help", "--proxies", "-iL", "-oX", "-oG", "--datadir")

def run_nmap(target: str,
             flags: str = "-sV --version-light -p 21,22,23,25,53,80,110,443,445,3306,3389,8080,8443") -> str:
    """Port scan with service version detection."""
    for token in flags.split():
        if any(token.startswith(b) for b in _NMAP_BLOCKED):
            return f"BLOCKED: flag {token!r} is not permitted in agentic context"
    return _run(["nmap"] + flags.split() + [target], timeout=120)


def run_nmap_full(target: str) -> str:
    """Full port scan (all 65535 ports, slower)."""
    return _run(["nmap", "-sV", "--version-light", "-p-", "--open", target], timeout=300)


def http_probe(url: str, path: str = "/") -> str:
    """Fetch a URL and return status code, headers, and body preview."""
    try:
        full = f"{url.rstrip('/')}{path}"
        req = urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(1024).decode(errors="replace")
            return json.dumps({
                "url": full,
                "status": resp.status,
                "headers": dict(resp.headers),
                "body_preview": body,
            }, indent=2)
    except urllib.error.HTTPError as e:
        return json.dumps({"url": url + path, "status": e.code, "error": str(e)})
    except Exception as e:
        return f"HTTP_ERROR: {e}"


def dns_lookup(domain: str) -> str:
    """Resolve domain to IPs."""
    try:
        results = socket.getaddrinfo(domain, None)
        ips = sorted({r[4][0] for r in results})
        hostname = socket.getfqdn(domain)
        return json.dumps({"domain": domain, "fqdn": hostname, "ips": ips}, indent=2)
    except Exception as e:
        return f"DNS_ERROR: {e}"


def grab_banner(host: str, port: int) -> str:
    """Connect to host:port and grab the raw service banner."""
    s = _proxy_socket()
    try:
        s.settimeout(5)
        s.connect((host, int(port)))
        s.send(b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n")
        banner = s.recv(2048).decode(errors="replace")
        return banner.strip() or "(connected but no banner received)"
    except Exception as e:
        return f"BANNER_ERROR: {e}"
    finally:
        s.close()


def run_whois(target: str) -> str:
    """WHOIS lookup for domain or IP."""
    return _run(["whois", target], timeout=30)


def search_exploit(service: str, version: str = "") -> str:
    """Search ExploitDB via searchsploit for known exploits."""
    query = f"{service} {version}".strip()
    return _run(["searchsploit", "--json", query], timeout=30)


def run_nuclei(target: str, templates: str = "cves,exposures,misconfiguration") -> str:
    """Run nuclei vulnerability scanner."""
    cmd = ["nuclei", "-u", target, "-t", templates, "-silent", "-nc"]
    return _run(cmd, timeout=180)


def run_nikto(url: str) -> str:
    """Run nikto web vulnerability scanner."""
    return _run(["nikto", "-h", url, "-nointeractive", "-Format", "txt"], timeout=180)


def run_gobuster(url: str,
                 wordlist: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    """Directory/file bruteforce against a web target."""
    return _run(
        ["gobuster", "dir", "-u", url, "-w", wordlist, "-q", "--no-error",
         "-b", "404,403"],
        timeout=120,
    )


def run_ffuf(url: str,
             wordlist: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    """Fast web fuzzer — directory discovery."""
    return _run(
        ["ffuf", "-u", f"{url}/FUZZ", "-w", wordlist,
         "-mc", "200,301,302,403", "-s"],
        timeout=120,
    )


def run_sqlmap(url: str, level: int = 1) -> str:
    """Test a URL for SQL injection (read-only, no exploitation)."""
    return _run(
        ["sqlmap", "-u", url, "--level", str(level),
         "--batch", "--forms", "--crawl=2", "--technique=BT",
         "--output-dir=/tmp/sqlmap_out"],
        timeout=180,
    )


def ssl_check(host: str, port: int = 443) -> str:
    """Check SSL/TLS certificate and configuration."""
    return _run(["sslscan", "--no-colour", f"{host}:{port}"], timeout=30)


def run_theHarvester(domain: str, sources: str = "google,bing,crtsh") -> str:
    """OSINT email/subdomain harvesting."""
    return _run(
        ["theHarvester", "-d", domain, "-b", sources, "-l", "50"],
        timeout=60,
    )


def check_smb(target: str) -> str:
    """Enumerate SMB shares and version."""
    return _run(["smbclient", "-L", f"//{target}/", "-N"], timeout=30)


def check_ftp_anon(host: str) -> str:
    """Check if FTP allows anonymous login."""
    try:
        import ftplib
        proxy = _tor_proxy()
        if proxy:
            # Inject a SOCKS5 socket directly into ftplib so the control
            # connection is routed through Tor without monkey-patching globals.
            sock = _proxy_socket()
            sock.settimeout(5)
            sock.connect((host, 21))
            ftp = ftplib.FTP()
            ftp.sock = sock
            ftp.af = sock.family
            ftp.file = sock.makefile("rb")
            ftp.welcome = ftp.getresp()
        else:
            ftp = ftplib.FTP(timeout=5)
            ftp.connect(host, 21)
        try:
            ftp.login("anonymous", "probe@test.local")
            files = ftp.nlst()
            ftp.quit()
            return f"ANONYMOUS_LOGIN: allowed\nFiles: {files[:20]}"
        except ftplib.error_perm:
            return "ANONYMOUS_LOGIN: denied"
    except Exception as e:
        return f"FTP_ERROR: {e}"


# ── Tool Registry ─────────────────────────────────────────────────────────────

SECURITY_TOOLS = [
    AgentTool(
        name="run_nmap",
        description=(
            "Run an nmap port scan on a target IP or hostname. "
            "Returns open ports, service names, and version strings. "
            "Use this first to discover the attack surface."
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "IP or hostname"},
                "flags": {
                    "type": "string",
                    "description": "nmap flags (default scans common ports with version detection)",
                    "default": "-sV --version-light -p 21,22,23,25,53,80,110,443,445,3306,3389,8080,8443",
                },
            },
            "required": ["target"],
        },
        fn=run_nmap,
        requires_approval=True,
    ),
    AgentTool(
        name="http_probe",
        description=(
            "Probe an HTTP/HTTPS endpoint. Returns status code, response headers, "
            "and body preview. Use to fingerprint web servers and find interesting paths."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Base URL e.g. http://10.0.0.1"},
                "path": {"type": "string", "description": "Path to probe", "default": "/"},
            },
            "required": ["url"],
        },
        fn=http_probe,
        requires_approval=True,
    ),
    AgentTool(
        name="dns_lookup",
        description="Resolve a domain name to IP addresses and get FQDN.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to resolve"},
            },
            "required": ["domain"],
        },
        fn=dns_lookup,
    ),
    AgentTool(
        name="grab_banner",
        description="Connect to a host and port and capture the raw service banner.",
        parameters={
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "description": "Port number"},
            },
            "required": ["host", "port"],
        },
        fn=grab_banner,
        requires_approval=True,
    ),
    AgentTool(
        name="run_whois",
        description="WHOIS lookup for a domain or IP — returns registrar, owner, ASN info.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Domain or IP"},
            },
            "required": ["target"],
        },
        fn=run_whois,
    ),
    AgentTool(
        name="search_exploit",
        description=(
            "Search ExploitDB (searchsploit) for known public exploits for a service and version. "
            "Use after identifying a service version to find CVEs/PoCs."
        ),
        parameters={
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "e.g. 'apache', 'openssh', 'vsftpd'"},
                "version": {"type": "string", "description": "e.g. '2.4.49'", "default": ""},
            },
            "required": ["service"],
        },
        fn=search_exploit,
        requires_approval=True,
    ),
    AgentTool(
        name="ssl_check",
        description="Check SSL/TLS certificate, cipher suites, and common misconfigs.",
        parameters={
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "default": 443},
            },
            "required": ["host"],
        },
        fn=ssl_check,
        requires_approval=True,
    ),
    AgentTool(
        name="check_ftp_anon",
        description="Check if FTP service allows anonymous login and list accessible files.",
        parameters={
            "type": "object",
            "properties": {
                "host": {"type": "string"},
            },
            "required": ["host"],
        },
        fn=check_ftp_anon,
        requires_approval=True,
    ),
    AgentTool(
        name="check_smb",
        description="Enumerate SMB shares on a Windows/Samba host.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string"},
            },
            "required": ["target"],
        },
        fn=check_smb,
        requires_approval=True,
    ),
    AgentTool(
        name="run_nuclei",
        description=(
            "Run nuclei automated vulnerability scanner. Checks for CVEs, "
            "misconfigurations, and exposures. Use after initial recon."
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target URL"},
                "templates": {
                    "type": "string",
                    "description": "Template categories",
                    "default": "cves,exposures,misconfiguration",
                },
            },
            "required": ["target"],
        },
        fn=run_nuclei,
        requires_approval=True,
    ),
    AgentTool(
        name="run_gobuster",
        description="Directory/file bruteforce on a web target to discover hidden paths.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "wordlist": {
                    "type": "string",
                    "default": "/usr/share/wordlists/dirb/common.txt",
                },
            },
            "required": ["url"],
        },
        fn=run_gobuster,
        requires_approval=True,
    ),
    AgentTool(
        name="run_nikto",
        description="Run nikto web vulnerability scanner — checks for outdated software, misconfigs, dangerous files.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
        },
        fn=run_nikto,
        requires_approval=True,
    ),
    AgentTool(
        name="run_theHarvester",
        description="OSINT harvesting — collect emails, subdomains, hosts for a domain.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "sources": {
                    "type": "string",
                    "description": "Comma-separated source list",
                    "default": "google,bing,crtsh",
                },
            },
            "required": ["domain"],
        },
        fn=run_theHarvester,
        requires_approval=True,
    ),
]

# Passive-only subset: tools that make no active connections to the target
_PASSIVE_NAMES = {"dns_lookup", "run_whois"}
PASSIVE_TOOLS = [t for t in SECURITY_TOOLS if t.name in _PASSIVE_NAMES]
