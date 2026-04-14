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
from shadowcypher.core.bus import bus

class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="SHADOWCYPHER_APEX")
        self.set_default_size(1580, 980)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        # DEBUG: Toggle GPU acceleration based on driver support
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
            settings.set_property("gtk-enable-animations", True)
        
        # FIXME: Native OpenGL backend is flaky on some X11 drivers
        Gdk.set_allowed_backends("x11,wayland,*")

        # Load branding assets
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "native/icons/shadowcypher-256.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # 1. Apex HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("CITADEL // SHADOWCYPHER")
        self.header.set_subtitle("\U0001f575\ufe0f APEX_TACTICAL_OFFENSIVE")
        self.set_titlebar(self.header)

        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # 2. Apex Layout
        vbox_master = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_master)
        
        self.nav_box = self._build_sidebar()
        
        # 3. Main Operational Stack (The Pulse HUD)
        self._page_container = Gtk.Stack()
        self._page_container.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._page_container.set_transition_duration(400)
        
        # 4. Tactical Sidebar (The Pulse)
        self.pulse_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pulse_box.get_style_context().add_class("citadel-pulse")
        self.pulse_box.set_size_request(320, -1)
        
        # Section Header: Telemetry
        tel_header = Gtk.Label()
        tel_header.set_markup("<span size='small' weight='bold' color='#94a3b8'>// REAL-TIME_TELEMETRY</span>")
        tel_header.set_halign(Gtk.Align.START)
        self.pulse_box.pack_start(tel_header, False, False, 10)
        
        # Real-time Pulse Components
        self.cpu_label = Gtk.Label(label="CPU_LOAD: [||||||||||] 0%")
        self.mem_label = Gtk.Label(label="MEM_PRESSURE: [||||||||||] 0%")
        
        for lbl in [self.cpu_label, self.mem_label]:
            lbl.set_halign(Gtk.Align.START)
            self.pulse_box.pack_start(lbl, False, False, 5)

        # Section Header: Network
        net_header = Gtk.Label()
        net_header.set_markup("<span size='small' weight='bold' color='#94a3b8'>// NETWORK_ENTROPY</span>")
        net_header.set_halign(Gtk.Align.START)
        self.pulse_box.pack_start(net_header, False, False, 10)
        
        self.net_label = Gtk.Label(label="NET_ENTROPY: 0.00bps")
        self.irc_label = Gtk.Label(label="COORDINATION: NOMINAL")
        
        for lbl in [self.net_label, self.irc_label]:
            lbl.set_halign(Gtk.Align.START)
            self.pulse_box.pack_start(lbl, False, False, 5)

        # Assemble Full Layout
        self.layout_grid = Gtk.Grid()
        self.layout_grid.set_column_spacing(0)
        
        # Ensure children expand to fill the void
        self.nav_box.set_vexpand(True)
        self._page_container.set_hexpand(True)
        self._page_container.set_vexpand(True)
        self.pulse_box.set_vexpand(True)
        
        self.layout_grid.attach(self.nav_box, 0, 0, 1, 1)
        self.layout_grid.attach(self._page_container, 1, 0, 1, 1)
        self.layout_grid.attach(self.pulse_box, 2, 0, 1, 1)
        
        vbox_master.pack_start(self.layout_grid, True, True, 0)

        # 3. Apex Footer
        self.footer = Gtk.ActionBar()
        self.footer.get_style_context().add_class("footer")
        vbox_master.pack_end(self.footer, False, False, 0)
        
        self.status_label = Gtk.Label(label="CITADEL_NOMINAL | MISSION_READY")
        self.footer.pack_start(self.status_label)
        
        # 4. Final Initialization
        self._page_registry = {}
        self._switch_to_page("Operational Overview")
        
        # Subscribe to Autonomous Ticket Events
        from shadowcypher.core.bus import bus
        bus.subscribe("new_ticket", self._on_new_ticket)
        
        # Start High-Frequency Telemetry Tick
        GLib.timeout_add(100, self._pulse_tick)
        
        # --- Sovereign Ignition ---
        self._start_sovereign_hub()
        
        self.show_all()

    def _start_sovereign_hub(self):
        # FIXME: cleanup this mess
        from shadowcypher.core.sovereign import SovereignServer
        import asyncio
        import threading
        
        def run_srv():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            srv = SovereignServer(host="127.0.0.1", port=8888)
            
            # Start the Bot Client 2 seconds after server init
            def ignite_bot():
                time.sleep(2)
                from shadowcypher.core.irc_bot import sentinel
                sentinel.start()
                logger.info("hub", "SENTINEL_IGNITION: ShadowSentinel bot joined the hub.")
            
            threading.Thread(target=ignite_bot, daemon=True).start()
            loop.run_until_complete(srv.start())

        t = threading.Thread(target=run_srv, daemon=True)
        t.start()
        logger.info("hub", "SOVEREIGN_IGNITION: War-Room server launched in background.")

    def _pulse_tick(self) -> bool:
        from shadowcypher.core.platform import platform_engine
        from shadowcypher.core.hub import hub
        
        try:
            # Use Native Platform Vitals instead of overhead-heavy psutil
            vitals = platform_engine.get_system_vitals()
            cpu, mem = vitals["cpu"], vitals["mem"]
            
            # Update Visual Pulse (Mono-bar aesthetic)
            self.cpu_label.set_text(f"CPU_LOAD: [{'|'*int(cpu/10)}{'.'*(10-int(cpu/10))}] {cpu:.1f}%")
            self.mem_label.set_text(f"MEM_PRESSURE: [{'|'*int(mem/10)}{'.'*(10-int(mem/10))}] {mem:.1f}%")
            
            # Fetch tactical data from the Hub
            summary = hub.get_tactical_summary()
            self.net_label.set_text(f"NET_ENTROPY: {summary.get('telemetry', {}).get('load_avg', 0):.2f}bps")
            
            # Update Coordinate Status
            status_text = f"CITADEL_NOMINAL | MISSIONS: {summary.get('active_missions')} | LOAD: {vitals['p_load']:.2f}"
            self.status_label.set_text(status_text)
        except Exception:
            pass
        return True

    def _on_new_ticket(self, data: dict):
        handle = data.get("handle", "Unknown")
        self.header.set_subtitle(f"\u26a0\ufe0f TICKET_ALERT: {handle}")
        logger.info("ui", f"NOTIFIED: New autonomous ticket from {handle}")

    def _build_sidebar(self):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_size_request(280, -1)
        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")

        pages = [
            ("---", "APEX_COMMAND"),
            ("\U0001f4ca", "Operational Overview"),
            ("\U0001f3af", "Pulse Audit (Verify)"),
            ("\U0001f5c4", "Shadow Vault"),
            ("\U0001f916", "Tactical Swarm AI"),
            ("---", "RECON_&_INTEL"),
            ("\U0001f4e1", "Signal Recon"),
            ("\U0001f50e", "Deep OSINT Hub"),
            ("\U0001f310", "Network Ops"),
            ("\U0001f4f6", "Wireless Assault"),
            ("---", "OFFENSIVE_STRIKE"),
            ("\U0001f575", "Web Assault"),
            ("\U0001f4a3", "Offensive Exploit"),
            ("\U0001f3af", "Vulnerability Pulse"),
            ("\U0001f511", "Credential Assault"),
            ("---", "ADVANCED_OPS"),
            ("\U0001f6e1", "AD Infiltration"),
            ("\U0001f528", "AD Attacks (Impacket)"),
            ("\U0001f3a3", "Phishing Lab"),
            ("\U0001f4e6", "Payload Forge"),
            ("---", "DEFENSIVE_SOVEREIGN"),
            ("\U0001f525", "Firewall Control"),
            ("\U0001f50d", "Digital Forensics"),
            ("\U0001f512", "Session Manager"),
            ("\U0001f3ae", "Gaming OSINT"),
            ("\U0001f4ac", "Support & Comms"),
            ("\U0001f6e0", "Admin Panel"),
            ("\U0001f5e1", "Combat Deck"),
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
                row.page_id = name 
            sidebar.add(row)

        sidebar.set_activate_on_single_click(True)
        sidebar.connect("row-selected", self._on_sidebar_selected)
        scroller.add(sidebar)
        return scroller

    def _on_sidebar_selected(self, lb, row):
        if row is None:
            return
        name = getattr(row, "page_id", None)
        if name:
            self._switch_to_page(name)

    def _switch_to_page(self, name):
        import sys
        print(f"[NAV] Switching to: {name}", file=sys.stderr, flush=True)
        if name not in self._page_registry:
            mapping = {
                "Operational Overview": "dashboard.DashboardPage",
                "Pulse Audit (Verify)": "audit_page.PulseAuditPage",
                "Shadow Vault": "vault_page.ShadowVaultPage",
                "Tactical Swarm AI": "ai_page.AIPage",
                "Web Assault": "web_attacks_page.WebAttacksPage",
                "Signal Recon": "recon_page.ReconPage",
                "Network Ops": "network_page.NetworkPage",
                "Offensive Exploit": "exploit_page.ExploitPage",
                "Vulnerability Pulse": "vuln_page.VulnScannerPage",
                "Deep OSINT Hub": "osint_page.OSINTPage",
                "Wireless Assault": "wireless_page.WirelessPage",
                "AD Infiltration": "ad_page.AdPage",
                "AD Attacks (Impacket)": "ad_attacks_page.ADAttacksPage",
                "Phishing Lab": "phishing_page.PhishingPage",
                "Payload Forge": "payload_page.PayloadPage",
                "Digital Forensics": "forensics_page.ForensicsPage",
                "Credential Assault": "credentials_page.CredentialsPage",
                "Firewall Control": "firewall_page.FirewallPage",
                "Session Manager": "session_page.SessionPage",
                "Gaming OSINT": "steam_page.SteamAuditPage",
                "Support & Comms": "support_page.SupportPage",
                "Admin Panel": "admin_page.AdminPage",
                "Combat Deck": "combat_page.CombatDeck",
            }
            if name not in mapping:
                print(f"[NAV] Unknown page: {name}", file=sys.stderr, flush=True)
                return
            mod_name, class_name = mapping[name].split(".")
            try:
                mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
                cls = getattr(mod, class_name)
                page = cls()
                page.show_all()
                self._page_registry[name] = page
                self._page_container.add_named(page, name)
                print(f"[NAV] Loaded: {name} OK", file=sys.stderr, flush=True)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[NAV] CRASH loading {name}: {e}", file=sys.stderr, flush=True)
                logger.error("hub", f"PAGE_LOAD_FAILED: {name} -> {e}")
                err_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                err_box.set_margin_top(40)
                err_box.set_margin_start(40)
                err_lbl = Gtk.Label()
                err_lbl.set_markup(
                    f"<span size='large' color='#f87171'><b>⚠ Module Load Failed</b></span>\n\n"
                    f"<span color='#94a3b8'>{name}: {e}</span>"
                )
                err_box.pack_start(err_lbl, False, False, 0)
                err_box.show_all()
                self._page_registry[name] = err_box
                self._page_container.add_named(err_box, name)
        self._page_container.set_visible_child_name(name)
        self._page_container.show_all()

class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.shadowcypher.ShadowCypher")

    def do_activate(self):
        from shadowcypher.ui.welcome_dialog import needs_onboarding, show_welcome
        if needs_onboarding():
            show_welcome(parent=None)
        self._window = ShadowCypherWindow(self)

def main():
    try:
        if os.getuid() == 0:
            os.nice(-10) 
    except: pass

    from shadowcypher.core.hub import hub
    from shadowcypher.ai.sisyphus import sisyphus
    
    logger.info("hub", "BOOTING_APEX_PREDATOR_CORE...")
    
    hub.system_status = "OPTIMIZING"
    sisyphus.start()
    
    app = ShadowCypherApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
