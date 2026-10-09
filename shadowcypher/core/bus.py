"""
ShadowBus — The Apex Event Backbone.
Decouples Core modules (Kairos, Hub, Orchestrator) to prevent circular imports.
"""

import asyncio
import threading
from typing import Any, Callable, Dict, List

from shadowcypher.core.logger import logger


class ShadowBus:
    """Thread-safe, async-aware event backbone for the ShadowCypher suite."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Thread-safe subscription to event channels."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def publish(self, event_type: str, data: Any) -> None:
        """Broadcasts an event to all registered listeners."""
        with self._lock:
            listeners = self._listeners.get(event_type, []).copy()

        if not listeners:
            return

        for callback in listeners:
            try:
                self._dispatch(callback, data)
            except Exception as e:
                logger.error("bus", f"DISPATCH_FAILURE ({event_type}): {e}")

    def _dispatch(self, callback: Callable, data: Any) -> None:
        if asyncio.iscoroutinefunction(callback):
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(callback(data), loop)
            except RuntimeError:
                threading.Thread(target=lambda: asyncio.run(callback(data)), daemon=True).start()
        else:
            callback(data)

# Global Backbone Interface
bus = ShadowBus()
