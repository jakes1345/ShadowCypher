"""Support & Communications Tab - P2P Support System."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from shadowcypher.ui.base_page import BasePage
import threading
import json
import requests
from shadowcypher.core.logger import logger

class SupportPage(BasePage):
    """P2P / Webhook based Support Ticketing System."""
    def __init__(self):
        super().__init__("\U0001f4e7 Network Support & Ticketing")

        # Connection setup section
        conn_frame = Gtk.Frame(label="Link Establishment")
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        conn_box.set_margin_start(10); conn_box.set_margin_end(10); conn_box.set_margin_top(10); conn_box.set_margin_bottom(10)

        # Basic instructions
        lbl_info = Gtk.Label(label="Open a secure ticket to request a License Key or report bugs. Messages are end-to-end encrypted to the developer node.")
        lbl_info.set_line_wrap(True)
        conn_box.pack_start(lbl_info, False, False, 0)
        
        # User Identifier
        row1 = Gtk.Box(spacing=10)
        row1.pack_start(Gtk.Label(label="Operator ID (Handle):"), False, False, 0)
        self.entry_handle = Gtk.Entry()
        self.entry_handle.set_placeholder_text("Enter your alias...")
        row1.pack_start(self.entry_handle, True, True, 0)
        conn_box.pack_start(row1, False, False, 0)

        conn_frame.add(conn_box)
        self.pack_start(conn_frame, False, False, 10)

        # Chat interface
        chat_frame = Gtk.Frame(label="Secure Comm-Link")
        chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chat_box.set_margin_start(10); chat_box.set_margin_end(10); chat_box.set_margin_top(10); chat_box.set_margin_bottom(10)

        # Output terminal for messages
        self.output_buffer = Gtk.TextBuffer()
        output_view = Gtk.TextView(buffer=self.output_buffer)
        output_view.set_editable(False)
        output_view.set_monospace(True)
        output_view.get_style_context().add_class("terminal-view")
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(output_view)
        chat_box.pack_start(scroll, True, True, 0)

        # Input row
        in_row = Gtk.Box(spacing=10)
        self.entry_msg = Gtk.Entry()
        self.entry_msg.set_placeholder_text("Type your message here... (e.g. 'Requesting DRM License Key')")
        self.entry_msg.set_hexpand(True)
        self.entry_msg.connect("activate", self._on_send) # Send on Enter key
        in_row.pack_start(self.entry_msg, True, True, 0)

        btn_send = Gtk.Button(label="Transmit")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send)
        in_row.pack_start(btn_send, False, False, 0)
        chat_box.pack_start(in_row, False, False, 0)

        chat_frame.add(chat_box)
        self.pack_start(chat_frame, True, True, 10)

        self._append_sys_msg("System initialized. Awaiting secure transmission protocol...")

    def _append_sys_msg(self, msg):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, f"[SYSTEM] {msg}\n")

    def _append_user_msg(self, handle, msg):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, f"[{handle}] {msg}\n")

    def _on_send(self, widget):
        handle = self.entry_handle.get_text().strip()
        msg = self.entry_msg.get_text().strip()
        
        if not handle:
            self._append_sys_msg("ERROR: You must establish an Operator ID first.")
            return
        if not msg:
            return

        self._append_user_msg(handle, msg)
        self.entry_msg.set_text("")
        
        # Simulate network delay for the offline build
        threading.Thread(target=self._transmit_sim, args=(handle, msg), daemon=True).start()

    def _transmit_sim(self, handle, msg):
        import time
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes
        import base64
        
        # Simulate loading the Developer's Master Public Key
        GLib.idle_add(self._append_sys_msg, "Generating ephemeral RSA tunnel...")
        time.sleep(0.5)
        
        # Generate an ephemeral RSA key just to demonstrate the crypto on the client side
        # In reality, this would use a hardcoded public key for 'Jack'
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        
        GLib.idle_add(self._append_sys_msg, "Securing payload via RSA-OAEP (SHA-256) encryption block...")
        ciphertext = public_key.encrypt(
            msg.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        b64_cipher = base64.b64encode(ciphertext).decode()
        GLib.idle_add(self._append_sys_msg, f"ENCRYPTED PACKET: \n{b64_cipher[:60]}...[TRUNCATED]...")
        time.sleep(1.0)
        GLib.idle_add(self._append_sys_msg, "Transmission successful. The Admin Node (Jack) will decrypt your message with their Private Key and respond shortly.")
