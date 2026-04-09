"""ShadowCypher Tactical AI Swarm — Global AI Resuscitation Build V13."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
from shadowcypher.ai.orchestrator import AIOrchestrator
from shadowcypher.core.logger import logger
import threading


from shadowcypher.ui.components import TacticalTerminal, TacticalHeader, DataPod
from shadowcypher.core.hub import hub
from shadowcypher.core.logger import logger

class AIPage(Gtk.Box):
    """Deep-Spectrum AI Hub. Multimodal + Context aware."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.attachments = []
        self._build_ui()

    def _build_ui(self):
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. Apex Header
        self.header = TacticalHeader("TENGU_DEEP_CHAT: MISSION_READY")
        self.main_pod.pack_start(self.header, False, False, 0)

        # 2. Terminal View
        self.terminal = TacticalTerminal(height=500)
        self.main_pod.pack_start(self.terminal, True, True, 0)

        # 4. Interaction Hub
        input_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Dashboard Controls (New)
        ctrl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.intensity_toggle = Gtk.CheckButton(label="HIGH_INTENSITY (METACHAIN)")
        self.intensity_toggle.set_tooltip_text("Enable AutoAgent's dynamic tool creation and Docker sandboxing.")
        ctrl_row.pack_start(self.intensity_toggle, False, False, 0)
        input_container.pack_start(ctrl_row, False, False, 0)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Attachment Bar
        self.attach_lbl = Gtk.Label(xalign=0)
        self.attach_lbl.set_markup("<span size='small' color='#94a3b8'>ATTACHMENTS: NONE</span>")
        input_container.pack_start(self.attach_lbl, False, False, 0)

        btn_attach = Gtk.Button()
        btn_attach.set_image(Gtk.Image.new_from_icon_name("mail-attachment", Gtk.IconSize.BUTTON))
        btn_attach.connect("clicked", self._on_attach_clicked)
        entry_row.pack_start(btn_attach, False, False, 0)

        self.msg_entry = Gtk.Entry()
        self.msg_entry.set_placeholder_text("SEND_INTEL_OR_COMMAND...")
        self.msg_entry.connect("activate", self._on_send_clicked)
        entry_row.pack_start(self.msg_entry, True, True, 0)

        btn_send = Gtk.Button(label="ENGAGE")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send_clicked)
        entry_row.pack_end(btn_send, False, False, 0)

        input_container.pack_start(entry_row, False, False, 0)
        self.main_pod.pack_start(input_container, False, False, 0)

    def _on_attach_clicked(self, btn):
        dialog = Gtk.FileChooserDialog(title="SELECT_MISSION_MEDIA", parent=None, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.attachments.append(path)
            self.attach_lbl.set_markup(f"<span size='small' color='#38bdf8'>ATTACHMENTS: {len(self.attachments)} ITEMS READY</span>")
        dialog.destroy()

    def _on_send_clicked(self, widget):
        msg = self.msg_entry.get_text().strip()
        if not msg and not self.attachments: return
        
        self.terminal.log(f"USER >> {msg}", "USER")
        if self.attachments:
            self.terminal.log(f"SENT_MEDIA: {self.attachments}", "SYSTEM")
            
        self.header.set_active(True)
        hub.orchestrator.execute_query_async(
            msg, 
            images=self.attachments,
            agent_role="commander",
            callback=lambda txt: self.terminal.log(txt, "TENGU"),
            # New Synthesis Injection
            on_complete=self._on_mission_finish,
            intensity="MAX" if self.intensity_toggle.get_active() else None
        )
        self.msg_entry.set_text("")
        self.attachments = []
        self.attach_lbl.set_markup("<span size='small' color='#94a3b8'>ATTACHMENTS: NONE</span>")

    def _on_mission_finish(self, res):
        self.header.set_active(False)
        self.terminal.log(res, "TENGU")
