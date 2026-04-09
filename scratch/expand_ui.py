
import os

UI_DIR = "/home/jack/ShadowCypher/shadowcypher/ui"

MODULE_MAPPING = {
    "phishing_page": ("SOCIAL_ENGINEERING", "\U0001f3a3"),
    "osint_page": ("OPEN_SOURCE_INTEL", "\U0001f575"),
    "wireless_page": ("SIGNAL_INTELLIGENCE", "\U0001f4f6"),
    "ad_page": ("ENTERPRISE_NETWORK", "\U0001f3f0"),
    "forensics_page": ("POST_EXPLOITATION", "\U0001f52c"),
    "payload_page": ("ARSENAL_FORGE", "\U0001f528")
}

TEMPLATE = """\"\"\"APEX UI: {name} V3.0\"\"\"
from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from gi.repository import Gtk

class {class_name}(BasePage):
    def __init__(self):
        super().__init__("{icon} {label}")
        self._build_tactical_interface()

    def _build_tactical_interface(self):
        # 1. Metric Strip
        strip = Gtk.Box(spacing=15)
        strip.pack_start(DataPod("PULSE", "ACTIVE", "cyan"), True, True, 0)
        strip.pack_start(DataPod("LOAD", "0.0%", "violet"), True, True, 0)
        strip.set_margin_bottom(20)
        self.workspace.pack_start(strip, False, False, 0)

        # 2. Control Pod
        pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        pod.get_style_context().add_class("card")
        pod.set_margin_top(15); pod.set_margin_bottom(15); pod.set_margin_start(15); pod.set_margin_end(15)
        
        self.target_entry = Gtk.Entry(placeholder_text="MISSION_TARGET_SPEC")
        pod.pack_start(self.target_entry, False, False, 0)
        
        btn = self.make_action_btn("\u26a1 INITIATE_OPERATION", self._on_mission)
        pod.pack_start(btn, False, False, 0)
        
        self.workspace.pack_start(pod, True, True, 0)

    def _on_mission(self, btn):
        target = self.target_entry.get_text()
        self.run_mission(f"Perform {label} on target: {{target}}")

"""

for mod, (label, icon) in MODULE_MAPPING.items():
    class_name = "".join([x.capitalize() for x in mod.split("_")])
    path = os.path.join(UI_DIR, f"{mod}.py")
    if os.path.exists(path): continue
    
    content = TEMPLATE.format(
        name=label,
        class_name=class_name,
        icon=icon,
        label=label
    )
    with open(path, "w") as f:
        f.write(content)
    print(f"SCAFFOLDED: {path}")
