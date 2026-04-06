"""Firewall management module — iptables/nftables rule management."""

from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.sanitize import quote, validate_ip, validate_port


_NOOP = lambda x: None


class Firewall:
    """Firewall inspection and management using iptables and nftables."""

    VALID_CHAINS = frozenset({"INPUT", "OUTPUT", "FORWARD", "PREROUTING", "POSTROUTING"})
    VALID_PROTOCOLS = frozenset({"tcp", "udp", "icmp"})

    @staticmethod
    def detect_backend() -> str:
        """Detect which firewall backend is active."""
        nft_out, nft_rc = runner.run_sync("nft list ruleset 2>/dev/null | head -1", shell=True, timeout=5)
        if nft_rc == 0 and nft_out.strip():
            return "nftables"

        ipt_out, ipt_rc = runner.run_sync("iptables -L -n 2>/dev/null | head -1", shell=True, timeout=5)
        if ipt_rc == 0 and ipt_out.strip():
            return "iptables"

        ufw_out, ufw_rc = runner.run_sync("ufw status 2>/dev/null", shell=True, timeout=5)
        if ufw_rc == 0 and "active" in ufw_out.lower():
            return "ufw"

        return "none"

    @staticmethod
    def get_rules(on_output=None, on_complete=None) -> int:
        """Get all firewall rules."""
        backend = Firewall.detect_backend()

        if backend == "nftables":
            cmd = "nft list ruleset"
        elif backend == "iptables":
            cmd = "iptables -L -n -v --line-numbers 2>&1 && echo '\\n=== NAT ===' && iptables -t nat -L -n -v --line-numbers 2>&1"
        elif backend == "ufw":
            cmd = "ufw status verbose"
        else:
            cmd = "echo 'No firewall backend detected (nftables/iptables/ufw)'"

        logger.info("firewall", f"Listing rules (backend: {backend})")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def get_rules_sync() -> str:
        """Get firewall rules synchronously."""
        backend = Firewall.detect_backend()
        if backend == "nftables":
            out, _ = runner.run_sync("nft list ruleset 2>&1", shell=True, timeout=10)
        elif backend == "iptables":
            out, _ = runner.run_sync("iptables -L -n -v --line-numbers 2>&1", shell=True, timeout=10)
        elif backend == "ufw":
            out, _ = runner.run_sync("ufw status verbose 2>&1", shell=True, timeout=10)
        else:
            out = "No firewall backend detected"
        return out

    # ── iptables operations ──

    @staticmethod
    def ipt_add_rule(chain: str, rule: str, on_output=None, on_complete=None) -> int:
        """Add an iptables rule. e.g. chain='INPUT', rule='-p tcp --dport 22 -j ACCEPT'"""
        if chain not in Firewall.VALID_CHAINS:
            (on_output or _NOOP)(f"[ERROR] Invalid chain: {chain}\n")
            (on_complete or _NOOP)(1)
            return -1
        # rule is pre-formed iptables syntax — quote the whole thing would break it
        # but we validate the chain at least
        cmd = f"iptables -A {chain} {rule}"
        logger.info("firewall", f"Add iptables rule: {chain} {rule}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ipt_delete_rule(chain: str, rule_num: int, on_output=None, on_complete=None) -> int:
        """Delete an iptables rule by number."""
        if chain not in Firewall.VALID_CHAINS:
            (on_output or _NOOP)(f"[ERROR] Invalid chain: {chain}\n")
            (on_complete or _NOOP)(1)
            return -1
        rule_num = int(rule_num)
        if rule_num < 1:
            (on_output or _NOOP)("[ERROR] Invalid rule number\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"iptables -D {chain} {rule_num}"
        logger.info("firewall", f"Delete iptables rule: {chain} #{rule_num}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ipt_block_ip(ip: str, on_output=None, on_complete=None) -> int:
        """Block an IP address."""
        if not validate_ip(ip):
            (on_output or _NOOP)(f"[ERROR] Invalid IP: {ip}\n")
            (on_complete or _NOOP)(1)
            return -1
        safe_ip = quote(ip.strip())
        cmd = f"iptables -A INPUT -s {safe_ip} -j DROP && iptables -A OUTPUT -d {safe_ip} -j DROP"
        logger.info("firewall", f"Blocking IP: {ip}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def ipt_block_port(port: int, protocol: str = "tcp", on_output=None, on_complete=None) -> int:
        """Block a port."""
        if not validate_port(port):
            (on_output or _NOOP)(f"[ERROR] Invalid port: {port}\n")
            (on_complete or _NOOP)(1)
            return -1
        if protocol not in Firewall.VALID_PROTOCOLS:
            (on_output or _NOOP)(f"[ERROR] Invalid protocol: {protocol}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"iptables -A INPUT -p {protocol} --dport {int(port)} -j DROP"
        logger.info("firewall", f"Blocking port: {port}/{protocol}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ipt_allow_port(port: int, protocol: str = "tcp", on_output=None, on_complete=None) -> int:
        """Allow a port."""
        if not validate_port(port):
            (on_output or _NOOP)(f"[ERROR] Invalid port: {port}\n")
            (on_complete or _NOOP)(1)
            return -1
        if protocol not in Firewall.VALID_PROTOCOLS:
            (on_output or _NOOP)(f"[ERROR] Invalid protocol: {protocol}\n")
            (on_complete or _NOOP)(1)
            return -1
        cmd = f"iptables -A INPUT -p {protocol} --dport {int(port)} -j ACCEPT"
        logger.info("firewall", f"Allowing port: {port}/{protocol}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ipt_flush(chain: str = None, on_output=None, on_complete=None) -> int:
        """Flush iptables rules."""
        chain_arg = ""
        if chain:
            if chain not in Firewall.VALID_CHAINS:
                (on_output or _NOOP)(f"[ERROR] Invalid chain: {chain}\n")
                (on_complete or _NOOP)(1)
                return -1
            chain_arg = chain
        cmd = f"iptables -F {chain_arg}"
        logger.info("firewall", f"Flushing iptables: {chain or 'all'}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ipt_save(on_output=None, on_complete=None) -> int:
        """Save iptables rules to persist across reboots."""
        cmd = "iptables-save > /etc/iptables/rules.v4 2>/dev/null || iptables-save"
        logger.info("firewall", "Saving iptables rules")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    # ── UFW shorthand ──

    @staticmethod
    def ufw_enable(on_output=None, on_complete=None) -> int:
        cmd = "ufw --force enable"
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ufw_disable(on_output=None, on_complete=None) -> int:
        cmd = "ufw disable"
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ufw_allow(port: int, protocol: str = "tcp", on_output=None, on_complete=None) -> int:
        if not validate_port(port):
            return -1
        if protocol not in Firewall.VALID_PROTOCOLS:
            return -1
        cmd = f"ufw allow {int(port)}/{protocol}"
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)

    @staticmethod
    def ufw_deny(port: int, protocol: str = "tcp", on_output=None, on_complete=None) -> int:
        if not validate_port(port):
            return -1
        if protocol not in Firewall.VALID_PROTOCOLS:
            return -1
        cmd = f"ufw deny {int(port)}/{protocol}"
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, sudo=True)
