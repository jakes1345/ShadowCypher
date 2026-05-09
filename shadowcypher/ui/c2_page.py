"""C2 Session Manager — Command & Control Listener + Active Session Console."""

import threading
import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from shadowcypher.ui.base_page import BasePage
from shadowcypher.ui.components import DataPod
from shadowcypher.modules.c2 import C2Framework

c2 = C2Framework()


class C2Page(BasePage):
    def __init__(self):
        super().__init__("C2 COMMAND CENTER")
        self._selected_session: str | None = None
        self._poll_active = False
        self._build_ui()
        self._start_poll()
        self.connect("unrealize", lambda _: setattr(self, "_poll_active", False))

    # ── Metric pods ──────────────────────────────────────────────────────────

    def _build_ui(self):
        self.pod_status   = DataPod("LISTENER",    "OFFLINE", "red")
        self.pod_sessions = DataPod("SESSIONS",    "0")
        self.pod_proto    = DataPod("PROTOCOL",    "—")
        self.pod_port     = DataPod("PORT",        "—")
        for pod in [self.pod_status, self.pod_sessions, self.pod_proto, self.pod_port]:
            self.metric_strip.pack_start(pod, True, True, 5)

        # ── Listener controls ────────────────────────────────────────────────
        listener_frame = Gtk.Frame(label="LISTENER CONTROL")
        lbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lbox.set_margin_top(10); lbox.set_margin_bottom(10)
        lbox.set_margin_start(10); lbox.set_margin_end(10)

        row1 = Gtk.Box(spacing=8)
        row1.pack_start(Gtk.Label(label="Port:"), False, False, 0)
        self.port_entry = Gtk.Entry(text="8443")
        self.port_entry.set_width_chars(7)
        row1.pack_start(self.port_entry, False, False, 0)

        row1.pack_start(Gtk.Label(label="Protocol:"), False, False, 0)
        self.proto_combo = Gtk.ComboBoxText()
        self.proto_combo.append("https", "HTTPS (TLS)")
        self.proto_combo.append("http",  "HTTP (plain)")
        self.proto_combo.set_active(0)
        row1.pack_start(self.proto_combo, False, False, 0)

        self.start_btn = self.make_action_btn("▶ START LISTENER", self._on_start, "suggested-action")
        self.stop_btn  = self.make_action_btn("■ STOP",           self._on_stop,  "destructive-action")
        self.stop_btn.set_sensitive(False)
        row1.pack_start(self.start_btn, False, False, 0)
        row1.pack_start(self.stop_btn,  False, False, 0)
        lbox.pack_start(row1, False, False, 0)

        # Payload generator row
        row2 = Gtk.Box(spacing=8)
        row2.pack_start(Gtk.Label(label="LHOST:"), False, False, 0)
        self.lhost_entry = Gtk.Entry(placeholder_text="attacker IP")
        self.lhost_entry.set_width_chars(15)
        row2.pack_start(self.lhost_entry, False, False, 0)

        row2.pack_start(Gtk.Label(label="Platform:"), False, False, 0)
        self.platform_combo = Gtk.ComboBoxText()
        self.platform_combo.append("linux",   "Linux (Python)")
        self.platform_combo.append("windows", "Windows (PowerShell)")
        self.platform_combo.append("msfvenom", "msfvenom (ELF/EXE)")
        self.platform_combo.set_active(0)
        row2.pack_start(self.platform_combo, False, False, 0)

        gen_btn = self.make_action_btn("⚡ GENERATE PAYLOAD", self._on_gen_payload)
        row2.pack_start(gen_btn, False, False, 0)
        lbox.pack_start(row2, False, False, 0)

        listener_frame.add(lbox)
        self.workspace.pack_start(listener_frame, False, False, 0)

        # ── Session panel (left = list, right = interaction) ─────────────────
        session_pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        session_pane.set_position(280)

        # Session list
        sess_frame = Gtk.Frame(label="ACTIVE SESSIONS")
        sess_scroll = Gtk.ScrolledWindow()
        sess_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sess_scroll.set_min_content_height(160)

        self.session_store = Gtk.ListStore(str, str, str, str, str)
        # cols: session_id, remote_ip, hostname, os_type, last_seen_str
        self.session_view = Gtk.TreeView(model=self.session_store)
        self.session_view.set_headers_visible(True)
        for i, title in enumerate(["ID", "IP", "Host", "OS", "Last Seen"]):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
            col.set_resizable(True)
            self.session_view.append_column(col)
        self.session_view.get_selection().connect("changed", self._on_session_select)

        sess_scroll.add(self.session_view)
        sess_frame.add(sess_scroll)

        sess_btn_row = Gtk.Box(spacing=6)
        sess_btn_row.set_margin_top(4)
        kill_btn = self.make_action_btn("✕ Kill Session", self._on_kill_session, "destructive-action")
        sess_btn_row.pack_start(kill_btn, False, False, 0)

        sess_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sess_left.pack_start(sess_frame, True, True, 0)
        sess_left.pack_start(sess_btn_row, False, False, 0)
        session_pane.add1(sess_left)

        # Interaction panel
        interact_frame = Gtk.Frame(label="SESSION INTERACTION")
        interact_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        interact_box.set_margin_start(8); interact_box.set_margin_end(8)
        interact_box.set_margin_top(8); interact_box.set_margin_bottom(8)

        # Output view
        out_scroll = Gtk.ScrolledWindow()
        out_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        out_scroll.set_min_content_height(120)
        self.output_buf = Gtk.TextBuffer()
        self.output_view = Gtk.TextView(buffer=self.output_buf)
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.modify_font(Pango.FontDescription("Monospace 9"))
        out_scroll.add(self.output_view)
        interact_box.pack_start(out_scroll, True, True, 0)

        # Command entry
        cmd_row = Gtk.Box(spacing=6)
        self.cmd_lbl = Gtk.Label(label="[no session]")
        self.cmd_lbl.set_halign(Gtk.Align.START)
        self.cmd_lbl.set_width_chars(12)
        cmd_row.pack_start(self.cmd_lbl, False, False, 0)

        self.cmd_entry = Gtk.Entry(placeholder_text="shell command...")
        self.cmd_entry.connect("activate", self._on_send_cmd)
        cmd_row.pack_start(self.cmd_entry, True, True, 0)

        send_btn = self.make_action_btn("SEND ↵", self._on_send_cmd)
        cmd_row.pack_start(send_btn, False, False, 0)

        interact_box.pack_start(cmd_row, False, False, 0)
        interact_frame.add(interact_box)
        session_pane.add2(interact_frame)

        self.workspace.pack_start(session_pane, True, True, 0)

    # ── Listener start/stop ──────────────────────────────────────────────────

    def _on_start(self, _btn):
        try:
            port = int(self.port_entry.get_text().strip() or "8443")
        except ValueError:
            self.log("[ERROR] Port must be a number", "ERROR")
            return

        proto = self.proto_combo.get_active_id() or "https"
        self.log(f"[C2] Starting {proto.upper()} listener on port {port}...", "APEX")

        def _do():
            ok = c2.start_listener(port=port, protocol=proto, on_output=lambda m: self.log(m))
            GLib.idle_add(self._on_listener_started, ok, proto, port)

        threading.Thread(target=_do, daemon=True).start()

    def _on_listener_started(self, ok: bool, proto: str, port: int):
        if ok:
            self.pod_status.update("ONLINE", "green")
            self.pod_proto.update(proto.upper())
            self.pod_port.update(str(port))
            self.start_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(True)
            self.header.set_active(True)
            self.log(f"[C2] Listener ACTIVE on {proto}://0.0.0.0:{port}", "SUCCESS")
        else:
            self.log("[C2] Failed to start listener — port in use?", "ERROR")

    def _on_stop(self, _btn):
        c2.stop_listener(on_output=lambda m: self.log(m))
        self.pod_status.update("OFFLINE", "red")
        self.pod_proto.update("—")
        self.pod_port.update("—")
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.header.set_active(False)
        self.log("[C2] Listener stopped.", "SYSTEM")

    # ── Payload generation ───────────────────────────────────────────────────

    def _on_gen_payload(self, _btn):
        lhost = self.lhost_entry.get_text().strip()
        if not lhost:
            self.log("[ERROR] Enter LHOST (attacker IP)", "ERROR")
            return
        try:
            port = int(self.port_entry.get_text().strip() or "8443")
        except ValueError:
            port = 8443

        plat = self.platform_combo.get_active_id() or "linux"
        self.log(f"[PAYLOAD] Generating {plat} agent for {lhost}:{port}...", "APEX")

        def _do():
            try:
                result = C2Framework.generate_payload(
                    lhost, port,
                    payload_type="msfvenom" if plat == "msfvenom" else "reverse_shell",
                    platform=plat if plat != "msfvenom" else "linux",
                    on_output=lambda m: self.log(m),
                )
                if result:
                    # Write to /tmp for easy retrieval
                    import os
                    out = f"/tmp/c2_agent_{plat}_{port}.{'py' if plat == 'linux' else 'ps1' if plat == 'windows' else 'bin'}"
                    if plat != "msfvenom":
                        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                        with os.fdopen(fd, "w") as f:
                            f.write(result)
                    else:
                        out = result
                    self.log(f"[PAYLOAD] Written to: {out}", "SUCCESS")
            except RuntimeError as e:
                self.log(f"[PAYLOAD] {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    # ── Session management ───────────────────────────────────────────────────

    def _on_session_select(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self._selected_session = None
            self.cmd_lbl.set_text("[no session]")
            return
        self._selected_session = model[treeiter][0]
        self.cmd_lbl.set_text(f"[{self._selected_session}]")
        self._refresh_output()

    def _on_send_cmd(self, _widget):
        if not self._selected_session:
            self.log("[ERROR] No session selected", "ERROR")
            return
        cmd = self.cmd_entry.get_text().strip()
        if not cmd:
            return
        ok = c2.interact(self._selected_session, cmd, on_output=lambda m: self.log(m))
        if ok:
            self.log(f"[>] {self._selected_session}: {cmd}", "APEX")
            self.cmd_entry.set_text("")
        else:
            self.log(f"[ERROR] Session {self._selected_session} gone", "ERROR")
            self._selected_session = None

    def _on_kill_session(self, _btn):
        if not self._selected_session:
            self.log("[ERROR] No session selected", "ERROR")
            return
        c2.kill_session(self._selected_session, on_output=lambda m: self.log(m))
        self._selected_session = None
        self.cmd_lbl.set_text("[no session]")

    def _refresh_output(self):
        if not self._selected_session:
            return
        history = c2.get_output(self._selected_session)
        if not history:
            return
        lines = []
        for entry in history:
            ts = time.strftime("%H:%M:%S", time.localtime(entry["time"]))
            data = entry.get("data", {})
            if isinstance(data, dict):
                out = data.get("output") or data.get("raw") or str(data)
                cmd_name = data.get("cmd", "")
                lines.append(f"[{ts}] CMD: {cmd_name}\n{out}")
            else:
                lines.append(f"[{ts}] {data}")
        GLib.idle_add(self._set_output_text, "\n".join(lines))

    def _set_output_text(self, text: str):
        self.output_buf.set_text(text)
        end = self.output_buf.get_end_iter()
        self.output_view.scroll_to_iter(end, 0.0, False, 0.0, 1.0)

    # ── Background poll (refresh sessions every 3s) ──────────────────────────

    def _start_poll(self):
        self._poll_active = True
        GLib.timeout_add(3000, self._poll_sessions)

    def _poll_sessions(self) -> bool:
        sessions = c2.list_sessions()
        self.pod_sessions.update(str(len(sessions)))
        self.session_store.clear()
        for s in sessions:
            last = time.strftime("%H:%M:%S", time.localtime(s["last_seen"]))
            self.session_store.append([
                s["session_id"],
                s["remote_ip"],
                s.get("hostname", ""),
                s.get("os_type", ""),
                last,
            ])
        # Refresh output for selected session
        if self._selected_session:
            self._refresh_output()
        return self._poll_active
