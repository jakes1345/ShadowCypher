"""Active Directory / enterprise network recon page."""
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from gi.repository import Gtk

class AdPage(BasePage):
    def __init__(self):
        super().__init__("🏰 Enterprise Network")

        self.pod_recon = DataPod("Recon level", "1", "cyan")
        self.pod_trust = DataPod("Trust health", "Secure", "violet")
        self.pod_kerb = DataPod("Kerberos", "Normal", "amber")

        self.metric_strip.pack_start(self.pod_recon, True, True, 0)
        self.metric_strip.pack_start(self.pod_trust, True, True, 0)
        self.metric_strip.pack_start(self.pod_kerb, True, True, 0)

        self._build_tactical_interface()

    def _build_tactical_interface(self):
        deck = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)

        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("Target IP or domain")
        deck.pack_start(self.target_entry, False, False, 0)

        btn = self.make_action_btn("⚡ Start Recon", self._on_mission)
        deck.pack_start(btn, False, False, 0)

        self.workspace.pack_start(deck, True, True, 0)

    def _on_mission(self, btn):
        target = self.target_entry.get_text()
        self.run_mission(f"Enterprise network recon on {target}")

