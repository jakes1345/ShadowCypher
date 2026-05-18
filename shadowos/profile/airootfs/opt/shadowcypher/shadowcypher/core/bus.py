"""
ShadowBus — The Apex Event Backbone.
Decouples Core modules (Kairos, Hub, Orchestrator) to prevent circular imports.
"""

import threading
import asyncio
from typing import Callable, List, Dict, Any, Union
from shadowcypher.core.logger import logger

class ShadowBus:
    """Thread-safe, Async-aware Event Backbone for the ShadowCypher suite."""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable):
        """Thread-safe subscription to tactical event channels."""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def publish(self, event_type: str, data: Any, ui_thread: bool = False):
        """
        Broadcasts an event to all registered listeners.
        Supports automatic async resolution and GLib UI proxying.
        """
        with self._lock:
            listeners = self._listeners.get(event_type, []).copy()
        
        if not listeners:
            return
        
        for callback in listeners:
            try:
                if ui_thread:
                    self._dispatch_ui(callback, data)
                else:
                    self._dispatch_standard(callback, data)
            except Exception as e:
                logger.error("bus", f"DISPATCH_FAILURE ({event_type}): {e}")

    def _dispatch_ui(self, callback: Callable, data: Any):
        """Proxies event delivery to the main GTK/GLib thread."""
        try:
            from gi.repository import GLib
            GLib.idle_add(callback, data)
        except (ImportError, ValueError, AttributeError):
            self._dispatch_standard(callback, data)

    def _dispatch_standard(self, callback: Callable, data: Any):
        """Handles standard and async callback execution."""
        if asyncio.iscoroutinefunction(callback):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(callback(data))
                else:
                    asyncio.run(callback(data))
            except Exception:
                # Handle cases where loop isn't available
                threading.Thread(target=lambda: asyncio.run(callback(data)), daemon=True).start()
        else:
            callback(data)

# Global Backbone Interface
bus = ShadowBus()
