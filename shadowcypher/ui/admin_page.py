"""Admin UI Extension — Embedded directly into ShadowCypher if Master Keys are present."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
import base64
import os

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.config import config


class AdminPage(BasePage):
    """The God-Mode tab. Only visible via asymmetric private key presence."""

    def __init__(self):
        super().__init__("\U0001f5dd ADMIN_MASTER_CONTROL")

        from shadowcypher.ui.components import DataPod
        
        # 1. Populate Metrics (Mainframe Status)
        self.pod_uptime = DataPod("CITADEL_UPTIME", "0:00:00", "cyan")
        self.pod_crypt = DataPod("CRYPT_LINK", "ACTIVE", "violet")
        self.pod_auth = DataPod("MASTER_AUTH", "ROOT", "amber")
        
        self.metric_strip.pack_start(self.pod_uptime, True, True, 0)
        self.metric_strip.pack_start(self.pod_crypt, True, True, 0)
        self.metric_strip.pack_start(self.pod_auth, True, True, 0)

        # ── 1. Ticket Decryption Box ──
        frm_decrypt = Gtk.Frame(label="Ticket Decryption Matrix (RSA-OAEP)")
        box_dec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box_dec.set_margin_start(10)
        box_dec.set_margin_end(10)
        box_dec.set_margin_top(10)
        box_dec.set_margin_bottom(10)

        lbl_in = Gtk.Label(label="Paste the user's Encrypted Ticket (Base64) below:")
        lbl_in.set_halign(Gtk.Align.START)
        box_dec.pack_start(lbl_in, False, False, 0)

        self.buf_in = Gtk.TextBuffer()
        tv_in = Gtk.TextView(buffer=self.buf_in)
        tv_in.set_wrap_mode(Gtk.WrapMode.CHAR)
        tv_in.get_style_context().add_class("terminal-view")
        scroll_in = Gtk.ScrolledWindow()
        scroll_in.set_min_content_height(120)
        scroll_in.add(tv_in)
        box_dec.pack_start(scroll_in, True, True, 0)

        btn_dec = Gtk.Button(label="\U0001f5dd Execute Neural Decryption")
        btn_dec.get_style_context().add_class("danger-btn")
        btn_dec.connect("clicked", self._on_decrypt)
        box_dec.pack_start(btn_dec, False, False, 0)

        frm_decrypt.add(box_dec)
        self.workspace.pack_start(frm_decrypt, True, True, 0)

        # Output terminal for Admin tools
        self.build_terminal()

        # ── 4. License Generation Box ──
        frm_gen = Gtk.Frame(label="AES-256 License Generator")
        box_gen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box_gen.set_margin_start(10)
        box_gen.set_margin_end(10)
        box_gen.set_margin_top(10)
        box_gen.set_margin_bottom(10)

        btn_gen = Gtk.Button(label="\u2699 Forge New License Key")
        btn_gen.get_style_context().add_class("suggested-action")
        btn_gen.connect("clicked", self._on_generate)
        box_gen.pack_start(btn_gen, False, False, 0)

        frm_gen.add(box_gen)
        self.workspace.pack_start(frm_gen, False, False, 0)

        # ── Timers ──
        GLib.timeout_add(1000, self._tick)

    def _tick(self):
        """Update live telemetry."""
        from shadowcypher.core.hub import hub
        summary = hub.get_tactical_summary()
        self.pod_uptime.set_value(summary["uptime"])
        return True

    def _on_decrypt(self, btn):
        bounds = self.buf_in.get_bounds()
        b64_ticket = self.buf_in.get_text(bounds[0], bounds[1], True).strip()
        if not b64_ticket:
            return

        try:
            self.clear_output("Locating Offline Master Private Key...\n")
            from shadowcypher.core.identity import identity

            if not identity.is_admin:
                self.on_output("[DENIED] This machine is not the admin node.\n")
                return

            with open(
                os.path.join(config.project_root, "admin_private.pem"), "rb"
            ) as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None
                )

            self.on_output(
                "Key successfully mounted into RAM. Reversing cipher block...\n\n"
            )

            ciphertext = base64.b64decode(b64_ticket)
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            self.on_output(
                f"══════ DECRYPTED MESSAGE ══════\n{plaintext.decode()}\n═══════════════════════════════\n"
            )

        except Exception as e:
            self.on_output(
                f"\n[FATAL ERROR] Decryption failed: {str(e)}\nEnsure you pasted the correct Base64 string.\n"
            )

    def _on_generate(self, btn):
        key = Fernet.generate_key()
        self.clear_output(
            f"====================================\n"
            f"   SHADOWCYPHER LICENSE GENERATOR   \n"
            f"====================================\n\n"
            f"[+] NEW LICENSE KEY FORGED:\n"
            f"\n{key.decode()}\n\n"
            f"Send this exact string to the user to unlock their arsenal."
        )
