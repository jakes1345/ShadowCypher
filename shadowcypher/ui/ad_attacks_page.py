import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from shadowcypher.modules.ad_attacks import ADAttacks
from shadowcypher.ui.base_page import BasePage


class ADAttacksPage(BasePage):
    def __init__(self):
        super().__init__("\U0001f4bb Active Directory (Impacket & Responder)")

        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        notebook = Gtk.Notebook()
        notebook.append_page(
            self._build_impacket_tab(), Gtk.Label(label="Impacket Tools")
        )
        notebook.append_page(self._build_responder_tab(), Gtk.Label(label="Responder"))
        self.main_pod.pack_start(notebook, False, False, 0)

        self.build_terminal()

        stop_box = Gtk.Box()
        stop_box.pack_start(self.build_stop_button(), False, False, 0)
        self.main_pod.pack_start(stop_box, False, False, 0)

    def _build_impacket_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Target IP:"), False, False, 0)
        self.imp_target = Gtk.Entry()
        self.imp_target.set_placeholder_text("192.168.1.100")
        self.imp_target.set_hexpand(True)
        row.pack_start(self.imp_target, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="Domain:"), False, False, 0)
        self.imp_domain = Gtk.Entry()
        self.imp_domain.set_placeholder_text("CORP")
        row2.pack_start(self.imp_domain, True, True, 0)

        row2.pack_start(Gtk.Label(label="User:"), False, False, 0)
        self.imp_user = Gtk.Entry()
        self.imp_user.set_placeholder_text("Administrator")
        row2.pack_start(self.imp_user, True, True, 0)
        box.pack_start(row2, False, False, 0)

        row3 = Gtk.Box(spacing=8)
        row3.pack_start(Gtk.Label(label="Password:"), False, False, 0)
        self.imp_pass = Gtk.Entry()
        self.imp_pass.set_placeholder_text("Password123")
        self.imp_pass.set_visibility(False)
        row3.pack_start(self.imp_pass, True, True, 0)

        row3.pack_start(Gtk.Label(label="Hashes:"), False, False, 0)
        self.imp_hash = Gtk.Entry()
        self.imp_hash.set_placeholder_text("LM:NT")
        row3.pack_start(self.imp_hash, True, True, 0)
        box.pack_start(row3, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(
            self.make_action_btn("\U0001f528 PSExec", self._on_psexec, "danger-btn"),
            False,
            False,
            0,
        )
        btn_row.pack_start(
            self.make_action_btn("\U0001f4be SecretsDump", self._on_secretsdump),
            False,
            False,
            0,
        )
        box.pack_start(btn_row, False, False, 0)

        return box

    def _build_responder_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label="Interface:"), False, False, 0)
        self.resp_iface = Gtk.Entry()
        self.resp_iface.set_text("eth0")
        row.pack_start(self.resp_iface, False, False, 0)

        self.resp_analyze = Gtk.CheckButton(label="Analyze Mode Only (-A)")
        row.pack_start(self.resp_analyze, False, False, 0)

        self.resp_wpad = Gtk.CheckButton(label="Enable WPAD")
        row.pack_start(self.resp_wpad, False, False, 0)
        box.pack_start(row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        btn_row.pack_start(
            self.make_action_btn(
                "\U0001f310 Start Responder", self._on_responder, "danger-btn"
            ),
            False,
            False,
            0,
        )
        box.pack_start(btn_row, False, False, 0)

        return box

    def _on_psexec(self, btn):
        target = self.imp_target.get_text().strip()
        user = self.imp_user.get_text().strip()
        domain = self.imp_domain.get_text().strip()
        password = self.imp_pass.get_text().strip()
        hashes = self.imp_hash.get_text().strip()
        self.clear_output(f"Launching PSExec against {target}...\n\n")
        self.run_job(
            ADAttacks.impacket_psexec(
                target,
                user,
                password,
                domain,
                hashes,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )

    def _on_secretsdump(self, btn):
        target = self.imp_target.get_text().strip()
        user = self.imp_user.get_text().strip()
        domain = self.imp_domain.get_text().strip()
        password = self.imp_pass.get_text().strip()
        hashes = self.imp_hash.get_text().strip()
        self.clear_output(f"Launching SecretsDump against {target}...\n\n")
        self.run_job(
            ADAttacks.impacket_secretsdump(
                target,
                user,
                password,
                domain,
                hashes,
                use_vss=False,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )

    def _on_responder(self, btn):
        iface = self.resp_iface.get_text().strip()
        analyze = self.resp_analyze.get_active()
        wpad = self.resp_wpad.get_active()
        self.clear_output(f"Launching Responder on {iface}...\n\n")
        self.run_job(
            ADAttacks.run_responder(
                iface,
                analyze_only=analyze,
                wpad=wpad,
                on_output=self.on_output,
                on_complete=self.on_complete,
            )
        )
