import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import os

from shadowcypher.ui.base_page import BasePage
from shadowcypher.modules.phishing import Phishing
from shadowcypher.core.logger import logger

class PhishingPage(BasePage):
    """Deep Phishing & Social Engineering Interface."""

    def __init__(self):
        super().__init__("\U0001f3a3 PHISHING_ASSAULT (ShadowPhish Bridge)")

        from shadowcypher.ui.components import DataPod
        
        # Populate Metrics
        self.pod_creds = DataPod("CAPTURED_CREDS", "0", "cyan")
        self.pod_uptime = DataPod("SERVER_UPTIME", "IDLE", "violet")
        self.pod_success = DataPod("SUCCESS_RATIO", "0.0%", "amber")
        
        self.metric_strip.pack_start(self.pod_creds, True, True, 0)
        self.metric_strip.pack_start(self.pod_uptime, True, True, 0)
        self.metric_strip.pack_start(self.pod_success, True, True, 0)

        # Build Notebook
        notebook = Gtk.Notebook()
        notebook.append_page(self._build_artifacts_tab(), Gtk.Label(label="Artifacts"))
        notebook.append_page(self._build_server_tab(), Gtk.Label(label="Phish Server"))
        notebook.append_page(self._build_smuggling_tab(), Gtk.Label(label="Smuggling"))
        self.workspace.pack_start(notebook, True, True, 0)
        
        # Termination control
        self.workspace.pack_start(self.build_stop_button(), False, False, 0)

    def _build_artifacts_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)

        # 1. PDF Artifact
        row_pdf = Gtk.Box(spacing=10)
        row_pdf.pack_start(Gtk.Label(label="Redirect URL:"), False, False, 0)
        self.pdf_url = Gtk.Entry()
        self.pdf_url.set_placeholder_text("https://phish.target.com/login")
        self.pdf_url.set_hexpand(True)
        row_pdf.pack_start(self.pdf_url, True, True, 0)
        box.pack_start(row_pdf, False, False, 0)

        btn_pdf = self.make_action_btn("\U0001f4c4 Generate Malicious PDF", self._on_pdf, "danger-btn")
        box.pack_start(btn_pdf, False, False, 0)

        box.pack_start(Gtk.Separator(), False, False, 5)

        # 2. PowerShell Obfuscation
        lbl = Gtk.Label(label="PowerShell Payload (Raw):", xalign=0)
        box.pack_start(lbl, False, False, 0)
        
        self.ps_input = Gtk.TextView()
        self.ps_input.set_size_request(-1, 100)
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.ps_input)
        box.pack_start(scroll, False, False, 0)

        row_opts = Gtk.Box(spacing=20)
        self.chk_b64 = Gtk.CheckButton(label="Base64 Encode")
        self.chk_b64.set_active(True)
        self.chk_comp = Gtk.CheckButton(label="Deflate Compression")
        self.chk_comp.set_active(True)
        row_opts.pack_start(self.chk_b64, False, False, 0)
        row_opts.pack_start(self.chk_comp, False, False, 0)
        box.pack_start(row_opts, False, False, 0)

        btn_ps = self.make_action_btn("\u26a1 Obfuscate PS1", self._on_ps)
        box.pack_start(btn_ps, False, False, 0)

        return box

    def _build_server_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)

        row = Gtk.Box(spacing=10)
        row.pack_start(Gtk.Label(label="Template:"), False, False, 0)
        self.template_combo = Gtk.ComboBoxText()
        
        # PRO_DIVE: Scrape real templates from the modules directory
        from shadowcypher.core.config import config
        project_root = str(config.project_root)
        tpl_dir = os.path.join(project_root, "shadowcypher/modules/phish_data/sites")
        if os.path.exists(tpl_dir):
            templates = sorted([d for d in os.listdir(tpl_dir) if os.path.isdir(os.path.join(tpl_dir, d))])
            for t in templates:
                self.template_combo.append_text(t.capitalize())
        else:
            # Fallback
            for t in ["Google", "Microsoft", "Steam", "Facebook", "Instagram"]:
                self.template_combo.append_text(t)
        
        self.template_combo.set_active(0)
        row.pack_start(self.template_combo, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=10)
        row2.pack_start(Gtk.Label(label="Local Port:"), False, False, 0)
        self.phish_port = Gtk.SpinButton.new_with_range(80, 65535, 1)
        self.phish_port.set_value(8080)
        row2.pack_start(self.phish_port, False, False, 0)
        
        self.chk_tunnel = Gtk.CheckButton(label="SECURE_TUNNEL (HTTPS)")
        row2.pack_start(self.chk_tunnel, False, False, 10)
        box.pack_start(row2, False, False, 0)

        btn = self.make_action_btn("\U0001f310 Launch Phishing Server", self._on_start_server, "danger-btn")
        box.pack_start(btn, False, False, 0)

        btn_ai = self.make_action_btn("\U0001f9e0 Synthesize AI-Lure", self._on_ai_lure)
        box.pack_start(btn_ai, False, False, 0)

        return box

    def _build_smuggling_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(15); box.set_margin_bottom(15); box.set_margin_start(15); box.set_margin_end(15)

        row = Gtk.Box(spacing=10)
        row.pack_start(Gtk.Label(label="Source File:"), False, False, 0)
        self.smuggle_file = Gtk.Entry()
        self.smuggle_file.set_placeholder_text("/path/to/malware.exe")
        row.pack_start(self.smuggle_file, True, True, 0)
        box.pack_start(row, False, False, 0)

        row2 = Gtk.Box(spacing=10)
        row2.pack_start(Gtk.Label(label="Download Name:"), False, False, 0)
        self.smuggle_name = Gtk.Entry()
        self.smuggle_name.set_text("invoice.iso")
        row2.pack_start(self.smuggle_name, True, True, 0)
        box.pack_start(row2, False, False, 0)

        btn = self.make_action_btn("\U0001f4e6 Generate HTML Smuggler", self._on_smuggling)
        box.pack_start(btn, False, False, 0)

        return box

    # ── Handlers ──

    def _on_pdf(self, btn):
        url = self.pdf_url.get_text().strip()
        if not url:
            self.on_output("[ERROR] Please specify a redirect URL.")
            return
        res = Phishing.generate_pdf(url)
        self.on_output(res)

    def _on_ps(self, btn):
        buf = self.ps_input.get_buffer()
        script = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()
        if not script:
            self.on_output("[ERROR] Please enter a script to obfuscate.")
            return
        b64 = self.chk_b64.get_active()
        comp = self.chk_comp.get_active()
        res = Phishing.generate_obfuscated_ps1(script, use_b64=b64, use_compress=comp)
        self.on_output(res)

    def _on_start_server(self, btn):
        tmpl = self.template_combo.get_active_text()
        port = int(self.phish_port.get_value())
        use_tunnel = self.chk_tunnel.get_active()
        self.clear_output(f"Launching {tmpl} phishing site on port {port} (Bridge: {'HTTPS_TUNNEL' if use_tunnel else 'LOCAL'})...\n")
        Phishing.start_phishing_server(tmpl, port, self.on_output, use_tunnel=use_tunnel)

    def _on_ai_lure(self, btn):
        tmpl = self.template_combo.get_active_text()
        self.terminal.log(f"INITIATING_DEEPHAT_SYNTHESIS: Forging {tmpl} persuasion lure...", "AI")
        res = Phishing.generate_professional_bait(tmpl, "http://localhost:8080")
        self.terminal.log(res, "SUCCESS")

    def _on_smuggling(self, btn):
        path = self.smuggle_file.get_text().strip()
        name = self.smuggle_name.get_text().strip()
        if not path:
            self.on_output("[ERROR] Specify a source file path.")
            return
        res = Phishing.generate_html_smuggling(path, name)
        self.on_output(res)
