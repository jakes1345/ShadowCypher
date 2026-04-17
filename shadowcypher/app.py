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
from shadowcypher.core.platform import platform_engine

# --- PHASE SIGMA: Weapon Alignment ---
hub.register_arsenal()

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
        """Launches the native signal plane and orchestrates bot ignition."""
        import subprocess
        import threading
        from shadowcypher.core.platform import platform_engine
        
        relay_bin = platform_engine.resolve_path("native", "relay", "shadow-relay")
        if not os.path.exists(relay_bin):
            logger.error("hub", "NATIVE_FATAL: Shadow-Relay binary missing. Swarm signal blocked.")
            return

        def monitor_process(proc):
            for line in proc.stdout:
                if "TITAN" in line or "SWARM" in line:
                    logger.debug("relay", line.strip())
            proc.wait()
            logger.warn("hub", "RELAY_DISCONNECT: Native core has terminated.")

        # Ignite the Go Relay
        self.relay_proc = subprocess.Popen(
            [relay_bin],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid
        )
        threading.Thread(target=monitor_process, args=(self.relay_proc,), daemon=True).start()

        # Ignition Sequence: Wait for the Bridge to lock on before starting the Bot
        def post_ignition():
            from shadowcypher.core.hub import hub
            logger.info("hub", "IGNITION_WAIT: Synchronizing with native signal plane...")
            
            # Smart Wait (Max 10s)
            for _ in range(20):
                if hasattr(hub, 'bridge') and hub.bridge.connected:
                    break
                time.sleep(0.5)
            
            try:
                from shadowcypher.core.irc_bot import sentinel
                sentinel.start()
                logger.info("hub", "SENTINEL_IGNITION: ShadowSentinel joined the native swarm.")
            except Exception as e:
                logger.error("hub", f"SENTINEL_FAILURE: {e}")

        threading.Thread(target=post_ignition, daemon=True).start()

    def _pulse_tick(self) -> bool:
        from shadowcypher.core.platform import platform_engine
        from shadowcypher.core.hub import hub
        from shadowcypher.core.audit import auditor
        
        try:
            # 1. Performance Vitals
            vitals = platform_engine.get_system_vitals()
            cpu, mem = vitals["cpu"], vitals["mem"]
            self.cpu_label.set_text(f"CPU_LOAD: [{'|'*int(cpu/10)}{'.'*(10-int(cpu/10))}] {cpu:.1f}%")
            self.mem_label.set_text(f"MEM_PRESSURE: [{'|'*int(mem/10)}{'.'*(10-int(mem/10))}] {mem:.1f}%")
            
            # 2. Tactical Metrics
            summary = hub.get_tactical_summary()
            swarm_count = summary.get("telemetry", {}).get("swarm_nodes", 0)
            self.net_label.set_text(f"NET_ENTROPY: {summary.get('telemetry', {}).get('load_avg', 0):.2f}bps")
            self.irc_label.set_markup(f"SWARM_NODES: <span color='#22c55e'>{swarm_count} ACTIVE</span>")
            
            # 3. EMPIRICAL_VERIFICATION: The Heart of Truth
            # Run a lightweight health check (don't run full AI sanity every second)
            health = auditor.verify_relay_link()
            fid_color = "#22c55e" if health["status"] == "PASS" else "#f87171"
            
            # Update Coordinate Status
            status_text = (f"FIDELITY: <span color='{fid_color}'>LIVE</span> | "
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
        scroller.set_size_request(280, -1)
        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")

        pages = [
            ("---", "NEXUS-COMMAND"),
            ("\U0001f4ca", "Central Command HUD"),
            ("\U0001f5fa", "Spectre War-Map"),
            ("\U0001f5c4", "Artifact Crypt"),
            ("\U0001f916", "Shadow-Synthesizer"),
            ("---", "COVERT-INTEL"),
            ("\U0001f4e1", "Signal Analysis"),
            ("\U0001f50e", "Spectral Intelligence"),
            ("\U0001f47b", "Ghost Ops Infiltration"),
            ("\U0001f310", "Infrastructure Recon"),
            ("\U0001f3af", "Vulnerability Sweep"),
            ("\U0001f3ae", "Gaming Asset Audit"),
            ("---", "OFFENSIVE-LAB"),
            ("\U0001f575", "Web Layer Destruction"),
            ("\U0001f3a3", "Phishing Synthesis"),
            ("\U0001f4e6", "Ghost Factory"),
            ("\U0001f4a3", "Zero-Day Strike"),
            ("\U0001f511", "Key Harvester"),
            ("\U0001f4f6", "Wireless Saturation"),
            ("---", "LANGUAGE_SOVEREIGNTY"),
            ("\u2728", "ShadowScript Lab"),
            ("\U0001f4dc", "Omni-Grammar Bible"),
            ("---", "SOVEREIGN-OPS"),
            ("\U0001f6e1", "Citadel Breach"),
            ("\U0001f528", "Privilege Escalation"),
            ("\U0001f525", "Perimeter Shield"),
            ("\U0001f50d", "Forensic Reconstruction"),
            ("\U0001f512", "Active Link Manager"),
            ("---", "SYSTEM-NUCLEUS"),
            ("\U0001f6e0", "Hub Settings"),
            ("\U0001f5e1", "Tactical HUD"),
            ("\U0001f5dd", "God-Panel (Latent Matrix)"),
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
                "Central Command HUD": "dashboard.DashboardPage",
                "Spectre War-Map": "war_map_page.WarMapPage",
                "Artifact Crypt": "vault_page.ShadowVaultPage",
                "Shadow-Synthesizer": "ai_page.AIPage",
                "Signal Analysis": "recon_page.ReconPage",
                "Spectral Intelligence": "osint_page.OSINTPage",
                "Infrastructure Recon": "network_page.NetworkPage",
                "Vulnerability Sweep": "vuln_page.VulnScannerPage",
                "Gaming Asset Audit": "steam_page.SteamAuditPage",
                "Web Layer Destruction": "web_attacks_page.WebAttacksPage",
                "Phishing Synthesis": "phishing_page.PhishingPage",
                "Ghost Factory": "payload_page.PayloadPage",
                "Zero-Day Strike": "exploit_page.ExploitPage",
                "Key Harvester": "credentials_page.CredentialsPage",
                "Wireless Saturation": "wireless_page.WirelessPage",
                "ShadowScript Lab": "shadowscript_page.ShadowScriptPage",
                "Omni-Grammar Bible": "shadowscript_page.ShadowScriptBible",
                "Citadel Breach": "ad_page.AdPage",
                "Privilege Escalation": "ad_attacks_page.ADAttacksPage",
                "Perimeter Shield": "firewall_page.FirewallPage",
                "Forensic Reconstruction": "forensics_page.ForensicsPage",
                "Active Link Manager": "session_page.SessionPage",
                "Hub Settings": "admin_page.AdminPage",
                "Tactical HUD": "combat_page.CombatDeck",
                "Ghost Ops Infiltration": "ghost_page.GhostDeck",
                "God-Panel (Latent Matrix)": "admin_page.AdminPage",
                "Wraith Protocol": "admin_page.AdminPage",
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
