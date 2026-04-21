"""APEX UI: ENTERPRISE_NETWORK V3.0"""
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from gi.repository import Gtk

class AdPage(BasePage):
    def __init__(self):
        super().__init__("🏰 ENTERPRISE_NETWORK")

        # 1. Populate Metric Strip
        self.pod_recon = DataPod("DOMAIN_RECON", "LVL_1", "cyan")
        self.pod_trust = DataPod("TRUST_HEALTH", "SECURE", "violet")
        self.pod_kerb = DataPod("KERBEROS_VIBE", "NOMINAL", "amber")

        self.metric_strip.pack_start(self.pod_recon, True, True, 0)
        self.metric_strip.pack_start(self.pod_trust, True, True, 0)
        self.metric_strip.pack_start(self.pod_kerb, True, True, 0)

        self._build_tactical_interface()

    def _build_tactical_interface(self):
        # Mission Deck
        deck = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text("MISSION_TARGET_SPEC (e.g. GATEWAY_IP00)")
        deck.pack_start(self.target_entry, False, False, 0)
        
        btn = self.make_action_btn("⚡ INITIATE_DOMAIN_RECON", self._on_mission)
        deck.pack_start(btn, False, False, 0)
        
        self.workspace.pack_start(deck, True, True, 0)

    def _on_mission(self, btn):
        target = self.target_entry.get_text()
        self.run_mission(f"Perform ENTERPRISE_NETWORK on target: {target}")

