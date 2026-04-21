"""
ShadowCypher Support Page — Legacy War-Room (Deprecated).
This page previously relied on IRC infrastructure that has been removed.
All communication is now handled by the Sovereign Chat page.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from shadowcypher.core.logger import logger


class SupportPage(Gtk.Box):
    """
    Legacy support page — redirects to SovereignChatPage.
    Kept as a shell to avoid import errors from app.py.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Center container
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        center.set_valign(Gtk.Align.CENTER)
        center.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Label()
        icon.set_markup("<span size='72000'>🛡</span>")
        center.pack_start(icon, False, False, 0)

        title = Gtk.Label()
        title.set_markup(
            "<span size='x-large' weight='800' color='#3b82f6'>"
            "SOVEREIGN COMMUNICATION</span>"
        )
        center.pack_start(title, False, False, 0)

        desc = Gtk.Label()
        desc.set_markup(
            "<span color='#64748b'>"
            "The legacy IRC-based War-Room has been replaced by the\n"
            "native <b>Sovereign Chat</b> system.\n\n"
            "Navigate to the <b>Chat</b> tab for secure, encrypted communication.\n"
            "WebSocket-based • AES-256-GCM • Multi-room • Zero IRC dependencies"
            "</span>"
        )
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_line_wrap(True)
        desc.set_max_width_chars(60)
        center.pack_start(desc, False, False, 0)

        self.pack_start(center, True, True, 0)
        logger.info("support", "Legacy SupportPage loaded — redirecting to Sovereign Chat")
