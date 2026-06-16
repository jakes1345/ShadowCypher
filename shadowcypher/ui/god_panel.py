"""
God-Panel — Real-time Sovereign Orchestration & Full-Spectrum System Control.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import time
import psutil
import socket
import threading

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.config import config
from shadowcypher.core.bus import bus
from shadowcypher.core.logger import logger


class GodPanel(BasePage):
    """Master control panel — live subsystem matrix with kill-switch access."""

    def __init__(self):
        super().__init__("\U0001f9e0 GOD-PANEL: LATENT MATRIX")
        from shadowcypher.ui.components import DataPod

        self.pod_cpu = DataPod("CPU", "0%", "cyan")
        self.pod_mem = DataPod("RAM", "0%", "violet")
        self.pod_ai = DataPod("AI_CORE", "INIT", "amber")
        self.pod_relay = DataPod("GO_RELAY", "SYNC", "cyan")
        self.pod_chat = DataPod("SOV_CHAT", "IDLE", "green")
        self.pod_swarm = DataPod("SWARM", "0", "red")
        for pod in [self.pod_cpu, self.pod_mem, self.pod_ai, self.pod_relay, self.pod_chat, self.pod_swarm]:
            self.metric_strip.pack_start(pod, True, True, 0)

        # Subsystem Matrix
        frm = Gtk.Frame(label="SUBSYSTEM MATRIX")
        self.matrix_store = Gtk.ListStore(str, str, str, str)
        tree = Gtk.TreeView(model=self.matrix_store)
        tree.get_style_context().add_class("node-list")
        for i, t in enumerate(["SUBSYSTEM", "STATUS", "LATENCY", "ENDPOINT"]):
            tree.append_column(Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i))
        sw = Gtk.ScrolledWindow()
        sw.set_min_content_height(200)
        sw.add(tree)
        bx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        bx.set_margin_start(10)
        bx.set_margin_end(10)
        bx.set_margin_top(10)
        bx.set_margin_bottom(10)
        bx.pack_start(sw, True, True, 0)
        btn = Gtk.Button(label="⚡ Synchronize Subsystems")
        btn.connect("clicked", lambda _: threading.Thread(target=self._refresh_matrix, daemon=True).start())
        bx.pack_start(btn, False, False, 5)
        frm.add(bx)
        self.workspace.pack_start(frm, True, True, 0)

        # AI Model Control
        frm2 = Gtk.Frame(label="AI ENGINE CONTROL")
        row = Gtk.Box(spacing=10)
        row.set_margin_start(10)
        row.set_margin_end(10)
        row.set_margin_top(10)
        row.set_margin_bottom(10)
        self.model_entry = Gtk.Entry()
        self.model_entry.set_placeholder_text("e.g. claude-haiku-4-5-20251001 or llama3.1:8b")
        self.model_entry.set_text(config.get("ai", "model", default="claude-haiku-4-5-20251001"))
        row.pack_start(self.model_entry, True, True, 0)
        btn_sw = Gtk.Button(label="Switch Model")
        btn_sw.get_style_context().add_class("suggested-action")
        btn_sw.connect("clicked", self._on_switch_model)
        row.pack_start(btn_sw, False, False, 0)
        frm2.add(row)
        self.workspace.pack_start(frm2, False, False, 0)

        # Integrity
        frm3 = Gtk.Frame(label="INTEGRITY STATUS")
        bx3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        bx3.set_margin_start(10)
        bx3.set_margin_end(10)
        bx3.set_margin_top(10)
        bx3.set_margin_bottom(10)
        self.integrity_label = Gtk.Label()
        self.integrity_label.set_line_wrap(True)
        self.integrity_label.set_xalign(0)
        bx3.pack_start(self.integrity_label, False, False, 0)
        btn_rh = Gtk.Button(label="Regenerate Baseline")
        btn_rh.connect("clicked", self._on_rehash)
        bx3.pack_start(btn_rh, False, False, 5)
        frm3.add(bx3)
        self.intel_sidebar.pack_start(frm3, False, False, 0)

        self._tick_id = GLib.timeout_add(3000, self._tick)
        self.connect("unrealize", lambda _: GLib.source_remove(self._tick_id) if self._tick_id else None)
        threading.Thread(target=self._refresh_matrix, daemon=True).start()

    def _refresh_matrix(self):
        """Asynchronous full-spectrum subsystem matrix refresh."""
        import urllib.request
        import time as _time
        results = []

        # Port-based service checks: (label, port, http_url_or_None)
        port_checks = [
            ("Ollama AI",   11434, "http://127.0.0.1:11434/api/tags"),
            ("Go Relay",    8888,  None),
            ("Nexus Relay", 9988,  None),
            ("Ghost C2",    44444, None),
            ("Tor SOCKS5",  9050,  None),
        ]
        for name, port, url in port_checks:
            t0 = _time.monotonic()
            try:
                if url:
                    urllib.request.urlopen(url, timeout=1)
                else:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        pass
                rtt = f"{((_time.monotonic() - t0) * 1000):.0f}ms"
                results.append([name, "ONLINE", rtt, str(port)])
            except Exception:
                results.append([name, "OFFLINE", "—", str(port)])

        # Sisyphus integrity sentinel
        try:
            from shadowcypher.ai.sisyphus import sisyphus
            state = "STABLE" if sisyphus.is_stable else "TAMPERED"
            results.append(["Sisyphus", state, "—", "—"])
        except Exception:
            results.append(["Sisyphus", "ERROR", "—", "—"])

        # CVE Feed
        try:
            from shadowcypher.modules.cve_feed import cve_feed
            active = getattr(cve_feed, "_active", False) or getattr(cve_feed, "running", False)
            results.append(["CVE Feed", "ACTIVE" if active else "IDLE", "—", "NVD"])
        except Exception:
            results.append(["CVE Feed", "UNAVAIL", "—", "—"])

        # Knowledge Graph
        try:
            from shadowcypher.core.knowledge_graph import kg
            stats = kg.stats()
            results.append(["Knowledge Graph", f"{stats.get('nodes', 0)} nodes", "—", "—"])
        except Exception:
            results.append(["Knowledge Graph", "UNAVAIL", "—", "—"])

        # Ghost nodes
        try:
            from shadowcypher.core.ghost import ghost_orchestrator
            node_count = len(ghost_orchestrator.get_active_nodes())
            results.append(["Shadow Nodes", f"{node_count} linked", "—", "44444"])
        except Exception:
            results.append(["Shadow Nodes", "0 linked", "—", "44444"])

        def _update_ui():
            self.matrix_store.clear()
            online = sum(1 for r in results if r[1] in ("ONLINE", "STABLE", "ACTIVE"))
            for r in results:
                self.matrix_store.append(r)
                lbl = r[0]
                if lbl == "Ollama AI":
                    self.pod_ai.set_value(r[1])
                elif lbl == "Go Relay":
                    self.pod_relay.set_value(r[1])
                elif lbl == "Shadow Nodes":
                    self.pod_swarm.set_value(r[1])
            self.pod_chat.set_value(f"{online}/{len(results)}")
            return False

        GLib.idle_add(_update_ui)

    def _tick(self):
        if not self.get_mapped():
            return True
        try:
            self.pod_cpu.set_value(f"{psutil.cpu_percent():.0f}%")
            self.pod_mem.set_value(f"{psutil.virtual_memory().percent:.0f}%")
            try:
                from shadowcypher.ai.sisyphus import sisyphus
                s = "✅ STABLE" if sisyphus.is_stable else "⚠️ TAMPERED"
                self.integrity_label.set_markup(f"<span color='{'#10b981' if sisyphus.is_stable else '#f43f5e'}'>{s}</span>")
            except Exception:
                pass
        except Exception:
            pass
        return True

    def _on_switch_model(self, btn):
        model = self.model_entry.get_text().strip()
        if not model:
            return
        self.log(f"Switching to: {model}", "APEX")
        def _sw():
            from shadowcypher.ai.engine import ai_engine
            ok = ai_engine.switch_model(model, on_progress=lambda m: GLib.idle_add(self.log, m, "INFO"))
            if ok:
                config.set("ai", "model", model)
                GLib.idle_add(self.log, f"Switched to {model}", "SUCCESS")
            else:
                GLib.idle_add(self.log, f"Failed: {model}", "ERROR")
        threading.Thread(target=_sw, daemon=True).start()

    def _on_rehash(self, btn):
        self.log("Regenerating integrity baseline...", "INFO")
        def _rh():
            try:
                from shadowcypher.ai.sisyphus import sisyphus
                sisyphus.generate_baseline()
                GLib.idle_add(self.log, "Baseline regenerated.", "SUCCESS")
            except Exception as e:
                GLib.idle_add(self.log, f"Rehash failed: {e}", "ERROR")
        threading.Thread(target=_rh, daemon=True).start()
