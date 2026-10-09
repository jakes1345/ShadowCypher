"""
Counter-Intelligence Detection Engine — ShadowCypher Sovereign Platform.
Detects MITM/ARP spoofing, SSL interception, DNS leaks, rogue DHCP,
promiscuous interfaces, traffic anomalies, and performs OSINT self-audit.

Zero telemetry. Stealth-aware. Scapy-optional (subprocess fallback throughout).
"""

import hashlib
import json
import re
import socket
import ssl
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger
from shadowcypher.core.module import BaseModule
from shadowcypher.core.sanitize import validate_ip
from shadowcypher.core.stealth import stealth


class CounterIntelEngine(BaseModule):
    """
    Sovereign counter-intelligence engine.
    All methods run in background threads and communicate via on_output / on_complete callbacks.
    All findings are emitted to the 'counter_intel' bus channel.
    """

    # Known-good CA organisation names used for issuer trust validation
    _TRUSTED_CA_ORGS = {
        "DigiCert Inc", "GlobalSign", "Let's Encrypt", "Sectigo Limited",
        "Google Trust Services LLC", "Amazon", "Cloudflare, Inc.",
        "QuoVadis Trustlink Schweiz AG", "Comodo CA Limited", "GoDaddy.com, Inc.",
        "IdenTrust", "Internet Security Research Group", "Entrust, Inc.",
        "Baltimore CyberTrust", "Microsoft Corporation", "Apple Inc.",
        "ISRG", "Starfield Technologies",
    }

    # Ports considered normal outbound TCP
    _ALLOWED_PORTS = frozenset({
        20, 21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995,
        2083, 2087, 3389, 8080, 8443,
    })

    # Tor relay / proxy ports — unexpected from non-Tor processes
    _TOR_PORTS = frozenset({9001, 9030, 9050, 9051, 9150})

    # Default TLS targets for interception check
    _DEFAULT_TLS_TARGETS = ["google.com:443", "cloudflare.com:443", "one.one.one.one:443"]

    def __init__(self):
        super().__init__(module_name="counter_intel")
        self._findings: List[dict] = []
        self._lock = threading.Lock()
        # In-memory fingerprint baseline — populated on first SSL check pass
        self._fp_baseline: Dict[str, str] = {}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _emit(self, finding: dict) -> None:
        """Record a finding and broadcast it on the bus."""
        with self._lock:
            self._findings.append(finding)
        bus.publish("counter_intel", finding)
        sev = finding.get("severity", "info").upper()
        ftype = finding.get("type", "UNKNOWN")
        logger.info("counter_intel", f"FINDING [{sev}]: {ftype}")

    def _out(self, cb: Optional[Callable], msg: str) -> None:
        """Call the on_output callback safely."""
        if cb:
            try:
                cb(msg)
            except Exception:
                pass

    def _done(self, cb: Optional[Callable], result) -> None:
        """Call the on_complete callback safely."""
        if cb:
            try:
                cb(result)
            except Exception:
                pass

    def _run(self, args: list, timeout: int = 30) -> str:
        """Run a subprocess, return stdout. Returns '' on any error."""
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            return r.stdout or ""
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
            return ""

    # ── 1. ARP Spoofing Detection ─────────────────────────────────────────────

    def detect_arp_spoofing(self, interface: str = "eth0", duration: int = 30,
                             on_output: Optional[Callable] = None,
                             on_complete: Optional[Callable] = None) -> None:
        """
        Capture ARP traffic and alert on IP→multi-MAC mappings (cache poisoning).
        Uses scapy when available; falls back to repeated arp -n polling.
        """
        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, f"[ARP] Monitoring {interface} for {duration}s...")
                self.log(f"ARP_SPOOF_DETECT: iface={interface} duration={duration}")

                ip_mac_map: Dict[str, set] = defaultdict(set)

                # ── Try scapy ──
                try:
                    from scapy.all import ARP, sniff  # type: ignore  # noqa: F401

                    def _pkt_cb(pkt):
                        if ARP in pkt and pkt[ARP].op == 2:  # is-at (reply)
                            ip_mac_map[pkt[ARP].psrc].add(pkt[ARP].hwsrc)

                    self._out(on_output, "[ARP] scapy active — capturing ARP replies...")
                    sniff(filter="arp", iface=interface, prn=_pkt_cb,
                          timeout=duration, store=False)

                except ImportError:
                    # ── Fallback: poll arp -n ──
                    import time
                    self._out(on_output, "[ARP] scapy not available — polling arp -n...")
                    steps = max(3, duration // 10)
                    for _ in range(steps):
                        out = self._run(["arp", "-n"], timeout=5)
                        for line in out.splitlines():
                            parts = line.split()
                            # Linux: Address  HWtype  HWaddress  Flags  Iface
                            if len(parts) >= 3 and ":" in parts[2]:
                                ip_addr, mac = parts[0], parts[2]
                                if validate_ip(ip_addr) and mac != "(incomplete)":
                                    ip_mac_map[ip_addr].add(mac)
                        time.sleep(duration / steps)

                # ── Evaluate map ──
                for ip_addr, macs in ip_mac_map.items():
                    self._out(on_output, f"[ARP] {ip_addr} → {', '.join(macs)}")
                    if len(macs) > 1:
                        mac_list = sorted(macs)
                        self._out(on_output,
                                  f"[!] ARP SPOOF: {ip_addr} claims MACs {mac_list[0]} AND {mac_list[1]}")
                        finding = {
                            "type": "ARP_SPOOF",
                            "ip": ip_addr,
                            "mac1": mac_list[0],
                            "mac2": mac_list[1],
                            "all_macs": mac_list,
                            "severity": "critical",
                        }
                        self._emit(finding)
                        findings.append(finding)

                if not findings:
                    self._out(on_output, "[ARP] Clean — no ARP spoofing detected.")

            except Exception as exc:
                self._out(on_output, f"[ARP ERROR] {exc}")
                logger.error("counter_intel", f"ARP_SPOOF_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_ARP").start()

    # ── 2. Promiscuous Interface Detection ────────────────────────────────────

    def detect_promiscuous_interfaces(self, on_output: Optional[Callable] = None,
                                      on_complete: Optional[Callable] = None) -> None:
        """
        Check every network interface for the PROMISC flag.
        Primary: ip link show. Fallback: /sys/class/net/<iface>/flags bitmask.
        """
        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, "[PROMISC] Checking interface flags...")
                self.log("PROMISC_DETECT")

                out = self._run(["ip", "link", "show"], timeout=10)
                if out:
                    for line in out.splitlines():
                        # "2: eth0: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP>"
                        m = re.match(r'^\d+:\s+([\w@.-]+):\s+<([^>]+)>', line)
                        if m:
                            iface = m.group(1).split("@")[0]
                            flags = [f.strip() for f in m.group(2).split(",")]
                            if "PROMISC" in flags:
                                self._out(on_output,
                                          f"[!] PROMISC: {iface} is in promiscuous mode (flags: {flags})")
                                finding = {
                                    "type": "PROMISC_IFACE",
                                    "interface": iface,
                                    "flags": flags,
                                    "severity": "warning",
                                }
                                self._emit(finding)
                                findings.append(finding)
                            else:
                                self._out(on_output, f"[PROMISC] {iface}: {flags[:4]}... OK")
                else:
                    # Fallback: /sys/class/net bitmask (IFF_PROMISC = 0x100)
                    import os
                    net_base = "/sys/class/net"
                    try:
                        for iface in os.listdir(net_base):
                            flags_path = os.path.join(net_base, iface, "flags")
                            try:
                                with open(flags_path) as fh:
                                    flags_val = int(fh.read().strip(), 16)
                                if flags_val & 0x100:
                                    self._out(on_output,
                                              f"[!] PROMISC: {iface} (flags=0x{flags_val:x})")
                                    finding = {
                                        "type": "PROMISC_IFACE",
                                        "interface": iface,
                                        "flags_hex": hex(flags_val),
                                        "severity": "warning",
                                    }
                                    self._emit(finding)
                                    findings.append(finding)
                            except (OSError, ValueError):
                                pass
                    except OSError:
                        self._out(on_output, "[PROMISC] /sys/class/net not accessible.")

                if not findings:
                    self._out(on_output, "[PROMISC] Clean — no promiscuous interfaces found.")

            except Exception as exc:
                self._out(on_output, f"[PROMISC ERROR] {exc}")
                logger.error("counter_intel", f"PROMISC_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_PROMISC").start()

    # ── 3. SSL Interception Detection ─────────────────────────────────────────

    def detect_ssl_interception(self, targets: Optional[List[str]] = None,
                                 on_output: Optional[Callable] = None,
                                 on_complete: Optional[Callable] = None) -> None:
        """
        Fetch live TLS certs from well-known endpoints and compare SHA-256
        fingerprints against a runtime baseline. A changed fingerprint or
        an unknown issuer indicates a transparent MITM proxy.
        """
        targets = targets or self._DEFAULT_TLS_TARGETS

        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, "[SSL] Checking TLS certificate integrity...")
                self.log(f"SSL_INTERCEPT_CHECK: targets={targets}")

                ctx = ssl.create_default_context()

                for target_spec in targets:
                    parts = target_spec.rsplit(":", 1)
                    host = parts[0]
                    port = int(parts[1]) if len(parts) == 2 else 443

                    try:
                        self._out(on_output, f"[SSL] Connecting to {host}:{port}...")
                        conn = socket.create_connection((host, port), timeout=10)
                        with ctx.wrap_socket(conn, server_hostname=host) as tls:
                            cert_bin = tls.getpeercert(binary_form=True)
                            cert_info = tls.getpeercert()

                        fp = hashlib.sha256(cert_bin).hexdigest()

                        # Extract issuer
                        issuer_dict = {k: v for tup in cert_info.get("issuer", [])
                                       for k, v in tup}
                        issuer_org = issuer_dict.get("organizationName", "")
                        issuer_cn  = issuer_dict.get("commonName", "")

                        self._out(on_output,
                                  f"[SSL] {host}: FP={fp[:20]}... Issuer={issuer_org or issuer_cn}")

                        # Compare / pin fingerprint
                        baseline = self._fp_baseline.get(host)
                        if baseline is None:
                            self._fp_baseline[host] = fp
                            self._out(on_output, f"[SSL] {host}: baseline fingerprint pinned.")
                        elif baseline != fp:
                            self._out(on_output,
                                      f"[!] SSL INTERCEPT: {host} cert changed! "
                                      f"expected={baseline[:20]}... got={fp[:20]}...")
                            finding = {
                                "type": "SSL_INTERCEPT",
                                "host": host,
                                "expected_fp": baseline,
                                "got_fp": fp,
                                "severity": "critical",
                            }
                            self._emit(finding)
                            findings.append(finding)

                        # Check issuer trust
                        org_trusted = any(t in issuer_org for t in self._TRUSTED_CA_ORGS)
                        cn_trusted  = any(t in issuer_cn  for t in self._TRUSTED_CA_ORGS)
                        if issuer_org and not org_trusted and not cn_trusted:
                            self._out(on_output,
                                      f"[!] SSL UNKNOWN CA: {host} issued by '{issuer_org}' "
                                      f"— may be a corporate MITM proxy")
                            finding = {
                                "type": "SSL_UNKNOWN_CA",
                                "host": host,
                                "issuer_org": issuer_org,
                                "fingerprint": fp,
                                "severity": "warning",
                            }
                            self._emit(finding)
                            findings.append(finding)

                    except ssl.SSLCertVerificationError as exc:
                        self._out(on_output,
                                  f"[!] SSL INTERCEPT: {host} cert verification FAILED ({exc})")
                        finding = {
                            "type": "SSL_INTERCEPT",
                            "host": host,
                            "error": str(exc),
                            "severity": "critical",
                        }
                        self._emit(finding)
                        findings.append(finding)
                    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
                        self._out(on_output, f"[SSL] Cannot reach {host}:{port} — {exc}")

                if not findings:
                    self._out(on_output, "[SSL] Clean — no SSL interception detected.")

            except Exception as exc:
                self._out(on_output, f"[SSL ERROR] {exc}")
                logger.error("counter_intel", f"SSL_INTERCEPT_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_SSL").start()

    # ── 4. DNS Leak Detection ─────────────────────────────────────────────────

    def detect_dns_leak(self, on_output: Optional[Callable] = None,
                         on_complete: Optional[Callable] = None) -> None:
        """
        Check /etc/resolv.conf for non-local nameservers when Tor is active,
        and query an external leak-test endpoint to see what resolvers are visible.
        """
        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, "[DNS] DNS leak detection...")
                self.log("DNS_LEAK_CHECK")

                # 1. /etc/resolv.conf audit
                try:
                    with open("/etc/resolv.conf") as fh:
                        resolv = fh.read()
                    for line in resolv.splitlines():
                        line = line.strip()
                        if line.startswith("nameserver"):
                            ns = line.split()[-1]
                            self._out(on_output, f"[DNS] nameserver: {ns}")
                            if stealth.active and ns not in ("127.0.0.1", "::1", "127.0.0.53"):
                                self._out(on_output,
                                          f"[!] DNS LEAK: Tor active but resolv.conf uses {ns}")
                                finding = {
                                    "type": "DNS_LEAK",
                                    "source": "resolv.conf",
                                    "resolver_ip": ns,
                                    "severity": "warning",
                                }
                                self._emit(finding)
                                findings.append(finding)
                except OSError:
                    self._out(on_output, "[DNS] /etc/resolv.conf not readable.")

                # 2. External resolver check
                if stealth.active:
                    self._out(on_output, "[DNS] Stealth active — querying via Tor...")
                    try:
                        session = stealth.torify_requests_session()
                        resp = session.get("https://ipleak.net/json/", timeout=15,
                                           headers={"User-Agent": "ShadowCypher/1.0 counter-intel"})
                        data = resp.json()
                        resolver_ip = data.get("ip", "UNKNOWN")
                        self._out(on_output, f"[DNS] Tor exit resolver: {resolver_ip}")
                    except ImportError:
                        self._out(on_output, "[DNS] requests not available — skipping Tor resolver check.")
                    except Exception as exc:
                        self._out(on_output, f"[DNS] Tor resolver check failed: {exc}")
                else:
                    self._out(on_output, "[DNS] Querying ipleak.net for visible resolvers...")
                    try:
                        req = urllib.request.Request(
                            "https://ipleak.net/json/",
                            headers={"User-Agent": "ShadowCypher/1.0 counter-intel"},
                        )
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            data = json.loads(resp.read())
                        resolver_ip = data.get("ip", "UNKNOWN")
                        country     = data.get("country_name", "?")
                        isp         = data.get("isp_name", "?")
                        self._out(on_output,
                                  f"[DNS] Public resolver: {resolver_ip} | {isp} ({country})")
                    except Exception as exc:
                        self._out(on_output, f"[DNS] ipleak.net unreachable: {exc}")

                if not findings:
                    self._out(on_output, "[DNS] Clean — no DNS leaks detected.")

            except Exception as exc:
                self._out(on_output, f"[DNS ERROR] {exc}")
                logger.error("counter_intel", f"DNS_LEAK_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_DNS").start()

    # ── 5. Rogue DHCP Detection ───────────────────────────────────────────────

    def detect_rogue_dhcp(self, interface: str = "eth0",
                           on_output: Optional[Callable] = None,
                           on_complete: Optional[Callable] = None) -> None:
        """
        Listen for DHCP OFFER packets. More than one offering server = rogue DHCP.
        Uses scapy when available; falls back to inspecting system lease files.
        """
        def _worker():
            findings: List[dict] = []
            dhcp_servers: set = set()
            try:
                self._out(on_output, f"[DHCP] Rogue DHCP detection on {interface}...")
                self.log(f"ROGUE_DHCP_DETECT: iface={interface}")

                try:
                    from scapy.all import BOOTP, DHCP, sniff  # type: ignore

                    def _pkt_cb(pkt):
                        if DHCP in pkt:
                            opts = dict(
                                (k, v) for k, v in pkt[DHCP].options
                                if isinstance(k, str)
                            )
                            if opts.get("message-type") == 2:  # OFFER
                                server_ip = str(pkt[BOOTP].siaddr)
                                if validate_ip(server_ip) and server_ip != "0.0.0.0":
                                    dhcp_servers.add(server_ip)

                    self._out(on_output, "[DHCP] Sniffing DHCP OFFERs via scapy (10s)...")
                    sniff(filter="udp and (port 67 or port 68)",
                          iface=interface, prn=_pkt_cb, timeout=10, store=False)

                except ImportError:
                    # Fallback: parse system lease files
                    import os
                    self._out(on_output, "[DHCP] scapy unavailable — scanning lease files...")
                    lease_sources = [
                        "/var/lib/dhcp/dhclient.leases",
                        "/var/lib/NetworkManager/dhclient.leases",
                        "/run/systemd/netif/leases/",
                    ]
                    for src in lease_sources:
                        if not os.path.exists(src):
                            continue
                        try:
                            if os.path.isdir(src):
                                for fname in os.listdir(src):
                                    content = open(os.path.join(src, fname)).read()
                                    for ip in re.findall(r'SERVER_ADDRESS=([\d\.]+)', content):
                                        if validate_ip(ip):
                                            dhcp_servers.add(ip)
                            else:
                                content = open(src).read()
                                for ip in re.findall(
                                        r'option dhcp-server-identifier\s+([\d\.]+)', content):
                                    if validate_ip(ip):
                                        dhcp_servers.add(ip)
                        except OSError:
                            pass

                self._out(on_output,
                          f"[DHCP] DHCP server(s) seen: {', '.join(dhcp_servers) or 'none'}")

                if len(dhcp_servers) > 1:
                    server_list = sorted(dhcp_servers)
                    self._out(on_output,
                              f"[!] ROGUE DHCP: {len(dhcp_servers)} servers — {server_list}")
                    finding = {
                        "type": "ROGUE_DHCP",
                        "servers": server_list,
                        "rogue_server": server_list[-1],
                        "severity": "critical",
                    }
                    self._emit(finding)
                    findings.append(finding)
                else:
                    self._out(on_output, "[DHCP] Clean — single DHCP server or none detected.")

            except Exception as exc:
                self._out(on_output, f"[DHCP ERROR] {exc}")
                logger.error("counter_intel", f"ROGUE_DHCP_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_DHCP").start()

    # ── 6. Traffic Anomaly Scan ───────────────────────────────────────────────

    def scan_traffic_anomalies(self, on_output: Optional[Callable] = None,
                                on_complete: Optional[Callable] = None) -> None:
        """
        Parse ss -tupn (or netstat fallback) to find unexpected outbound
        connections: non-standard ports, Tor ports from unknown processes,
        and unusual UDP traffic.
        """
        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, "[TRAFFIC] Traffic anomaly scan (ss -tupn)...")
                self.log("TRAFFIC_ANOMALY_SCAN")

                out = self._run(["ss", "-tupn"], timeout=15)
                if not out:
                    out = self._run(["netstat", "-tupn"], timeout=15)
                if not out:
                    self._out(on_output, "[TRAFFIC] ss/netstat unavailable — skipping.")
                    self._done(on_complete, findings)
                    return

                for line in out.splitlines():
                    line = line.strip()
                    if not line or line.startswith("Netid") or line.startswith("Proto"):
                        continue

                    parts = line.split()
                    if len(parts) < 5:
                        continue

                    proto  = parts[0].lower()
                    local  = parts[4] if len(parts) > 4 else ""
                    remote = parts[5] if len(parts) > 5 else ""
                    proc   = parts[-1] if "pid=" in parts[-1] or "users:" in parts[-1] else ""

                    # Parse remote port from "ip:port" or "[ipv6]:port"
                    remote_port = 0
                    try:
                        remote_port = int(remote.rsplit(":", 1)[-1])
                    except (ValueError, IndexError):
                        pass

                    if remote_port == 0:
                        continue

                    remote_host = remote.rsplit(":", 1)[0].strip("[]")

                    # Skip loopback and unresolved wildcard
                    if remote_host in ("127.0.0.1", "::1", "*", "0.0.0.0", "::", "[::]"):
                        continue

                    # Flag Tor ports from non-Tor processes
                    if remote_port in self._TOR_PORTS:
                        if not any(kw in proc.lower() for kw in ("shadowcypher", "tor", "torsocks")):
                            msg = (f"[!] Unexpected Tor port {remote_port}: "
                                   f"{local} → {remote} [{proc}]")
                            self._out(on_output, msg)
                            finding = {
                                "type": "SUSPICIOUS_CONN",
                                "local": local, "remote": remote,
                                "process": proc,
                                "reason": f"Tor port {remote_port} from non-Tor process",
                                "severity": "warning",
                            }
                            self._emit(finding)
                            findings.append(finding)
                            continue

                    # Flag unusual TCP ports
                    if proto.startswith("tcp") and remote_port not in self._ALLOWED_PORTS:
                        msg = (f"[TRAFFIC] Unusual TCP port {remote_port}: "
                               f"{local} → {remote} [{proc}]")
                        self._out(on_output, msg)
                        finding = {
                            "type": "SUSPICIOUS_CONN",
                            "local": local, "remote": remote,
                            "process": proc,
                            "reason": f"Non-standard TCP port {remote_port}",
                            "severity": "info",
                        }
                        self._emit(finding)
                        findings.append(finding)

                    # Flag unusual UDP
                    elif proto.startswith("udp") and remote_port not in {53, 67, 68, 123, 5353, 1900}:
                        msg = (f"[TRAFFIC] Unusual UDP port {remote_port}: "
                               f"{remote} [{proc}]")
                        self._out(on_output, msg)
                        finding = {
                            "type": "SUSPICIOUS_CONN",
                            "proto": "udp",
                            "local": local, "remote": remote,
                            "process": proc,
                            "reason": f"Unusual UDP port {remote_port}",
                            "severity": "info",
                        }
                        self._emit(finding)
                        findings.append(finding)

                if not findings:
                    self._out(on_output, "[TRAFFIC] Clean — no traffic anomalies detected.")

            except Exception as exc:
                self._out(on_output, f"[TRAFFIC ERROR] {exc}")
                logger.error("counter_intel", f"TRAFFIC_ANOMALY_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_TRAFFIC").start()

    # ── 7. Full Scan ─────────────────────────────────────────────────────────

    def run_full_scan(self, interface: str = "eth0",
                      on_output: Optional[Callable] = None,
                      on_complete: Optional[Callable] = None) -> None:
        """
        Run all six checks sequentially. Emits SCAN_COMPLETE on bus with
        total finding count and severity breakdown. Calls on_complete with
        the full list of findings.
        """
        def _worker():
            all_findings: List[dict] = []

            self._out(on_output, "=" * 62)
            self._out(on_output, " COUNTER-INTEL FULL SCAN INITIATED")
            self._out(on_output, "=" * 62)
            self.log(f"FULL_SCAN_START: iface={interface}")

            def _run_phase(label: str, fn: Callable, **kwargs):
                """Run one detection phase synchronously by blocking on an Event."""
                self._out(on_output, f"\n[+] Phase: {label}")
                done_ev = threading.Event()
                phase_results: List[dict] = []

                def _cb(results):
                    if isinstance(results, list):
                        phase_results.extend(results)
                    done_ev.set()

                fn(on_output=on_output, on_complete=_cb, **kwargs)
                done_ev.wait(timeout=90)
                all_findings.extend(phase_results)

            _run_phase("PROMISC INTERFACES", self.detect_promiscuous_interfaces)
            _run_phase("SSL INTERCEPTION",   self.detect_ssl_interception)
            _run_phase("DNS LEAK",           self.detect_dns_leak)
            _run_phase("TRAFFIC ANOMALIES",  self.scan_traffic_anomalies)
            _run_phase("ARP SPOOFING",       self.detect_arp_spoofing,
                       interface=interface, duration=15)
            _run_phase("ROGUE DHCP",         self.detect_rogue_dhcp,
                       interface=interface)

            # Summary
            sev: Dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
            for f in all_findings:
                bucket = f.get("severity", "info")
                sev[bucket] = sev.get(bucket, 0) + 1

            self._out(on_output, "\n" + "=" * 62)
            self._out(on_output,
                      f" SCAN COMPLETE — {len(all_findings)} findings  "
                      f"(CRITICAL:{sev['critical']} WARNING:{sev['warning']} INFO:{sev['info']})")
            self._out(on_output, "=" * 62)

            bus.publish("counter_intel", {
                "type": "SCAN_COMPLETE",
                "total": len(all_findings),
                "severity_breakdown": sev,
            })
            self.log(f"FULL_SCAN_COMPLETE: {len(all_findings)} findings")
            self._done(on_complete, all_findings)

        threading.Thread(target=_worker, daemon=True, name="CI_FullScan").start()

    # ── 8. OSINT Self-Audit ───────────────────────────────────────────────────

    def osint_self_audit(self, handle: Optional[str] = None,
                          on_output: Optional[Callable] = None,
                          on_complete: Optional[Callable] = None) -> None:
        """
        Self-exposure audit:
        - Public IP + Tor exit node check
        - HaveIBeenPwned breach check for the user's handle/email
        - DNS enumeration for handle-derived domains
        """
        def _worker():
            findings: List[dict] = []
            try:
                self._out(on_output, "[OSINT] Self-audit: what does the internet know about you?")
                self.log(f"OSINT_SELF_AUDIT: handle={handle}")

                # 1. Public IP
                public_ip = "UNKNOWN"
                try:
                    req = urllib.request.Request(
                        "https://api.ipify.org",
                        headers={"User-Agent": "ShadowCypher/1.0 counter-intel"},
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        public_ip = resp.read().decode().strip()
                    self._out(on_output, f"[OSINT] Public IP: {public_ip}")
                except Exception as exc:
                    self._out(on_output, f"[OSINT] IP lookup failed: {exc}")

                # 2. Is public IP a Tor exit node?
                if public_ip != "UNKNOWN":
                    try:
                        tor_url = (
                            f"https://check.torproject.org/cgi-bin/"
                            f"TorBulkExitList.py?ip={public_ip}"
                        )
                        req2 = urllib.request.Request(
                            tor_url,
                            headers={"User-Agent": "ShadowCypher/1.0 counter-intel"},
                        )
                        with urllib.request.urlopen(req2, timeout=10) as resp2:
                            exit_list = resp2.read().decode()
                        if public_ip in exit_list:
                            self._out(on_output,
                                      f"[!] {public_ip} is a Tor exit node — traffic analysis risk")
                        else:
                            self._out(on_output, f"[OSINT] {public_ip} is NOT a Tor exit node.")
                    except Exception as exc:
                        self._out(on_output, f"[OSINT] Tor exit check failed: {exc}")

                # 3. HaveIBeenPwned
                if handle:
                    email_or_user = handle.strip()
                    self._out(on_output, f"[OSINT] Checking HIBP for: {email_or_user}")
                    try:
                        encoded = urllib.parse.quote(email_or_user, safe="")
                        hibp_url = (
                            f"https://haveibeenpwned.com/api/v3/breachedaccount/{encoded}"
                            "?truncateResponse=false"
                        )
                        req = urllib.request.Request(
                            hibp_url,
                            headers={
                                "User-Agent": "ShadowCypher-OSINT/1.0",
                                "hibp-api-key": "",
                            },
                        )
                        try:
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                breaches = json.loads(resp.read())
                            names = [b.get("Name", "?") for b in breaches]
                            self._out(on_output,
                                      f"[!] HIBP: {email_or_user} found in "
                                      f"{len(breaches)} breach(es): {', '.join(names[:8])}")
                            finding = {
                                "type": "HIBP_BREACH",
                                "handle": email_or_user,
                                "breach_count": len(breaches),
                                "breaches": names[:10],
                                "severity": "warning",
                            }
                            self._emit(finding)
                            findings.append(finding)
                        except urllib.error.HTTPError as e:
                            if e.code == 404:
                                self._out(on_output,
                                          f"[OSINT] HIBP: {email_or_user} not found in any known breach.")
                            elif e.code == 401:
                                self._out(on_output,
                                          "[OSINT] HIBP API key required for email lookups "
                                          "(add hibp_api_key to settings).")
                            else:
                                self._out(on_output, f"[OSINT] HIBP HTTP {e.code}: {e.reason}")
                    except Exception as exc:
                        self._out(on_output, f"[OSINT] HIBP error: {exc}")

                    # 4. DNS handle enumeration
                    self._out(on_output, f"[OSINT] DNS enumeration for handle '{email_or_user}'...")
                    base = re.sub(r"[@\s]", "", email_or_user.lower().split("@")[0])
                    for tld in (".com", ".net", ".org", ".io", ".dev", ".site"):
                        domain = f"{base}{tld}"
                        try:
                            addrs = socket.getaddrinfo(domain, None)
                            ips = sorted({a[4][0] for a in addrs})
                            self._out(on_output, f"[OSINT] {domain} → {', '.join(ips)}")
                        except socket.gaierror:
                            pass  # not registered / not resolving

                if not findings:
                    self._out(on_output, "[OSINT] Self-audit complete — no critical exposures detected.")

            except Exception as exc:
                self._out(on_output, f"[OSINT ERROR] {exc}")
                logger.error("counter_intel", f"OSINT_SELF_AUDIT_ERROR: {exc}")
            finally:
                self._done(on_complete, findings)

        threading.Thread(target=_worker, daemon=True, name="CI_OSINT").start()
