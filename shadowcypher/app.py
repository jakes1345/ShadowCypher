import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import sys, os, time

from shadowcypher.core.hub import hub
from shadowcypher.ui.themes import get_theme
from shadowcypher.core.logger import logger
from shadowcypher.core.security import StealthHoneypot
from shadowcypher.core.identity import identity

class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="SHADOWCYPHER_APEX")
        self.set_default_size(1580, 980)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        # 1. Apex HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("ShadowCypher")
        self.header.set_subtitle("\U0001f575\ufe0f APEX_MISSION_CONTROL")
        self.set_titlebar(self.header)

        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # 2. Apex Layout
        vbox_master = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_master)
        hbox_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vbox_master.pack_start(hbox_content, True, True, 0)

        self._sidebar = self._build_sidebar()
        hbox_content.pack_start(self._sidebar, False, False, 0)

        self._page_container = Gtk.Stack()
        self._page_container.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        hbox_content.pack_start(self._page_container, True, True, 0)

        # 3. Apex Footer (Synchronized with ShadowHub)
        self.footer = Gtk.ActionBar()
        self.system_status = Gtk.Label()
        self.footer.pack_start(self.system_status)

        self.uptime_status = Gtk.Label(label="IDLE")
        self.footer.pack_end(self.uptime_status)
        vbox_master.pack_start(self.footer, False, False, 0)

        self._page_registry = {}
        self._switch_to_page("Operational Overview")
        GLib.timeout_add(1000, self._tick_apex_telemetry)
        self.show_all()

    def _tick_apex_telemetry(self):
        """Global UI Synchronization with the ShadowHub Core."""
        summary = hub.get_tactical_summary()
        role = "ADMIN" if identity.is_admin else "OPERATOR"
        
        self.system_status.set_markup(
            f"<span color='#38bdf8'><b>[{role}]</b></span> | "
            f"<span color='#f87171'><b>[MISSIONS:{summary['active_missions']}]</b></span> | "
            f"<span color='#a855f7'><b>[APEX_CORE: ACTIVE]</b></span>"
        )
        self.uptime_status.set_text(f"UPTIME: {summary['uptime']}")
        return True

    def _build_sidebar(self):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_size_request(280, -1)
        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")

        pages = [
            ("---", "APEX_COMMAND"),
            ("\U0001f4ca", "Operational Overview"),
            ("\U0001f916", "Tactical Swarm AI"),
            ("---", "OFFENSIVE_ARSENAL"),
            ("\U0001f310", "Web Assault"),
            ("\U0001f4e1", "Signal Recon"),
            ("\u26a1", "Offensive Exploit"),
            ("\U0001f50e", "Vulnerability Pulse"),
        ]

        for icon, name in pages:
            row = Gtk.ListBoxRow()
            if icon == "---":
                lbl = Gtk.Label(label=f" {name}", xalign=0)
                lbl.get_style_context().add_class("sidebar-header")
                row.set_sensitive(False)
                row.add(lbl)
            else:
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
                hbox.set_margin_start(10)
                icon_lbl = Gtk.Label(label=icon)
                icon_lbl.get_style_context().add_class("cyan-text")
                name_lbl = Gtk.Label(label=name, xalign=0)
                hbox.pack_start(icon_lbl, False, False, 0)
                hbox.pack_start(name_lbl, True, True, 0)
                row.add(hbox)
                row.set_name(name)
            sidebar.add(row)

        sidebar.connect("row-activated", self._on_sidebar_selected)
        scroller.add(sidebar)
        return scroller

    def _on_sidebar_selected(self, lb, row):
        name = row.get_name()
        if name: self._switch_to_page(name)

    def _switch_to_page(self, name):
        if name not in self._page_registry:
            mapping = {
                "Operational Overview": "dashboard.DashboardPage",
                "Tactical Swarm AI": "ai_page.AIPage",
                "Web Assault": "web_attacks_page.WebAttacksPage",
                "Signal Recon": "recon_page.ReconPage",
                "Offensive Exploit": "exploit_page.ExploitPage",
                "Vulnerability Pulse": "vuln_page.VulnScannerPage",
            }
            if name in mapping:
                mod_name, class_name = mapping[name].split(".")
                mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
                cls = getattr(mod, class_name)
                self._page_registry[name] = cls()
                self._page_container.add_named(self._page_registry[name], name)
        self._page_container.set_visible_child_name(name)
        self._page_container.show_all()

class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.shadowcypher.apex")

    def do_activate(self):
        self._window = ShadowCypherWindow(self)

def main():
    # APEX_BOOTSTRAP_PROTOCOL
    from shadowcypher_overlord_audit import ApexOverlord
    from shadowcypher.core.hub import hub
    from shadowcypher.ai.sisyphus import sisyphus
    
    logger.info("system", "BOOTING_APEX_PREDATOR_CORE...")
    
    # 1. Ground-Up System Scan
    ApexOverlord().stabilize()
    
    # 2. Start Infinite Intelligence Loop
    hub.system_status = "OPTIMIZING"
    sisyphus.start()
    
    app = ShadowCypherApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
