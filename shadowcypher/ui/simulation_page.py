"""Simulation page — network stress testing and web security research."""

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod


class SimulationDeck(BasePage):
    def __init__(self):
        super().__init__("Simulation")
        self._build_combat_ui()

    def _build_combat_ui(self):
        self.pod_status = DataPod("Status", "Idle")
        self.pod_threads = DataPod("Threads", "0")
        self.pod_packets = DataPod("Packets", "0")
        for pod in [self.pod_status, self.pod_threads, self.pod_packets]:
            self.metric_strip.pack_start(pod, True, True, 5)

        # --- CHAOS ENGINE SECTION ---
        chaos_frame = Gtk.Frame(label="Network Stress Test")
        chaos_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        chaos_box.set_margin_start(10)
        chaos_box.set_margin_end(10)
        chaos_box.set_margin_top(10)
        chaos_box.set_margin_bottom(10)

        target_row = Gtk.Box(spacing=8)
        target_row.pack_start(Gtk.Label(label="Target:"), False, False, 0)
        self.target_entry = Gtk.Entry(placeholder_text="IP or hostname")
        target_row.pack_start(self.target_entry, True, True, 0)

        target_row.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.port_entry = Gtk.Entry(placeholder_text="443")
        self.port_entry.set_text("443")
        self.port_entry.set_width_chars(6)
        target_row.pack_start(self.port_entry, False, False, 0)
        chaos_box.pack_start(target_row, False, False, 0)

        opts_row = Gtk.Box(spacing=8)
        opts_row.pack_start(Gtk.Label(label="Duration (s):"), False, False, 0)
        self.duration_entry = Gtk.Entry(placeholder_text="30")
        self.duration_entry.set_text("30")
        self.duration_entry.set_width_chars(5)
        opts_row.pack_start(self.duration_entry, False, False, 0)

        opts_row.pack_start(Gtk.Label(label="Threads:"), False, False, 0)
        self.threads_entry = Gtk.Entry(placeholder_text="10")
        self.threads_entry.set_text("10")
        self.threads_entry.set_width_chars(5)
        opts_row.pack_start(self.threads_entry, False, False, 0)
        chaos_box.pack_start(opts_row, False, False, 0)

        btn_row = Gtk.Box(spacing=8)
        self.chaos_btn = self.make_action_btn("Start Stress Test", self._on_chaos_click, "destructive-action")
        btn_row.pack_start(self.chaos_btn, False, False, 0)

        self.stop_btn = self.make_action_btn("Stop", self._on_stop_click, "suggested-action")
        btn_row.pack_start(self.stop_btn, False, False, 0)
        chaos_box.pack_start(btn_row, False, False, 0)

        chaos_frame.add(chaos_box)
        self.workspace.pack_start(chaos_frame, False, False, 0)

        # --- WEBFORGE V2 SECTION ---
        forge_frame = Gtk.Frame(label="Web Tests")
        forge_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        forge_box.set_margin_start(10)
        forge_box.set_margin_end(10)
        forge_box.set_margin_top(10)
        forge_box.set_margin_bottom(10)

        self.forge_combo = Gtk.ComboBoxText()
        self.forge_combo.append("xss",       "XSS Scan (Reflected)")
        self.forge_combo.append("csrf",      "CSRF PoC Generator")
        self.forge_combo.append("clickjack", "Clickjacking Test")
        self.forge_combo.append("cors",      "CORS Misconfiguration")
        self.forge_combo.append("headers",   "Security Header Audit")
        self.forge_combo.append("subdomain", "Subdomain Takeover")
        self.forge_combo.append("lfi",       "LFI Scan")
        self.forge_combo.append("redirect",  "Open Redirect Scan")
        self.forge_combo.set_active(0)
        forge_box.pack_start(self.forge_combo, False, False, 0)

        self.wasm_btn = self.make_action_btn("RUN WEB TEST", self._on_forge_click)
        forge_box.pack_start(self.wasm_btn, False, False, 0)

        forge_frame.add(forge_box)
        self.workspace.pack_start(forge_frame, False, False, 0)

    def _on_chaos_click(self, btn):
        from shadowcypher.core.sanitize import validate_target
        from shadowcypher.modules.chaos import chaos

        target = self.target_entry.get_text().strip()
        if not target:
            self.log("ERROR: Specify a target IP/host", "error")
            return

        if not validate_target(target):
            self.log(f"Invalid target: {target}", "error")
            return

        try:
            port = int(self.port_entry.get_text().strip())
            duration = int(self.duration_entry.get_text().strip())
            threads = int(self.threads_entry.get_text().strip())
        except ValueError:
            self.log("ERROR: Port, duration, and threads must be integers", "error")
            return

        self.log(f"Stress test → {target}:{port} | {threads} threads × {duration}s", "system")
        self.pod_status.set_value("Active")
        self.pod_threads.set_value(str(threads))
        self.header.set_active(True)

        chaos.start_udp_flood(target, port, duration=duration, threads=threads)

        # Auto-stop after duration
        GLib.timeout_add_seconds(duration + 2, self._auto_stop)

    def _on_stop_click(self, btn):
        from shadowcypher.modules.chaos import chaos
        chaos.stop()
        self.pod_status.set_value("Stopped")
        self.pod_threads.set_value("0")
        self.header.set_active(False)
        self.log("Stopped.", "success")

    def _auto_stop(self):
        from shadowcypher.modules.chaos import chaos
        if chaos.active:
            chaos.stop()
        GLib.idle_add(self.pod_status.set_value, "Idle")
        GLib.idle_add(self.pod_threads.set_value, "0")
        GLib.idle_add(self.header.set_active, False)
        self.log("Stress test complete.", "success")
        return False

    def _on_forge_click(self, btn):
        import threading

        from shadowcypher.core.sanitize import validate_target
        from shadowcypher.modules.web_forge import web_forge

        exploit_type = self.forge_combo.get_active_id()
        if not exploit_type:
            self.log("ERROR: Select an exploit type", "error")
            return

        target = self.target_entry.get_text().strip()
        if not target:
            self.log("ERROR: Specify a target URL/host in the Target field", "error")
            return
        if not validate_target(target):
            self.log(f"Invalid target: {target}", "error")
            return

        def cb(line):
            GLib.idle_add(self.log, str(line), "system")

        dispatch = {
            "xss":       lambda: web_forge.xss_scan(target, cb),
            "csrf":      lambda: web_forge.csrf_generate(target, "POST", cb),
            "clickjack": lambda: web_forge.clickjack_test(target, cb),
            "cors":      lambda: web_forge.cors_test(target, cb),
            "headers":   lambda: web_forge.header_audit(target, cb),
            "subdomain": lambda: web_forge.subdomain_takeover(target, cb),
            "lfi":       lambda: web_forge.lfi_scan(target, "id", cb),
            "redirect":  lambda: web_forge.open_redirect_scan(target, "url", cb),
        }
        handler = dispatch.get(exploit_type)
        if not handler:
            self.log(f"Unknown test type: {exploit_type}", "error")
            return

        self.log(f"Running {exploit_type} test → {target}", "ai")
        threading.Thread(target=handler, daemon=True).start()
