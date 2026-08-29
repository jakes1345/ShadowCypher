import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
import os
import threading

from gi.repository import Gdk, GLib, Gtk

# Wire custom askpass so sudo prompts use the ShadowCypher elevation gate
_askpass = os.path.join(os.path.dirname(__file__), "..", "..", "native", "shadowcypher-askpass")
_askpass = os.path.abspath(_askpass)
if os.path.exists(_askpass):
    os.environ["SUDO_ASKPASS"] = _askpass

from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger
from shadowcypher.core.platform import platform_engine
from shadowcypher.ui.themes import get_theme


class ShadowCypherWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="ShadowCypher")
        self.set_default_size(1280, 720)
        self.set_size_request(800, 600)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.set_wmclass("ShadowCypher", "org.shadowcypher.ShadowCypher")
        GLib.set_prgname("ShadowCypher")

        # Early-bind sidebar list to prevent initialization race conditions
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.get_style_context().add_class("sidebar")

        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
            settings.set_property("gtk-enable-animations", True)

        # x11 must be listed first; OpenGL fallback order matters on multi-driver systems
        Gdk.set_allowed_backends("x11,wayland,*")

        # Load branding assets — prefer dark (black bg) variant for window icon
        icon_path = platform_engine.resolve_path("native", "icons", "shadowcypher-256-dark.png")
        if not os.path.exists(icon_path):
            icon_path = platform_engine.resolve_path("native", "icons", "shadowcypher-256.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # 1. Apex HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("ShadowCypher")
        self.header.set_subtitle("Sovereign Security Platform")
        self.set_titlebar(self.header)

        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # 2. Apex Layout
        vbox_master = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_master)

        self.nav_box = self._build_sidebar()

        # 3. Main Operational Stack (ShadowCypher HUD)
        self._page_container = Gtk.Stack()
        self._page_container.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._page_container.set_transition_duration(100)

        # 4. Telemetry sidebar (live stats)
        self.pulse_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pulse_box.get_style_context().add_class("citadel-pulse")
        self.pulse_box.set_size_request(260, -1)

        # Section Header: Telemetry
        tel_header = Gtk.Label()
        tel_header.set_markup("<span size='small' weight='bold' color='#94a3b8'>// REAL-TIME_TELEMETRY</span>")
        tel_header.set_halign(Gtk.Align.START)
        self.pulse_box.pack_start(tel_header, False, False, 10)

        # Real-time telemetry widgets
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

        # Wrap page container in a ScrolledWindow for vertical overflow
        self.page_scroller = Gtk.ScrolledWindow()
        self.page_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.page_scroller.set_hexpand(True)
        self.page_scroller.set_vexpand(True)
        self.page_scroller.add(self._page_container)

        self.layout_grid.attach(self.nav_box, 0, 0, 1, 1)
        self.layout_grid.attach(self.page_scroller, 1, 0, 1, 1)
        self.layout_grid.attach(self.pulse_box, 2, 0, 1, 1)

        vbox_master.pack_start(self.layout_grid, True, True, 0)

        # Tour panel — slides up from between layout and footer
        from shadowcypher.ui.tour import TourPanel, tour_completed
        self._tour = TourPanel(
            navigate_cb=self._switch_to_page,
            on_finish=None,
        )
        vbox_master.pack_start(self._tour, False, False, 0)

        # 3. Apex Footer
        self.footer = Gtk.ActionBar()
        self.footer.get_style_context().add_class("footer")

        self.status_label = Gtk.Label()
        self.status_label.set_markup("FIDELITY: <span color='#f87171'>SYNC</span> | MSN: 0 | ID: ???")
        self.footer.set_center_widget(self.status_label)

        # "Take Tour" link in footer
        tour_btn = Gtk.Button(label="Take Tour")
        tour_btn.set_relief(Gtk.ReliefStyle.NONE)
        tour_btn.get_style_context().add_class("tour-btn-skip")
        tour_btn.connect("clicked", lambda _: self._tour.start())
        self.footer.pack_end(tour_btn)

        vbox_master.pack_end(self.footer, False, False, 0)

        # 4. Final Initialization
        self._page_registry = {}

        # Hide to tray on close instead of destroying the window
        self.connect("delete-event", self._on_delete_event)

        # Subscribe to Autonomous Ticket Events
        bus.subscribe("new_ticket", self._on_new_ticket)

        # Single persistent background thread: probes Tor every 10s, caches result
        self._tor_up = False
        threading.Thread(target=self._tor_probe_worker, daemon=True, name="TorProbe").start()

        # Telemetry tick — 3s is plenty
        GLib.timeout_add(3000, self._pulse_tick)

        self.show_all()

        # Defer first page load until the window is fully realized and painted.
        # Loading pages before realization causes the black-window-on-launch bug
        # because many GTK widgets (WebKit, DrawingArea, etc.) require a realized
        # parent to paint their first frame correctly.
        GLib.idle_add(self._load_initial_page)

        # Auto-start tour on first launch (after UI is visible and welcome is done)
        if not tour_completed():
            # Delay slightly so the window fully renders before tour slides up
            GLib.timeout_add(800, self._maybe_start_tour)

    def _load_initial_page(self) -> bool:
        """Load the landing page after the window is realized. One-shot idle callback."""
        self._switch_to_page("Central Command HUD")
        # Sync sidebar highlight to the initial page
        first_row = self.sidebar_list.get_row_at_index(1)
        if first_row is None:
            first_row = self.sidebar_list.get_row_at_index(0)
        if first_row:
            self.sidebar_list.select_row(first_row)
        return False  # one-shot

    def _maybe_start_tour(self) -> bool:
        from shadowcypher.ui.tour import tour_completed
        from shadowcypher.ui.welcome_dialog import needs_onboarding, show_welcome
        if needs_onboarding():
            show_welcome(self)
        if not tour_completed():
            self._tour.start()
        return False  # one-shot

    def _show_update_banner(self, info: dict):
        """Show a dismissible infobar when a new version is available."""
        bar = Gtk.InfoBar()
        bar.set_message_type(Gtk.MessageType.INFO)
        bar.set_show_close_button(True)
        lbl = Gtk.Label()
        lbl.set_markup(
            f"<b>ShadowCypher v{info['version']} available</b>  "
            f"<span color='#94a3b8'>Run <tt>shadowcypher --update</tt> to install.</span>"
        )
        bar.get_content_area().pack_start(lbl, False, False, 0)
        bar.connect("response", lambda b, _: b.destroy())
        # Insert below headerbar — find the top vbox
        children = self.get_children()
        if children:
            vbox = children[0]
            if isinstance(vbox, Gtk.Box):
                vbox.pack_start(bar, False, False, 0)
                vbox.reorder_child(bar, 0)
        bar.show_all()

    def _pulse_tick(self) -> bool:
        from shadowcypher.core.hub import hub

        try:
            # 1. /proc reads — fast, no I/O blocking
            vitals = platform_engine.get_system_vitals()
            cpu, mem = vitals["cpu"], vitals["mem"]
            self.cpu_label.set_text(f"CPU_LOAD: [{'|'*int(cpu/10)}{'.'*(10-int(cpu/10))}] {cpu:.1f}%")
            self.mem_label.set_text(f"MEM_PRESSURE: [{'|'*int(mem/10)}{'.'*(10-int(mem/10))}] {mem:.1f}%")

            # 2. Tactical metrics — flat dict (hub.get_tactical_summary() flattens telemetry)
            summary = hub.get_tactical_summary()
            swarm_count = summary.get("swarm_nodes", 0)
            load_avg = summary.get("load_avg", 0.0)
            self.net_label.set_text(f"NET_ENTROPY: {load_avg:.2f}")
            node_color = "#22c55e" if swarm_count > 0 else "#64748b"
            self.irc_label.set_markup(f"SWARM_NODES: <span color='{node_color}'>{swarm_count} ACTIVE</span>")

            # 3. Ghost status from cached probe (updated off-thread)
            ghost_active = os.path.exists("/tmp/.ghost_mode_state")  # nosec B108
            tor_up = getattr(self, "_tor_up", False)
            if ghost_active and tor_up:
                self.ghost_label.set_markup("<span color='#22c55e'>GHOST: ACTIVE ✓</span>")
            elif tor_up:
                self.ghost_label.set_markup("<span color='#f59e0b'>GHOST: TOR-ONLY</span>")
            else:
                self.ghost_label.set_markup("<span color='#f87171'>GHOST: INACTIVE</span>")

            # 4. Footer status
            fid_color = "#22c55e" if ghost_active else "#f87171"
            shadow_id = summary.get("shadow_id", "UNLINKED")
            self.status_label.set_markup(
                f"FIDELITY: <span color='{fid_color}'>{'GHOST' if ghost_active else 'EXPOSED'}</span> | "
                f"MSN: {summary.get('active_missions', 0)} | "
                f"ID: {shadow_id}"
            )
        except Exception as _e:
            from shadowcypher.core.logger import logger as _log
            _log.warning("app", f"PULSE_TICK_ERROR: {_e}")
        return True

    def _tor_probe_worker(self) -> None:
        """Single persistent background thread: probe Tor port every 10s."""
        import socket as _sock
        import time as _time
        while True:
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
                s.settimeout(0.5)
                self._tor_up = s.connect_ex(("127.0.0.1", 9050)) == 0
                s.close()
            except Exception:
                self._tor_up = False
            _time.sleep(10)

    def _on_new_ticket(self, data: dict):
        handle = data.get("handle", "Unknown")
        self.header.set_subtitle(f"⚠️ TICKET_ALERT: {handle}")
        logger.info("ui", f"NOTIFIED: New autonomous ticket from {handle}")

    def _on_delete_event(self, _widget, _event):
        self.hide()
        return True  # block destroy; quit only via tray menu

    def _build_sidebar(self):
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_width(False)
        scroller.set_size_request(220, -1)

        # self.sidebar_list is now pre-initialized in __init__

        # (icon, label, badge)  badge=None means no badge
        pages = [
            ("---", "Command Center", None),
            ("\U0001f4ca", "Central Command HUD", None),
            ("\U0001f5fa", "Attack Map", None),
            ("\U0001f5c4", "Vault", None),
            ("\U0001f916", "AI Assistant", "APEX"),
            ("\U0001f510", "Guardian AI", None),
            ("---", "Intelligence", None),
            ("✨", "Intelligence Center", "APEX"),
            ("\U0001f3af", "Vuln Scanner", None),
            ("\U0001f310", "Network Scanner", None),
            ("\U0001f50e", "OSINT Probe", None),
            ("\U0001f4bc", "Session Manager", None),
            ("\U0001f9e0", "Recon Engine", None),
            ("\U0001f3ae", "Steam OSINT", None),
            ("---", "Operations", None),
            ("\U0001f575", "Web Security", None),
            ("\U0001f4a3", "Payload Builder", "APEX"),
            ("\U0001f4f6", "Wireless", None),
            ("\U0001f5a5", "C2 Command Center", "APEX"),
            ("\U0001f480", "PoC Engine", None),
            ("\U0001f3a3", "Phishing Forge", None),
            ("\U0001f3db", "AD Assessment", None),
            ("\U0001f5c2", "AD Pivot", None),
            ("⚡", "Simulation", None),
            ("\U0001f4dc", "ShadowScript", None),
            ("---", "Sovereign", None),
            ("\U0001f5a5", "Terminal", None),
            ("\U0001f4ac", "Community Chat", None),
            ("\U0001f4e8", "Shadow Mail", None),
            ("\U0001f47b", "Shadow Nodes", "APEX"),
            ("\U0001f47a", "Ghost Mode", "APEX"),
            ("\U0001f50d", "Forensic Audit", None),
            ("\U0001f6e1", "Guardian", None),
            ("\U0001f9ea", "Datasets", None),
            ("\U0001f525", "Firewall Manager", None),
            ("\U0001f511", "Credentials Vault", "APEX"),
            ("\U0001f6e0", "Hub Settings", None),
            ("\U0001f5dd", "God-Panel", "APEX"),
            ("☢", "Emergency Wipe", "APEX"),
            ("\U0001f4cb", "ShadowCypher Audit", None),
            ("\U0001f9ec", "AI Lab", None),
            ("\U0001f4de", "Support", None),
        ]

        for entry in pages:
            icon, name, badge = entry
            row = Gtk.ListBoxRow()
            if icon == "---":
                lbl = Gtk.Label(label=f"  {name}", xalign=0)
                lbl.get_style_context().add_class("sidebar-header")
                row.set_sensitive(False)
                row.add(lbl)
            else:
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                hbox.set_margin_start(10)
                icon_lbl = Gtk.Label(label=icon)
                icon_lbl.get_style_context().add_class("cyan-text")
                name_lbl = Gtk.Label(label=name, xalign=0)
                hbox.pack_start(icon_lbl, False, False, 0)
                hbox.pack_start(name_lbl, True, True, 0)
                if badge:
                    badge_lbl = Gtk.Label(label=badge)
                    badge_lbl.get_style_context().add_class("tier-badge")
                    hbox.pack_end(badge_lbl, False, False, 6)
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
                "Attack Map": "war_map_page.WarMapPage",
                "Vault": "vault_page.ShadowVaultPage",
                "AI Assistant": "ai_page.AIPage",
                "Guardian AI": "guardian_ai_page.GuardianAIPage",
                "Intelligence Center": "intel_page.SpectralIntelligencePage",
                "Vuln Scanner": "vuln_page.VulnScannerPage",
                "Network Scanner": "network_page.NetworkPage",
                "OSINT Probe": "osint_page.OSINTPage",
                "Session Manager": "session_page.SessionPage",
                "Recon Engine": "recon_page.ReconPage",
                "Steam OSINT": "steam_page.SteamAuditPage",
                "Web Security": "web_security_page.WebSecurityPage",
                "Payload Builder": "craft_page.CraftPage",
                "Wireless": "wireless_page.WirelessPage",
                "C2 Command Center": "relay_page.RelayPage",
                "PoC Engine": "poc_page.PocPage",
                "Phishing Forge": "awareness_page.AwarenessPage",
                "AD Assessment": "ad_assessment_page.ADAssessmentPage",
                "AD Pivot": "ad_page.AdPage",
                "Simulation": "simulation_page.SimulationDeck",
                "ShadowScript": "shadowscript_page.ShadowScriptPage",
                "Terminal": "terminal_widget.TerminalPage",
                "Community Chat": "chat_page.ChatPage",
                "Shadow Mail": "mail_page.MailPage",
                "Shadow Nodes": "ghost_page.ShadowNodesPage",
                "Ghost Mode": "ghost_mode_page.GhostModePage",
                "Forensic Audit": "forensics_page.ForensicsPage",
                "Guardian": "guardian_page.GuardianPage",
                "Datasets": "dataset_page.DatasetPage",
                "Firewall Manager": "firewall_page.FirewallPage",
                "Credentials Vault": "secrets_page.SecretsPage",
                "Hub Settings": "admin_page.AdminPage",
                "God-Panel": "god_panel.GodPanel",
                "Emergency Wipe": "wraith_page.WraithProtocol",
                "ShadowCypher Audit": "audit_page.ShadowCypherAuditPage",
                "AI Lab": "ai_lab_page.AILabPage",
                "Support": "support_page.SupportPage",
            }
            if name not in mapping:
                return
            mod_name, class_name = mapping[name].split(".")
            try:
                mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
                cls = getattr(mod, class_name)
                page = cls(**kwargs)
                # If subclass inherits BasePage but builds its own layout (so it
                # packed a second main_pod and left BasePage's default unpacked),
                # auto-commit the default pod so it only appears once.
                from shadowcypher.ui.base_page import BasePage
                if isinstance(page, BasePage) and not page.get_children():
                    page.pack_start(page.main_pod, True, True, 0)
                self._page_registry[name] = page
                self._page_container.add_named(page, name)
                page.show_all()
            except Exception as e:
                import traceback
                logger.error("hub", f"PAGE_LOAD_FAILED: {name} -> {e}\n{traceback.format_exc()}")
                err_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                err_box.set_valign(Gtk.Align.CENTER)
                err_box.set_halign(Gtk.Align.CENTER)
                title = Gtk.Label()
                title.set_markup(f"<span size='large' weight='bold' color='#ef4444'>Failed to load: {name}</span>")
                detail = Gtk.Label(label=str(e))
                detail.set_line_wrap(True)
                detail.get_style_context().add_class("dim-label")
                err_box.pack_start(title, False, False, 0)
                err_box.pack_start(detail, False, False, 0)
                self._page_registry[name] = err_box
                self._page_container.add_named(err_box, name)
                err_box.show_all()

        # Switch instantly if requested
        if make_visible:
            self._page_container.set_visible_child_name(name)

class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.shadowcypher.ShadowCypher")
        self._tray: "Gtk.StatusIcon | None" = None

    def do_activate(self):
        from shadowcypher.ui.welcome_dialog import needs_onboarding, show_welcome
        if needs_onboarding():
            show_welcome(parent=None)
        self._window = ShadowCypherWindow(self)

        # Keep app alive when window is hidden to tray
        self.hold()

        # System tray
        self._setup_tray()

        # Background update check
        from shadowcypher.core.updater import run_background_check
        def _on_update(info):
            GLib.idle_add(self._window._show_update_banner, info)
        run_background_check(on_update_available=_on_update)

        # RAG knowledge base — build in background if not already done
        from shadowcypher.ai.rag import build_in_background
        build_in_background()

        # Default to shadow-gemma4 if available — off main thread to avoid startup lag
        def _pick_default_model():
            from shadowcypher.ai.providers import provider_registry
            models = provider_registry.active.list_models() if provider_registry.active else []
            if "shadow-gemma4:latest" in models:
                provider_registry.switch("ollama", model="shadow-gemma4:latest")
        threading.Thread(target=_pick_default_model, daemon=True).start()

    def _setup_tray(self):
        icon_path = platform_engine.resolve_path("native", "icons", "shadowcypher-16.png")
        self._tray = Gtk.StatusIcon()
        if os.path.exists(icon_path):
            self._tray.set_from_file(icon_path)
        else:
            self._tray.set_from_icon_name("security-high")
        self._tray.set_tooltip_text("ShadowCypher — Sovereign Security Platform")
        self._tray.set_visible(True)
        self._tray.connect("activate", self._on_tray_activate)
        self._tray.connect("popup-menu", self._on_tray_menu)

    def _on_tray_activate(self, _icon):
        if self._window.is_visible():
            self._window.hide()
        else:
            self._window.show()
            self._window.present()

    def _on_tray_menu(self, icon, button, time):
        menu = Gtk.Menu()

        label = "Hide" if self._window.is_visible() else "Show"
        toggle = Gtk.MenuItem(label=f"{label} ShadowCypher")
        toggle.connect("activate", lambda _: self._on_tray_activate(icon))
        menu.append(toggle)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._do_quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

    def _do_quit(self):
        if self._tray:
            self._tray.set_visible(False)
        self.release()
        self.quit()

def main():
    import sys
    try:
        if os.getuid() == 0:
            os.nice(-10)
    except Exception as e:
        print(f"DEBUG: Failed to adjust process priority: {e}", file=sys.stderr)

    import threading

    from shadowcypher.ai.sisyphus import sisyphus
    from shadowcypher.api import start_server
    from shadowcypher.core.hub import hub

    logger.info("hub", "BOOTING_APEX_PREDATOR_CORE...")

    hub.system_status = "OPTIMIZING"
    sisyphus.start()

    # Start local Guardian API for Android app
    try:
        api_thread = threading.Thread(target=start_server, daemon=True)
        api_thread.start()
        logger.info("hub", "Guardian API started on 0.0.0.0:9999")
    except Exception as e:
        logger.error("hub", f"Failed to start Guardian API: {e}")

    app = ShadowCypherApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
