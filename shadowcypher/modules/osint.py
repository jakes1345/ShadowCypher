"""OSINT module — open source intelligence gathering."""

from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import quote, validate_target, validate_port


_NOOP = lambda x: None


class OSINT:
    """Open source intelligence gathering tools."""

    @staticmethod
    def ssl_cert_info(host: str, port: int = 443, on_output=None, on_complete=None) -> int:
        """Get SSL certificate information."""
        if not validate_target(host):
            (on_output or _NOOP)(f"[ERROR] Invalid host: {host}\n")
            (on_complete or _NOOP)(1)
            return -1
        if not validate_port(port):
            (on_output or _NOOP)(f"[ERROR] Invalid port: {port}\n")
            (on_complete or _NOOP)(1)
            return -1
        port = int(port)
        cmd = f"echo | openssl s_client -connect {quote(host)}:{port} -servername {quote(host)} 2>/dev/null | openssl x509 -noout -text 2>/dev/null"
        logger.info("osint", f"SSL cert: {host}:{port}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def http_headers(url: str, on_output=None, on_complete=None) -> int:
        """Fetch HTTP headers from a URL."""
        cmd = f"curl -sI --max-time 10 {quote(url)}"
        logger.info("osint", f"HTTP headers: {url}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def email_mx_check(domain: str) -> str:
        """Check MX records and mail server info for a domain."""
        if not validate_target(domain):
            return f"Invalid domain: {domain}"
        safe = quote(domain)
        output, _ = runner.run_sync(
            f"dig +short {safe} MX 2>/dev/null && echo '---SPF---' && dig +short {safe} TXT 2>/dev/null | grep -i spf",
            shell=True, timeout=10
        )
        return output

    @staticmethod
    def shodan_lookup(ip: str, api_key: str = None) -> str:
        """Query Shodan for a given IP (requires API key)."""
        if not api_key:
            return "Shodan API key required. Set in config.json under osint.shodan_api_key"
        if not validate_target(ip):
            return f"Invalid IP: {ip}"
        cmd = f"curl -sS {quote(f'https://api.shodan.io/shodan/host/{ip}?key={api_key}')} --max-time 10"
        output, _ = runner.run_sync(cmd, shell=True, timeout=15)
        return output

    @staticmethod
    def subnet_info(ip: str) -> str:
        """Get subnet/ASN information for an IP."""
        if not validate_target(ip):
            return f"Invalid IP: {ip}"
        output, _ = runner.run_sync(
            f"whois -h whois.cymru.com {quote(f' -v {ip}')} 2>/dev/null",
            shell=True, timeout=10
        )
        return output

    @staticmethod
    def zone_transfer(domain: str, ns: str = None, on_output=None, on_complete=None) -> int:
        """Attempt DNS zone transfer (AXFR)."""
        if not validate_target(domain):
            (on_output or _NOOP)(f"[ERROR] Invalid domain: {domain}\n")
            (on_complete or _NOOP)(1)
            return -1
        if ns is None:
            ns_out, _ = runner.run_sync(f"dig +short {quote(domain)} NS | head -1", shell=True, timeout=5)
            ns = ns_out.strip() if ns_out.strip() else domain
        cmd = f"dig AXFR {quote(domain)} @{quote(ns)}"
        logger.info("osint", f"Zone transfer attempt: {domain} via {ns}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def tech_detect(url: str, on_output=None, on_complete=None) -> int:
        """Detect web technologies via HTTP headers and response analysis."""
        safe = quote(url)
        script = f"""
echo "=== HTTP Headers ==="
headers=$(curl -sI --max-time 10 {safe} 2>/dev/null)
echo "$headers"
echo ""
echo "=== Technology Hints ==="
echo "$headers" | grep -iE '(server|x-powered-by|x-aspnet|x-generator|x-drupal|cf-ray|x-varnish|x-cache)' || echo "No technology headers found"
echo ""
echo "=== Security Headers ==="
echo "$headers" | grep -iE '(strict-transport|content-security-policy|x-frame-options|x-content-type|x-xss-protection|referrer-policy|permissions-policy)' || echo "No security headers found"
"""
        logger.info("osint", f"Tech detection: {url}")
        return runner.run(script, on_output or _NOOP, on_complete or _NOOP, shell=True)
