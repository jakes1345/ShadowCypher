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
        if not validate_target(url):
            if on_output:
                on_output(f"[ERROR] Invalid URL: {url}")
            return

        if not os.path.exists(wordlist):
            if on_output:
                on_output(f"[ERROR] Wordlist not found: {wordlist}")
            return

        # Ffuf requires FUZZ keyword
        fuzz_url = url.rstrip("/") + "/FUZZ"
        if extension:
            fuzz_url += f".{extension.strip('.')}"

        args = ["ffuf", "-c", "-w", wordlist, "-u", fuzz_url, "-t", "50"]
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
        if not validate_target(url):
            if on_output:
                on_output(f"[ERROR] Invalid URL: {url}")
            return

        if not os.path.exists(wordlist):
            if on_output:
                on_output(f"[ERROR] Wordlist not found: {wordlist}")
            return

        # Replace the subdomain part with FUZZ
        # Example: host_header = "FUZZ.target.com"
        args = [
            "ffuf",
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
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return

        args = ["nuclei", "-u", target, "-c", "50", "-no-color"]

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
