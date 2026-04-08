"""ShadowCypher Tactical AI Swarm — Global AI Resuscitation Build V13."""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
from shadowcypher.ai.orchestrator import AIOrchestrator
from shadowcypher.core.logger import logger
import threading


class AIPage(Gtk.Box):
    """Elite Tactical AI interface. Features live terminal logs and local-AI health checks."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.orchestrator = AIOrchestrator()
        self._build_ui()

    def _build_ui(self):
        # ── TACTICAL WORKSPACE (Obsidian Pod) ──
        self.main_pod = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_pod.get_style_context().add_class("card")
        self.pack_start(self.main_pod, True, True, 0)

        # 1. AI STATUS HUB
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_lbl = Gtk.Label(label="\U0001f916 TENGU AI SWARM: ACTIVE_PULSE")
        status_lbl.get_style_context().add_class("app-title")
        status_box.pack_start(status_lbl, False, False, 0)
        self.main_pod.pack_start(status_box, False, False, 0)

        # 2. LOG FEED (Tactical Terminal)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.get_style_context().add_class("terminal-view")
        self.log_view.set_size_request(-1, 400)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.log_view)
        self.main_pod.pack_start(scroll, True, True, 0)

        # 3. INTERACTION HUB (Chat Style)
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        self.msg_entry = Gtk.Entry()
        self.msg_entry.set_placeholder_text("EXECUTE_AI_QUERY...")
        self.msg_entry.connect("activate", self._on_send_clicked)
        input_box.pack_start(self.msg_entry, True, True, 0)

        btn_send = Gtk.Button(label="ENGAGE")
        btn_send.get_style_context().add_class("suggested-action")
        btn_send.connect("clicked", self._on_send_clicked)
        input_box.pack_end(btn_send, False, False, 0)

        # 4. MASTERCLASS QUICK TRIGGER
        btn_masterclass = Gtk.Button(label="LAUNCH_MASTERCLASS")
        btn_masterclass.get_style_context().add_class("destructive-action")
        btn_masterclass.get_style_context().add_class("pulse-animation")
        btn_masterclass.connect("clicked", self._on_masterclass_clicked)
        input_box.pack_end(btn_masterclass, False, False, 10)

        self.main_pod.pack_start(input_box, False, False, 0)

        self._log_terminal("[SYSTEM] TENGU_CORE_ONLINE...")
        self._log_terminal("[SYSTEM] MASTERCLASS_LOOP_CALIBRATED...")

    def _on_masterclass_clicked(self, widget):
        msg = self.msg_entry.get_text()
        if not msg:
            self._log_terminal(
                "[WARN] SPECIFY_TARGET_IP_IN_QUERY_FIELD_BEFORE_MASTERCLASS"
            )
            return
        self._log_terminal(f"[CRITICAL] INITIATING_FULL_OFFENSIVE_AUDIT_ON: {msg}")
        # Send the special tool command
        import json

        safe_target = json.dumps(msg)
        masterclass_query = f'<TOOL_CALL>{{"tool": "run_masterclass", "args": {{"target": {safe_target}}}}}</TOOL_CALL>'
        threading.Thread(
            target=self._run_ai_swarm, args=(masterclass_query,), daemon=True
        ).start()

    def _log_terminal(self, text):
        buf = self.log_view.get_buffer()
        buf.insert(buf.get_end_iter(), f"{text}\n")
        self.log_view.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)

    def _on_send_clicked(self, widget):
        msg = self.msg_entry.get_text()
        if not msg:
            return
        self.msg_entry.set_text("")
        self.msg_entry.set_sensitive(False)
        # We need a reference to the button for lockdown
        # (Assuming widget is the entry or the button)
        self._log_terminal(f"USER >> {msg}")
        # Run AI Swarm in background
        threading.Thread(target=self._run_ai_swarm, args=(msg,), daemon=True).start()

    def _run_ai_swarm(self, query):
        try:
            # Atomic Callback for Progress Feed
            def hb(txt):
                GLib.idle_add(self._log_terminal, txt)

            hb("[TENGU] INITIATING_AUTONOMOUS_ORCHESTRATION...")
            # Real call with Callback Support
            response = self.orchestrator.execute_query(query, callback=hb)
            hb(f"TENGU >> {response}")
        except Exception as e:
            GLib.idle_add(self._log_terminal, f"[ERROR] SWARM_FAILURE: {str(e)}")
            GLib.idle_add(
                self._log_terminal, "[VITAL] ENSURE 'OLLAMA SERVE' IS RUNNING"
            )
        finally:
            # Unlock Inputs
            GLib.idle_add(self.msg_entry.set_sensitive, True)
            GLib.idle_add(self.msg_entry.grab_focus)
