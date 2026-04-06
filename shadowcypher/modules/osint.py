"""ShadowCypher OSINT (Identity) Engine — Absolute Sync (Build V30)."""

from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger

class OSINT:
    """The 'Identity' engine. Handles WHOIS, DNS, and HTTP/SSL probes."""
    
    @staticmethod
    def get_search_types():
        return ["WHOIS", "DNS", "SSL Cert", "HTTP Headers", "Tech Detect", "MX/SPF Check", "Subnet/ASN", "Zone Transfer"]

    @staticmethod
    def ssl_cert_info(target, port=443, on_output=None, on_complete=None):
        """Fetch SSL certificate information."""
        cmd = f"openssl s_client -connect {target}:{port} -showcerts </dev/null"
        runner.execute_task(f"SSL_{target}", cmd, callback=on_output)

    @staticmethod
    def http_headers(target, on_output=None, on_complete=None):
        """Fetch HTTP headers."""
        url = target if target.startswith("http") else f"https://{target}"
        cmd = f"curl -I {url}"
        runner.execute_task(f"HEADERS_{target}", cmd, callback=on_output)

    @staticmethod
    def tech_detect(target, on_output=None, on_complete=None):
        """Detect web technologies."""
        url = target if target.startswith("http") else f"https://{target}"
        cmd = f"whatweb {url}"
        runner.execute_task(f"TECH_{target}", cmd, callback=on_output)

    @staticmethod
    def email_mx_check(target):
        """Check for MX and SPF records."""
        import os
        os.system(f"host -t mx {target} > /tmp/mx_check.txt")
        os.system(f"host -t txt {target} >> /tmp/mx_check.txt")
        with open("/tmp/mx_check.txt", "r") as f:
            return f.read()

    @staticmethod
    def subnet_info(target):
        """Fetch subnet and ASN information."""
        import os
        os.system(f"whois -h whois.radb.net {target} > /tmp/subnet_info.txt")
        with open("/tmp/subnet_info.txt", "r") as f:
            return f.read()

    @staticmethod
    def zone_transfer(target, on_output=None, on_complete=None):
        """Attempt a DNS zone transfer."""
        cmd = f"dig axfr @ns1.{target} {target}"
        runner.execute_task(f"ZONE_TRANSFER_{target}", cmd, callback=on_output)
