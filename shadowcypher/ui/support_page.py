"""Support & Communications — Encrypted ticket system with file-based persistence."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from shadowcypher.ui.base_page import BasePage
import threading
import os
import json
import time
import base64
from datetime import datetime
from pathlib import Path
from shadowcypher.core.logger import logger


class SupportPage(BasePage):
    def __init__(self):
        super().__init__("\U0001f4e7 Secure Comm-Link")
        from shadowcypher.core.identity import identity
        from shadowcypher.core.config import config

        self._identity = identity
        self._tickets_dir = Path(config.project_root) / "tickets"
        self._tickets_dir.mkdir(exist_ok=True)

        conn_frame = Gtk.Frame(label="Operator Identity")
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        conn_box.set_margin_start(10)
        conn_box.set_margin_end(10)
        conn_box.set_margin_top(10)
        conn_box.set_margin_bottom(10)

        if identity.is_admin:
            lbl_info = Gtk.Label(
                label="You are the ADMIN NODE. Incoming tickets are decrypted here. Users see you as '\U0001f512 SHADOW_ADMIN'."
            )
        else:
            lbl_info = Gtk.Label(
                label="Send encrypted tickets to the developer. Messages are RSA-OAEP encrypted — only the admin's private key can decrypt them. Your IP is never transmitted."
            )
        lbl_info.set_line_wrap(True)
        conn_box.pack_start(lbl_info, False, False, 0)

        row1 = Gtk.Box(spacing=10)
        row1.pack_start(Gtk.Label(label="Your Handle:"), False, False, 0)
        self.entry_handle = Gtk.Entry()
        if identity.is_admin:
            self.entry_handle.set_text(identity.handle)
            self.entry_handle.set_sensitive(False)
        else:
            self.entry_handle.set_placeholder_text("Choose your operator alias...")
        row1.pack_start(self.entry_handle, True, True, 0)
        conn_box.pack_start(row1, False, False, 0)

        conn_frame.add(conn_box)
        self.pack_start(conn_frame, False, False, 10)

        chat_frame = Gtk.Frame(label="Secure Comm-Link")
        chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chat_box.set_margin_start(10)
        chat_box.set_margin_end(10)
        chat_box.set_margin_top(10)
        chat_box.set_margin_bottom(10)

        self.output_buffer = Gtk.TextBuffer()
        output_view = Gtk.TextView(buffer=self.output_buffer)
        output_view.set_editable(False)
        output_view.set_monospace(True)
        output_view.get_style_context().add_class("terminal-view")
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(output_view)
        chat_box.pack_start(scroll, True, True, 0)

        in_row = Gtk.Box(spacing=10)
        self.entry_msg = Gtk.Entry()
        self.entry_msg.set_placeholder_text("Type message... (encrypted before save)")
        self.entry_msg.set_hexpand(True)
        self.entry_msg.connect("activate", self._on_send)
        in_row.pack_start(self.entry_msg, True, True, 0)

        btn_send = Gtk.Button(label="Transmit")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send)
        in_row.pack_start(btn_send, False, False, 0)
        chat_box.pack_start(in_row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_export = Gtk.Button(label="\U0001f4cb Copy Last Ticket")
        btn_export.connect("clicked", self._on_copy_ticket)
        btn_row.pack_start(btn_export, False, False, 0)

        btn_load = Gtk.Button(label="\U0001f4c2 Load Ticket File")
        btn_load.connect("clicked", self._on_load_ticket)
        btn_row.pack_start(btn_load, False, False, 0)

        if identity.is_admin:
            btn_decrypt = Gtk.Button(label="\U0001f5dd Decrypt Loaded Ticket")
            btn_decrypt.get_style_context().add_class("danger-btn")
            btn_decrypt.connect("clicked", self._on_decrypt_ticket)
            btn_row.pack_start(btn_decrypt, False, False, 0)

        chat_box.pack_start(btn_row, False, False, 5)

        chat_frame.add(chat_box)
        self.pack_start(chat_frame, True, True, 10)

        self._last_ticket_b64 = None
        self._loaded_ticket_b64 = None

        self._append_sys("System initialized. All messages are end-to-end encrypted.")
        self._append_sys(
            f"Role: {identity.role.upper()} | Key Fingerprint: {identity.pubkey_fingerprint[:16]}..."
        )
        self._load_ticket_history()

    def _append_sys(self, msg):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, f"[SYSTEM] {msg}\n")

    def _append_msg(self, handle, msg):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, f"[{handle}] {msg}\n")

    def _on_send(self, widget):
        handle = self.entry_handle.get_text().strip()
        msg = self.entry_msg.get_text().strip()

        if not handle:
            self._append_sys("ERROR: Set your operator handle first.")
            return
        if not msg:
            return

        self._append_msg(handle, msg)
        self.entry_msg.set_text("")
        threading.Thread(
            target=self._encrypt_and_save, args=(handle, msg), daemon=True
        ).start()

    def _encrypt_and_save(self, handle, msg):
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization
        from shadowcypher.core.config import config

        pub_key_path = os.path.join(
            config.project_root, "shadowcypher", "core", "admin_public.pem"
        )

        if not os.path.exists(pub_key_path):
            GLib.idle_add(self._append_sys, "CRITICAL: Admin public key not found.")
            return

        try:
            with open(pub_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())

            ciphertext = public_key.encrypt(
                msg.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            b64_cipher = base64.b64encode(ciphertext).decode()
            self._last_ticket_b64 = b64_cipher

            ticket = {
                "handle": handle,
                "timestamp": datetime.now().isoformat(),
                "encrypted_message": b64_cipher,
                "role": self._identity.role,
            }

            ts = int(time.time())
            ticket_path = self._tickets_dir / f"ticket_{ts}.json"
            with open(ticket_path, "w") as f:
                json.dump(ticket, f, indent=2)

            GLib.idle_add(
                self._append_sys, f"Ticket encrypted and saved: {ticket_path.name}"
            )
            GLib.idle_add(self._append_sys, f"Cipher: {b64_cipher[:50]}...")

        except Exception as e:
            GLib.idle_add(self._append_sys, f"Encryption failed: {e}")

    def _on_copy_ticket(self, btn):
        if not self._last_ticket_b64:
            self._append_sys("No ticket to copy. Send a message first.")
            return
        clipboard = Gtk.Clipboard.get_default(self.get_display())
        clipboard.set_text(self._last_ticket_b64, -1)
        self._append_sys("Encrypted ticket copied to clipboard.")

    def _on_load_ticket(self, btn):
        dialog = Gtk.FileChooserDialog(
            title="Load Encrypted Ticket",
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        filt = Gtk.FileFilter()
        filt.set_name("Ticket files")
        filt.add_pattern("ticket_*.json")
        filt.add_pattern("*.json")
        dialog.add_filter(filt)
        dialog.set_current_folder(str(self._tickets_dir))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            try:
                with open(path, "r") as f:
                    ticket = json.load(f)
                handle = ticket.get("handle", "UNKNOWN")
                ts = ticket.get("timestamp", "?")
                self._loaded_ticket_b64 = ticket.get("encrypted_message", "")
                self._append_sys(f"Loaded ticket from {handle} ({ts})")
                self._append_sys(f"Cipher: {self._loaded_ticket_b64[:50]}...")
            except Exception as e:
                self._append_sys(f"Failed to load ticket: {e}")
        dialog.destroy()

    def _on_decrypt_ticket(self, btn):
        if not self._loaded_ticket_b64:
            self._append_sys("Load a ticket file first.")
            return

        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes, serialization
        from shadowcypher.core.config import config

        priv_path = os.path.join(config.project_root, "admin_private.pem")
        if not os.path.exists(priv_path):
            self._append_sys("DENIED: Admin private key not found on this system.")
            return

        try:
            with open(priv_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )

            ciphertext = base64.b64decode(self._loaded_ticket_b64)
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            self._append_sys("══════ DECRYPTED ══════")
            self._append_msg("\U0001f513 PLAINTEXT", plaintext.decode("utf-8"))
            self._append_sys("═══════════════════════")
        except Exception as e:
            self._append_sys(f"Decryption failed: {e}")

    def _load_ticket_history(self):
        tickets = sorted(self._tickets_dir.glob("ticket_*.json"))
        if not tickets:
            return
        self._append_sys(f"Found {len(tickets)} ticket(s) in archive.")
        for tp in tickets[-5:]:
            try:
                with open(tp, "r") as f:
                    t = json.load(f)
                handle = t.get("handle", "?")
                ts = t.get("timestamp", "?")
                role = t.get("role", "operator")
                self._append_sys(f"  [{role.upper()}] {handle} @ {ts}")
            except Exception:
                pass
