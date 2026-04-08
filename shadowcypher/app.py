import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import sys, os, time

from shadowcypher.ui.themes import get_theme
from shadowcypher.core.logger import logger
from shadowcypher.core.security import StealthHoneypot
from shadowcypher.core.identity import identity
import threading


class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="ShadowCypher")
        # Global Window Hardening
        self.set_default_size(1580, 980)
        self.set_resizable(True)
        self.set_decorated(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        # 1. Custom HeaderBar (Obsidian Elite)
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("ShadowCypher")
        self.header.set_subtitle("\U0001f575\ufe0f MISSION_COMMAND_CENTER")
        self.set_titlebar(self.header)

        # Scaled Raven Icon in Header
        from shadowcypher.core.config import config

        icon_path = os.path.join(
            config.project_root, "shadowcypher", "ui", "assets", "icon.png"
        )
        if os.path.exists(icon_path):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 28, 28, True)
                img = Gtk.Image.new_from_pixbuf(pb)
                self.header.pack_start(img)
                self.set_icon_from_file(icon_path)
            except (GLib.Error, FileNotFoundError, OSError):
                pass

        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # 2. Main Layout Container
        vbox_master = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_master)

        hbox_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vbox_master.pack_start(hbox_content, True, True, 0)

        self._sidebar = self._build_sidebar()
        hbox_content.pack_start(self._sidebar, False, False, 0)

        self._page_container = Gtk.Stack()
        self._page_container.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        hbox_content.pack_start(self._page_container, True, True, 0)

        # 3. Global Status Footer
        self.footer = Gtk.ActionBar()
        self.system_status = Gtk.Label()
        role_tag = (
            "<span color='#ff0040' font_weight='bold'>[\U0001f5dd] ADMIN NODE</span>"
            if identity.is_admin
            else "<span color='#38bdf8' font_weight='bold'>[\U0001f464] OPERATOR</span>"
        )
        self.system_status.set_markup(
            f"{role_tag} | <span color='#f87171'>[ENC] FERNET-256</span> | <span color='#a855f7'>[\U0001f916] AI_HEARTBEAT: ACTIVE</span>"
        )
        self.system_status.get_style_context().add_class("text-muted")
        self.footer.pack_start(self.system_status)

        self.uptime_status = Gtk.Label(label="00:00:00")
        self.footer.pack_end(self.uptime_status)
        vbox_master.pack_start(self.footer, False, False, 0)

        self._page_registry = {}
        self._switch_to_page("Operational Overview")
        GLib.timeout_add(1000, self._update_footer_clock)
        self.show_all()

    def _update_footer_clock(self):
        self.uptime_status.set_text(time.strftime("%H:%M:%S"))
        return True

    def _build_sidebar(self):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_size_request(280, -1)

        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")

        # STRUCTURE: (Icon, Name)
        pages = [
            ("---", "COMMAND_CENTRAL"),
            ("\U0001f4ca", "Operational Overview"),
            ("\U0001f916", "Tactical Swarm AI"),
            ("---", "OFFENSIVE_OPERATIONS"),
            ("\U0001f310", "Web Assault"),
            ("\U0001f4bb", "Domain Dominance"),
            ("\U0001f4e1", "Signal Recon"),
            ("\U0001f4a3", "Offensive Exploit"),
            ("\U0001f50e", "Vulnerability Pulse"),
            ("---", "INTEL_OSINT"),
            ("\U0001f50d", "Digital Analysis"),
            ("\U0001f4ad", "OSINT Intelligence"),
            ("\U0001f511", "Credential Hub"),
            ("---", "GAMING_SHADOW_OPS"),
            ("\U0001f3ae", "Master Asset Discovery"),
            ("\U0001f512", "Library Security Audit"),
            ("---", "SYSTEM_GRID"),
            ("\U0001f310", "Stealth Network"),
            ("\U0001f6e1", "Firewall Defense"),
            ("\U0001f4f6", "Wireless Signals"),
            ("\U0001f4bb", "System Control"),
            ("\U0001f4e7", "Support & Ticketing"),
        ]

        if identity.is_admin:
            pages.append(("---", "ADMIN_SECTOR"))
            pages.append(("\U0001f5dd", "Admin Master Control"))

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
        if name:
            self._switch_to_page(name)

    def _switch_to_page(self, name):
        if name not in self._page_registry:
            try:
                mapping = {
                    "Operational Overview": "dashboard.DashboardPage",
                    "Tactical Swarm AI": "ai_page.AIPage",
                    "Web Assault": "web_attacks_page.WebAttacksPage",
                    "Domain Dominance": "ad_attacks_page.ADAttacksPage",
                    "Signal Recon": "recon_page.ReconPage",
                    "Offensive Exploit": "exploit_page.ExploitPage",
                    "Vulnerability Pulse": "vuln_page.VulnScannerPage",
                    "Stealth Network": "network_page.NetworkPage",
                    "Digital Analysis": "forensics_page.ForensicsPage",
                    "OSINT Intelligence": "osint_page.OSINTPage",
                    "Credential Hub": "credentials_page.CredentialsPage",
                    "Master Asset Discovery": "steam_page.SteamAuditPage",
                    "Library Security Audit": "steam_page.SteamAuditPage",
                    "Firewall Defense": "firewall_page.FirewallPage",
                    "Wireless Signals": "wireless_page.WirelessPage",
                    "System Control": "session_page.SessionPage",
                    "Support & Ticketing": "support_page.SupportPage",
                    "Admin Master Control": "admin_page.AdminPage",
                }
                if name in mapping:
                    mod_name, class_name = mapping[name].split(".")
                    try:
                        mod = __import__(
                            f"shadowcypher.ui.{mod_name}", fromlist=[class_name]
                        )
                        cls = getattr(mod, class_name)
                        self._page_registry[name] = cls()
                    except Exception as e:
                        logger.error("ui", f"Failed to import page '{name}': {e}")
                        lbl = Gtk.Label(label=f"[MODULE ERROR] {name}: {e}")
                        lbl.set_line_wrap(True)
                        self._page_registry[name] = lbl

                    self._page_container.add_named(self._page_registry[name], name)
                self._page_container.show_all()
            except Exception as e:
                logger.error("ui", f"Failed to load page '{name}': {e}")
                lbl = Gtk.Label(label=f"[SYSTEM] ERROR_ACCESSING_{name.upper()}")
                self._page_container.add_named(lbl, name)
        self._page_container.set_visible_child_name(name)


class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.shadowcypher.overlord")

    def do_activate(self):
        self._window = ShadowCypherWindow(self)


_honeypot = None


def _start_honeypot():
    global _honeypot
    _honeypot = StealthHoneypot(port=2222, bind_addr="127.0.0.1")
    threading.Thread(target=_honeypot.start_bait, daemon=True).start()


def main():
    _start_honeypot()
    app = ShadowCypherApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
