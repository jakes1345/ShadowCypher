"""Payload forge page — generate and obfuscate payloads for authorized testing."""
from gi.repository import Gtk

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class CraftPage(BasePage):
    def __init__(self):
        super().__init__("🔨 Payload Forge")

        self.pod_pulse = DataPod("Status", "Active", "cyan")
        self.pod_depth = DataPod("Obfuscation", "Level 3", "violet")
        self.pod_entropy = DataPod("Entropy", "High", "amber")

        self.metric_strip.pack_start(self.pod_pulse, True, True, 0)
        self.metric_strip.pack_start(self.pod_depth, True, True, 0)
        self.metric_strip.pack_start(self.pod_entropy, True, True, 0)

        self._build_tactical_interface()

    def _build_tactical_interface(self):
        # Control Deck
        deck = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        row1 = Gtk.Box(spacing=10)
        row1.pack_start(Gtk.Label(label="Payload Type:"), False, False, 0)
        self.payload_type = Gtk.ComboBoxText()
        self.payload_type.append("elf", "Evasive ELF (x64/Shikata)")
        self.payload_type.append("ps1", "Stealth PowerShell (AMSI Bypass)")
        self.payload_type.append("py_xor", "Obfuscated Python (XOR)")
        self.payload_type.append("py_c2", "Encrypted C2 Agent (Fernet)")
        self.payload_type.set_active(0)
        row1.pack_start(self.payload_type, True, True, 0)
        deck.pack_start(row1, False, False, 0)

        row2 = Gtk.Box(spacing=10)
        self.lhost_entry = Gtk.Entry()
        self.lhost_entry.set_placeholder_text("LHOST (e.g. 10.0.2.15)")
        self.lhost_entry.set_text("10.0.2.15") # Ideally from config
        row2.pack_start(self.lhost_entry, True, True, 0)

        self.lport_entry = Gtk.Entry()
        self.lport_entry.set_placeholder_text("LPORT")
        self.lport_entry.set_text("4444")
        row2.pack_start(self.lport_entry, False, False, 0)
        deck.pack_start(row2, False, False, 0)

        btn = self.make_action_btn("⚡ Generate", self._on_forge)
        deck.pack_start(btn, False, False, 0)

        self.workspace.pack_start(deck, True, True, 0)

    def _on_forge(self, btn):
        from gi.repository import GLib

        from shadowcypher.modules.craft_factory import CraftFactory

        ptype = self.payload_type.get_active_id()
        lhost = self.lhost_entry.get_text().strip()
        lport = self.lport_entry.get_text().strip()

        self.terminal.clear()
        self.terminal.log(f"Generating {ptype} payload → {lhost}:{lport}", "SYSTEM")

        def _on_out(line):
            GLib.idle_add(self.terminal.log, line.strip(), "FORGE")

        if ptype == "elf":
            CraftFactory.generate_evasive_elf(lhost, lport, on_output=_on_out)
        elif ptype == "ps1":
            path = CraftFactory.generate_stealth_powershell(lhost, lport, on_output=_on_out)
            self.terminal.log(f"Saved: {path}", "SUCCESS")
        elif ptype == "py_xor":
            path = CraftFactory.generate_obfuscated_python(lhost, lport)
            self.terminal.log(f"Saved: {path}", "SUCCESS")
        elif ptype == "py_c2":
            b64 = CraftFactory.generate_stealth_c2_python(lhost, lport)
            self.terminal.log("Encrypted agent (base64):", "SUCCESS")
            self.terminal.log(b64, "DATA")

