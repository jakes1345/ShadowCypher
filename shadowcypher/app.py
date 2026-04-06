import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
import sys, os

from shadowcypher.ui.themes import get_theme
from shadowcypher.core.logger import logger

class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="ShadowCypher | MISSION_COMMAND")
        self.set_default_size(1400, 950)
        
        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._main_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self._main_grid)
        
        self._sidebar = self._build_sidebar()
        self._main_grid.pack_start(self._sidebar, False, False, 0)
        
        self._page_container = Gtk.Stack()
        self._main_grid.pack_start(self._page_container, True, True, 0)
        self._page_registry = {}

        self._switch_to_page("Operational Overview")
        self.show_all()

    def _build_sidebar(self):
        import platform
        current_os = platform.system()
        
        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")
        pages = [
            "\U0001f4ca Operational Overview", "\U0001f916 Tactical Swarm AI", "\U0001f4e1 Signal Recon",
            "\U0001f4a3 Offensive Exploit", "\U0001f50e Vulnerability Pulse", "\U0001f310 Stealth Network",
            "\U0001f50d Digital Analysis", "\U0001f4ad OSINT Intelligence", "\U0001f511 Credential Hub",
            "\U0001f6e1 Firewall Defense", "\U0001f4f6 Wireless Signals", "\U0001f4bb System Control",
            "\U0001f4e7 Network Support & Ticketing"
        ]
        
        linux_only_modules = ["Firewall Defense", "Wireless Signals"]
        
        for name in pages:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=name, xalign=0)
            
            clean_name = name.split(" ", 1)[1]
            if current_os != "Linux" and clean_name in linux_only_modules:
                lbl.set_label(f"[{current_os} UNSUPPORTED]\n{name}")
                lbl.set_sensitive(False)
                row.set_sensitive(False)
                
            row.add(lbl)
            row.set_name(clean_name)
            sidebar.add(row)
        sidebar.connect("row-activated", self._on_sidebar_selected)
        return sidebar

    def _on_sidebar_selected(self, listbox, row):
        name = row.get_name()
        if not name:
            name = row.get_child().get_text().split(" ", 1)[1]
        self._switch_to_page(name)

    def _switch_to_page(self, name):
        if name not in self._page_registry:
            try:
                if name == "Operational Overview":
                    from shadowcypher.ui.dashboard import DashboardPage
                    self._page_registry[name] = DashboardPage()
                elif name == "Tactical Swarm AI":
                    from shadowcypher.ui.ai_page import AIPage
                    self._page_registry[name] = AIPage()
                elif name == "Signal Recon":
                    from shadowcypher.ui.recon_page import ReconPage
                    self._page_registry[name] = ReconPage()
                elif name == "Offensive Exploit":
                    from shadowcypher.ui.exploit_page import ExploitPage
                    self._page_registry[name] = ExploitPage()
                elif name == "Vulnerability Pulse":
                    from shadowcypher.ui.vuln_page import VulnScannerPage
                    self._page_registry[name] = VulnScannerPage()
                elif name == "Stealth Network":
                    from shadowcypher.ui.network_page import NetworkPage
                    self._page_registry[name] = NetworkPage()
                elif name == "Digital Analysis":
                    from shadowcypher.ui.forensics_page import ForensicsPage
                    self._page_registry[name] = ForensicsPage()
                elif name == "OSINT Intelligence":
                    from shadowcypher.ui.osint_page import OSINTPage
                    self._page_registry[name] = OSINTPage()
                elif name == "Credential Hub":
                    from shadowcypher.ui.credentials_page import CredentialsPage
                    self._page_registry[name] = CredentialsPage()
                elif name == "Firewall Defense":
                    from shadowcypher.ui.firewall_page import FirewallPage
                    self._page_registry[name] = FirewallPage()
                elif name == "Wireless Signals":
                    from shadowcypher.ui.wireless_page import WirelessPage
                    self._page_registry[name] = WirelessPage()
                elif name == "System Control":
                    from shadowcypher.ui.session_page import SessionPage
                    self._page_registry[name] = SessionPage()
                elif name == "Network Support & Ticketing":
                    from shadowcypher.ui.support_page import SupportPage
                    self._page_registry[name] = SupportPage()
                self._page_container.add_named(self._page_registry[name], name)
                
                # Dynamic God-Mode tab injection (if Admin Private Key is physically present)
                import os
                from shadowcypher.core.config import config
                if os.path.exists(os.path.join(config.project_root, "admin_private.pem")) and "Admin Console" not in self._page_registry:
                    from shadowcypher.ui.admin_page import AdminPage
                    self._page_registry["Admin Console"] = AdminPage()
                    self._page_container.add_named(self._page_registry["Admin Console"], "Admin Console")
                    # Add to listbox visually
                    row_add = Gtk.ListBoxRow()
                    lbl_add = Gtk.Label(label="\U0001f5dd Admin Console")
                    lbl_add.set_halign(Gtk.Align.START)
                    row_add.add(lbl_add)
                    row_add.set_name("Admin Console")
                    self._sidebar.add(row_add)
                    
                self._page_container.show_all()
            except Exception as e:
                logger.error("ui", f"Failed to load page '{name}': {e}")
                lbl = Gtk.Label(label=f"[SYSTEM] ERROR_ACCESSING_{name.upper()}: {str(e)}")
                self._page_container.add_named(lbl, name)
                self._page_container.show_all()
        self._page_container.set_visible_child_name(name)

class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.shadow.cypher")
    def do_activate(self):
        self._window = ShadowCypherWindow(self)

if __name__ == "__main__":
    app = ShadowCypherApp()
    app.run(sys.argv)
