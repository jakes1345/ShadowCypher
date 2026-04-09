"""
ShadowBus — The Apex Event Backbone.
Decouples Core modules (Kairos, Hub, Orchestrator) to prevent circular imports.
"""

from typing import Callable, List, Dict
from shadowcypher.core.logger import logger
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib

class ShadowBus:
    """Lightweight Event Bus with thread-safe UI proxies."""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def publish(self, event_type: str, data: any, ui_thread: bool = False):
        """
        Publishes an event. 
        If ui_thread=True, ensures the callback runs in the main GLib loop.
        """
        if event_type not in self._listeners: return
        
        for callback in self._listeners[event_type]:
            try:
                if ui_thread:
                    GLib.idle_add(callback, data)
                else:
                    callback(data)
            except Exception as e:
                logger.error("bus", f"Event delivery failed for {event_type}: {e}")

# Global Backbone
bus = ShadowBus()
