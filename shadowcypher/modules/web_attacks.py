"""Web Attacks Module — Ffuf fuzzing and Nuclei template scanning."""

from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_target
from shadowcypher.core.logger import logger
import shlex
import os


class WebAttacks:
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
        from shadowcypher.core.config import config
        ffuf = config.get_tool_path("ffuf")
        
        if not validate_target(url):
            if on_output: on_output(f"[ERROR] Invalid URL: {url}")
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
        from shadowcypher.core.config import config
        ffuf = config.get_tool_path("ffuf")
        
        if not validate_target(url):
            if on_output: on_output(f"[ERROR] Invalid URL: {url}")
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
        from shadowcypher.core.config import config
        nuclei = config.get_tool_path("nuclei")
        
        if not validate_target(target):
            if on_output: on_output(f"[ERROR] Invalid target: {target}")
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
    def mhddos_strike(target, method="GET", threads=100, duration=60, on_output=None):
        """Execute elite Layer 7 or Layer 4 suppression using the MHDDoS engine."""
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        path = os.path.join(project_root, "tools", "elite", "MHDDoS", "start.py")
        proxies = os.path.join(project_root, "tools", "elite", "MHDDoS", "files", "proxies", "proxies.txt")
        
        if not os.path.exists(path):
            if on_output: on_output("[ERROR] MHDDoS_ENGINE_NOT_STAGED. Run elite tool acquisition.")
            return

        # Basic command assembly
        args = ["python3", path, method, target, "5", str(threads), proxies, "100", str(duration)]
        logger.info("web", f"MHDDoS STRIKE_DISPATCHED: {target} (Method: {method}, Duration: {duration}s)")
        return runner.execute_task(f"MHDDOS_{target}", args, callback=on_output)
