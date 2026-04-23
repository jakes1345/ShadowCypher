"""ShadowCypher OSINT (Identity) Engine — Absolute Sync (Build V30)."""

import subprocess
import shlex
from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import validate_target


class OSINT:
    """The 'Identity' engine. Handles WHOIS, DNS, and HTTP/SSL probes."""

    @staticmethod
    def get_search_types():
        return ["WHOIS", "DNS", "SSL Cert", "HTTP Headers", "Tech Detect", "MX/SPF Check", "Subnet/ASN", "Zone Transfer"]

    @staticmethod
    def ssl_cert_info(target, port=443, on_output=None, on_complete=None):
        """Fetch SSL certificate information."""
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        from shadowcypher.core.config import config
        openssl = config.get_tool_path("openssl")
        cmd = f"{openssl} s_client -connect {shlex.quote(target)}:{int(port)} -showcerts </dev/null"
        return runner.execute_task_shell(f"SSL_{target}", cmd, callback=on_output)

    @staticmethod
    def http_headers(target, on_output=None, on_complete=None):
        """Fetch HTTP headers."""
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        from shadowcypher.core.config import config
        curl = config.get_tool_path("curl")
        url = target if target.startswith("http") else f"https://{target}"
        return runner.execute_task(f"HEADERS_{target}", [curl, "-I", url], callback=on_output)

    @staticmethod
    def tech_detect(target, on_output=None, on_complete=None):
        """Detect web technologies."""
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        from shadowcypher.core.config import config
        whatweb = config.get_tool_path("whatweb")
        url = target if target.startswith("http") else f"https://{target}"
        return runner.execute_task(f"TECH_{target}", [whatweb, url], callback=on_output)

    @staticmethod
    def email_mx_check(target):
        """Check for MX and SPF records."""
        if not validate_target(target):
            return f"[ERROR] Invalid target: {target}"
        try:
            from shadowcypher.core.config import config
            host = config.get_tool_path("host")
            mx = subprocess.check_output([host, "-t", "mx", target], text=True, timeout=10)
            txt = subprocess.check_output([host, "-t", "txt", target], text=True, timeout=10)
            return mx + txt
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def subnet_info(target):
        """Fetch subnet and ASN information."""
        if not validate_target(target):
            return f"[ERROR] Invalid target: {target}"
        try:
            from shadowcypher.core.config import config
            whois = config.get_tool_path("whois")
            return subprocess.check_output([whois, "-h", "whois.radb.net", target], text=True, timeout=15)
        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def zone_transfer(target, on_output=None, on_complete=None):
        """Attempt a DNS zone transfer."""
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
            return
        from shadowcypher.core.config import config
        dig = config.get_tool_path("dig")
        return runner.execute_task(f"ZONE_TRANSFER_{target}", [dig, "axfr", f"@ns1.{target}", target], callback=on_output)

    @staticmethod
    def ai_intel(query, on_output=None):
        """Advanced AI-Driven OSINT Intelligence Synthesis."""
        from shadowcypher.ai.orchestrator import AIOrchestrator
        logger.info("ai", f"INITIATING_AI_INTEL_GATHERING: {query}")
        
        if on_output: 
            on_output(f"[AI] SEARCHING_GLOBALDB_FOR: {query}")
            on_output("[AI] CORRELATING_IDENTITY_METADATA...")
        
        orch = AIOrchestrator()
        # Uses the local reasoning model to synthesize OSINT findings.
        response = orch.execute_query_sync(
            f"Perform a deep dive OSINT search and identity analysis for: {query}. "
            "Summarize key findings and technical footprints. "
            "Use stealth check for all web requests."
        )
        
        if on_output:
            on_output(f"[AI] INTEL_SYNTHESIS_COMPLETE: {response[:200]}...")
        return response
