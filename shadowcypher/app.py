import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import sys, os, time

from shadowcypher.core.config import config
from shadowcypher.core.hub import hub
from shadowcypher.ui.themes import get_theme
from shadowcypher.core.logger import logger
from shadowcypher.core.security import StealthHoneypot
from shadowcypher.core.identity import identity
from shadowcypher.core.bus import bus
from shadowcypher.core.platform import platform_engine

# --- PHASE SIGMA: Weapon Alignment ---
hub.register_arsenal()

class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="SHADOWCYPHER_APEX")
        self.set_default_size(1280, 720)
        self.set_size_request(800, 600)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # APEX_IDENTITY: Force WM Class for taskbar icon binding
        self.set_wmclass("ShadowCypher", "org.shadowcypher.ShadowCypher")
        GLib.set_prgname("ShadowCypher")
        
        # Early-bind sidebar list to prevent initialization race conditions
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.get_style_context().add_class("sidebar")

        # DEBUG: Toggle GPU acceleration based on driver support
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
            settings.set_property("gtk-enable-animations", True)
        
        # FIXME: Native OpenGL backend is flaky on some X11 drivers
        Gdk.set_allowed_backends("x11,wayland,*")

        # Load branding assets
        from shadowcypher.core.platform import platform_engine
        icon_path = platform_engine.resolve_path("native", "icons", "shadowcypher-256.png")
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
        self._page_container.set_transition_duration(100)
        
        # 4. Tactical Sidebar (The Pulse)
        self.pulse_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pulse_box.get_style_context().add_class("citadel-pulse")
        self.pulse_box.set_size_request(260, -1)
        
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
        self.ghost_label = Gtk.Label()
        self.ghost_label.set_markup("<span color='#f87171'>GHOST: INACTIVE</span>")

        for lbl in [self.net_label, self.irc_label, self.ghost_label]:
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
        
        # Wrap page container in a ScrolledWindow to prevent horizontal overflow
        self.page_scroller = Gtk.ScrolledWindow()
        self.page_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.page_scroller.set_propagate_natural_width(True)
        self.page_scroller.set_propagate_natural_height(True)
        self.page_scroller.add(self._page_container)
        
        self.layout_grid.attach(self.nav_box, 0, 0, 1, 1)
        self.layout_grid.attach(self.page_scroller, 1, 0, 1, 1)
        self.layout_grid.attach(self.pulse_box, 2, 0, 1, 1)
        
        vbox_master.pack_start(self.layout_grid, True, True, 0)

        # 3. Apex Footer
        self.footer = Gtk.ActionBar()
        self.footer.get_style_context().add_class("footer")
        
        self.status_label = Gtk.Label()
        self.status_label.set_markup("FIDELITY: <span color='#f87171'>SYNC</span> | MSN: 0 | ID: ???")
        self.footer.set_center_widget(self.status_label)
        
        vbox_master.pack_end(self.footer, False, False, 0)
        
        # 4. Final Initialization
        self._page_registry = {}
        
        self._switch_to_page("Central Command HUD")
        
        # Ensure sidebar selection reflects the initial page
        first_row = self.sidebar_list.get_row_at_index(1) # Index 0 is the 'NEXUS-COMMAND' header
        if first_row:
            self.sidebar_list.select_row(first_row)
        
        # Subscribe to Autonomous Ticket Events
        from shadowcypher.core.bus import bus
        bus.subscribe("new_ticket", self._on_new_ticket)
        
        # Telemetry tick — 3s is plenty, no need to hammer every 2s
        GLib.timeout_add(3000, self._pulse_tick)

        self.show_all()

    def _pulse_tick(self) -> bool:
        from shadowcypher.core.platform import platform_engine
        from shadowcypher.core.hub import hub
        
        try:
            # 1. Performance Vitals (lightweight — reads /proc only)
            vitals = platform_engine.get_system_vitals()
            cpu, mem = vitals["cpu"], vitals["mem"]
            self.cpu_label.set_text(f"CPU_LOAD: [{'|'*int(cpu/10)}{'.'*(10-int(cpu/10))}] {cpu:.1f}%")
            self.mem_label.set_text(f"MEM_PRESSURE: [{'|'*int(mem/10)}{'.'*(10-int(mem/10))}] {mem:.1f}%")
            
            # 2. Tactical Metrics
            summary = hub.get_tactical_summary()
            swarm_count = summary.get("telemetry", {}).get("swarm_nodes", 0)
            self.net_label.set_text(f"NET_ENTROPY: {summary.get('telemetry', {}).get('load_avg', 0):.2f}bps")
            self.irc_label.set_markup(f"SWARM_NODES: <span color='#22c55e'>{swarm_count} ACTIVE</span>")
            
            # 3. Ghost Mode live status (cheap — just checks a file and a socket)
            import socket as _sock, os as _os
            ghost_active = _os.path.exists("/tmp/.ghost_mode_state")
            tor_up = False
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(0.3)
                tor_up = s.connect_ex(("127.0.0.1", 9050)) == 0
                s.close()
            except Exception:
                pass
            if ghost_active and tor_up:
                self.ghost_label.set_markup("<span color='#22c55e'>GHOST: ACTIVE ✓</span>")
            elif tor_up:
                self.ghost_label.set_markup("<span color='#f59e0b'>GHOST: TOR-ONLY</span>")
            else:
                self.ghost_label.set_markup("<span color='#f87171'>GHOST: INACTIVE</span>")

            # 4. Footer status
            fid_color = "#22c55e" if ghost_active else "#f87171"
            status_text = (f"FIDELITY: <span color='{fid_color}'>{'GHOST' if ghost_active else 'EXPOSED'}</span> | "
                           f"MSN: {summary.get('active_missions')} | "
                           f"ID: {summary.get('telemetry', {}).get('shadow_id', '???')}")
            self.status_label.set_markup(status_text)
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
        scroller.set_propagate_natural_width(False)
        scroller.set_size_request(220, -1)
        
        # self.sidebar_list is now pre-initialized in __init__

        pages = [
            ("---", "NEXUS-COMMAND"),
            ("\U0001f4ca", "Central Command HUD"),
            ("\U0001f5fa", "Spectre War-Map"),
            ("\U0001f5c4", "Artifact Crypt"),
            ("\U0001f916", "Shadow-Synthesizer"),
            ("---", "TACTICAL-INTEL"),
            ("\u2728", "Spectral Intelligence"),
            ("\U0001f3af", "Vulnerability Sweep"),
            ("\U0001f310", "Network Scanner"),
            ("\U0001f50e", "OSINT Probe"),
            ("\U0001f4bc", "Session Manager"),
            ("---", "OFFENSIVE-LAB"),
            ("\U0001f575", "Web & Cloud Strikes"),
            ("\U0001f4a3", "Payload Factory"),
            ("\U0001f4f6", "Wireless Saturation"),
            ("\U0001f5a5", "C2 Command Center"),
            ("\U0001f480", "Exploit Engine"),
            ("\U0001f3a3", "Phishing Forge"),
            ("\U0001f3db", "AD Attacks"),
            ("\u26a1", "Combat Deck"),
            ("\U0001f4dc", "ShadowScript"),
            ("---", "SOVEREIGN-OPS"),
            ("\U0001f4ac", "Sovereign Chat"),
            ("\U0001f47b", "Shadow Nodes"),
            ("\U0001f47a", "Ghost Mode"),
            ("\U0001f50d", "Forensic Audit"),
            ("\U0001f6e1", "Guardian"),
            ("\U0001f9ea", "Intel Harvest"),
            ("\U0001f525", "Firewall Manager"),
            ("\U0001f511", "Credentials Vault"),
            ("\U0001f6e0", "Hub Settings"),
            ("\U0001f5dd", "God-Panel"),
            ("\u2622", "Wraith Protocol"),
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
            self.sidebar_list.add(row)

        self.sidebar_list.set_activate_on_single_click(True)
        self.sidebar_list.connect("row-selected", self._on_sidebar_selected)
        scroller.add(self.sidebar_list)
        return scroller

    def _on_sidebar_selected(self, lb, row):
        if row is None:
            return
        name = getattr(row, "page_id", None)
        if name:
            self._switch_to_page(name)

    def _switch_to_page(self, name, make_visible=True, **kwargs):
        if name not in self._page_registry:
            mapping = {
                "Central Command HUD": "dashboard.DashboardPage",
                "Spectre War-Map": "war_map_page.WarMapPage",
                "Artifact Crypt": "vault_page.ShadowVaultPage",
                "Shadow-Synthesizer": "ai_page.AIPage",
                "Spectral Intelligence": "intel_page.SpectralIntelligencePage",
                "Vulnerability Sweep": "vuln_page.VulnScannerPage",
                "Network Scanner": "network_page.NetworkPage",
                "OSINT Probe": "osint_page.OSINTPage",
                "Session Manager": "session_page.SessionPage",
                "Web & Cloud Strikes": "web_attacks_page.WebAttacksPage",
                "Payload Factory": "payload_page.PayloadPage",
                "Wireless Saturation": "wireless_page.WirelessPage",
                "C2 Command Center": "c2_page.C2Page",
                "Exploit Engine": "exploit_page.ExploitPage",
                "Phishing Forge": "phishing_page.PhishingPage",
                "AD Attacks": "ad_attacks_page.ADAttacksPage",
                "Combat Deck": "combat_page.CombatDeck",
                "ShadowScript": "shadowscript_page.ShadowScriptPage",
                "Sovereign Chat": "chat_page.SovereignChatPage",
                "Shadow Nodes": "ghost_page.ShadowNodesPage",
                "Ghost Mode": "ghost_mode_page.GhostModePage",
                "Forensic Audit": "forensics_page.ForensicsPage",
                "Guardian": "guardian_page.GuardianPage",
                "Intel Harvest": "dataset_page.DatasetPage",
                "Firewall Manager": "firewall_page.FirewallPage",
                "Credentials Vault": "credentials_page.CredentialsPage",
                "Hub Settings": "admin_page.AdminPage",
                "God-Panel": "god_panel.GodPanel",
                "Wraith Protocol": "wraith_page.WraithProtocol",
            }
            if name not in mapping:
                return
            mod_name, class_name = mapping[name].split(".")
            try:
                mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
                cls = getattr(mod, class_name)
                page = cls(**kwargs)
                # Realize the page immediately but don't show_all() recursively yet
                self._page_registry[name] = page
                self._page_container.add_named(page, name)
                page.show_all() # Realize all child widgets once
            except Exception as e:
                logger.error("hub", f"PAGE_LOAD_FAILED: {name} -> {e}")
                err_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                err_box.add(Gtk.Label(label=f"Load Error: {name}"))
                self._page_registry[name] = err_box
                self._page_container.add_named(err_box, name)
        
        # Switch instantly if requested
        if make_visible:
            self._page_container.set_visible_child_name(name)

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
