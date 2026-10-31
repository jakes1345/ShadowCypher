"""
ShadowCypher Chaos Engine — UDP flood stress/simulation module.
Used by the CI test suite; also callable from the orchestrator for
controlled network-load testing within authorized scope.
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Optional


class ChaosEngine:
    """
    Lightweight UDP flood engine for authorized stress testing.
    All network operations require explicit start/stop lifecycle.
    """

    def __init__(self) -> None:
        self._stop_event: threading.Event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start_udp_flood(
        self,
        target: str,
        port: int,
        duration: float = 0,
        threads: int = 1,
        payload_size: int = 1024,
    ) -> None:
        """
        Begin UDP packet flood toward target:port.

        Args:
            target: Destination IP/hostname (must be in authorized CIDR).
            port: Destination UDP port.
            duration: Seconds to run (0 = run until stop() is called).
            threads: Number of parallel flood threads.
            payload_size: Bytes per packet.
        """
        self._stop_event.clear()
        self._threads.clear()

        payload = b"X" * payload_size
        deadline: Optional[float] = time.time() + duration if duration > 0 else None

        def _worker() -> None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                while not self._stop_event.is_set():
                    if deadline is not None and time.time() >= deadline:
                        break
                    try:
                        sock.sendto(payload, (target, port))
                    except Exception:
                        pass
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
                self._stop_event.set()

        for _ in range(max(1, threads)):
            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """Signal all flood threads to halt."""
        self._stop_event.set()

    def is_running(self) -> bool:
        return any(t.is_alive() for t in self._threads)
