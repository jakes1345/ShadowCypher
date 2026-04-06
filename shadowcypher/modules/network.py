"""Network operations module — packet capture, ARP scanning, port scanning, service fingerprinting."""

from shadowcypher.core.runner import runner
from shadowcypher.core.logger import logger
from shadowcypher.core.config import config
from shadowcypher.core.sanitize import (
    quote, validate_target, validate_interface, validate_ports,
    validate_port, sanitize_bpf_filter,
)


_NOOP = lambda x: None


class Network:
    """Real network operations using tcpdump, nmap, arp scanning."""

    @staticmethod
    def get_interfaces() -> str:
        """List all network interfaces with their IPs."""
        output, _ = runner.run_sync("ip -br addr", timeout=5)
        return output

    @staticmethod
    def get_routes() -> str:
        """Show routing table."""
        output, _ = runner.run_sync("ip route show", timeout=5)
        return output

    @staticmethod
    def get_connections() -> str:
        """Show active network connections."""
        output, _ = runner.run_sync("ss -tlnp", timeout=5, shell=True)
        return output

    @staticmethod
    def get_arp_table() -> str:
        """Show ARP cache."""
        output, _ = runner.run_sync("ip neigh show", timeout=5)
        return output

    @staticmethod
    def _detect_default_iface() -> str:
        """Auto-detect the default network interface."""
        out, _ = runner.run_sync(
            "ip route | grep default | awk '{print $5}' | head -1", shell=True, timeout=5
        )
        return out.strip() or "eth0"

    @staticmethod
    def _detect_subnet() -> str:
        """Auto-detect the local subnet."""
        out, _ = runner.run_sync(
            "ip route | grep 'src' | head -1 | awk '{print $1}'", shell=True, timeout=5
        )
        return out.strip() or "192.168.1.0/24"

    @staticmethod
    def arp_scan(interface: str = None, subnet: str = None,
                 on_output=None, on_complete=None) -> int:
        """ARP scan a local network to discover hosts."""
        nmap = config.get_tool_path("nmap")
        if subnet is None:
            subnet = Network._detect_subnet()
        elif not validate_target(subnet):
            (on_output or _NOOP)(f"[ERROR] Invalid subnet: {subnet}\n")
            (on_complete or _NOOP)(1)
            return -1

        iface_flag = ""
        if interface:
            if not validate_interface(interface):
                (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
                (on_complete or _NOOP)(1)
                return -1
            iface_flag = f"-e {quote(interface)}"

        cmd = f"{quote(nmap)} -sn -PR {iface_flag} {quote(subnet)}"
        logger.info("network", f"ARP scan: {subnet}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def packet_capture(interface: str = None, count: int = 100, filter_expr: str = "",
                       on_output=None, on_complete=None) -> int:
        """Capture packets using tcpdump."""
        tcpdump = config.get_tool_path("tcpdump")
        if interface is None:
            interface = Network._detect_default_iface()
        elif not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1

        count = max(1, min(int(count), 100000))
        filter_part = ""
        if filter_expr:
            safe_filter = sanitize_bpf_filter(filter_expr)
            if safe_filter:
                filter_part = f" {safe_filter}"

        cmd = f"{quote(tcpdump)} -i {quote(interface)} -c {count} -nn -l{filter_part}"
        logger.info("network", f"Packet capture: iface={interface}, count={count}, filter={filter_expr}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def packet_capture_to_file(interface: str, output_file: str, count: int = 1000,
                                filter_expr: str = "", on_output=None, on_complete=None) -> int:
        """Capture packets and save to pcap file."""
        tcpdump = config.get_tool_path("tcpdump")
        if not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1

        count = max(1, min(int(count), 100000))
        filter_part = ""
        if filter_expr:
            safe_filter = sanitize_bpf_filter(filter_expr)
            if safe_filter:
                filter_part = f" {safe_filter}"

        cmd = f"{quote(tcpdump)} -i {quote(interface)} -c {count} -w {quote(output_file)}{filter_part}"
        logger.info("network", f"Packet capture to file: {output_file}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def port_scan_tcp_connect(target: str, ports: str = "1-1024",
                               on_output=None, on_complete=None) -> int:
        """TCP connect scan (no root needed)."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1
        if not validate_ports(ports):
            (on_output or _NOOP)(f"[ERROR] Invalid port spec: {ports}\n")
            (on_complete or _NOOP)(1)
            return -1

        nmap = config.get_tool_path("nmap")
        cmd = f"{quote(nmap)} -sT -p {ports} -T4 --open {quote(target)}"
        logger.info("network", f"TCP connect scan: {target}:{ports}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def port_scan_syn(target: str, ports: str = "1-65535",
                       on_output=None, on_complete=None) -> int:
        """SYN stealth scan (requires root)."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1
        if not validate_ports(ports):
            (on_output or _NOOP)(f"[ERROR] Invalid port spec: {ports}\n")
            (on_complete or _NOOP)(1)
            return -1

        nmap = config.get_tool_path("nmap")
        cmd = f"{quote(nmap)} -sS -p {ports} -T4 --open {quote(target)}"
        logger.info("network", f"SYN stealth scan: {target}:{ports}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)

    @staticmethod
    def service_fingerprint(target: str, ports: str = None,
                             on_output=None, on_complete=None) -> int:
        """Detailed service version detection."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1

        nmap = config.get_tool_path("nmap")
        port_arg = ""
        if ports:
            if not validate_ports(ports):
                (on_output or _NOOP)(f"[ERROR] Invalid port spec: {ports}\n")
                (on_complete or _NOOP)(1)
                return -1
            port_arg = f"-p {ports}"
        cmd = f"{quote(nmap)} -sV --version-intensity 9 -sC {port_arg} {quote(target)}"
        logger.info("network", f"Service fingerprint: {target}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def network_monitor(interface: str = None, on_output=None, on_complete=None) -> int:
        """Monitor network traffic statistics in real-time."""
        if interface is None:
            interface = Network._detect_default_iface()
        elif not validate_interface(interface):
            (on_output or _NOOP)(f"[ERROR] Invalid interface: {interface}\n")
            (on_complete or _NOOP)(1)
            return -1

        # Use a script that reads /proc/net/dev periodically
        safe_iface = quote(interface)
        script = f"""
iface={safe_iface}
prev_rx=0; prev_tx=0
while true; do
    line=$(grep "$iface" /proc/net/dev)
    rx=$(echo "$line" | awk '{{print $2}}')
    tx=$(echo "$line" | awk '{{print $10}}')
    if [ "$prev_rx" -ne 0 ]; then
        drx=$((rx - prev_rx))
        dtx=$((tx - prev_tx))
        echo "$(date +%H:%M:%S) | RX: $((drx/1024)) KB/s | TX: $((dtx/1024)) KB/s"
    fi
    prev_rx=$rx; prev_tx=$tx
    sleep 1
done
"""
        logger.info("network", f"Network monitor started: {interface}")
        return runner.run(script, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def get_public_ip() -> str:
        """Get public IP address."""
        output, _ = runner.run_sync(
            "curl -4sS --max-time 5 https://ifconfig.me/ip", shell=True, timeout=10
        )
        return output.strip() if output else "N/A"

    @staticmethod
    def dns_leak_test(on_output=None, on_complete=None) -> int:
        """Basic DNS leak test by checking resolver IPs."""
        cmd = "dig +short whoami.akamai.net @ns1-1.akamaitech.net && echo '---' && dig +short myip.opendns.com @resolver1.opendns.com"
        logger.info("network", "DNS leak test started")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True)

    @staticmethod
    def network_os_detection(target: str, on_output=None, on_complete=None) -> int:
        """Perform OS detection and aggressive service scanning."""
        if not validate_target(target):
            (on_output or _NOOP)(f"[ERROR] Invalid target: {target}\n")
            (on_complete or _NOOP)(1)
            return -1
        nmap = config.get_tool_path("nmap")
        cmd = f"{quote(nmap)} -O -A -T4 {quote(target)}"
        logger.info("network", f"OS detection scan: {target}")
        return runner.run(cmd, on_output or _NOOP, on_complete or _NOOP, shell=True, sudo=True)
