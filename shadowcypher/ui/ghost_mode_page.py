"""
Ghost Mode Page — Total Operational Invisibility Control Panel.
Wraps ghost_mode.py and tor_cloak.py into the app UI.
All offensive tools should check stealth.active before firing.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango
import threading
import os
import socket
import json
import time

from shadowcypher.ui.base_page import BasePage
from shadowcypher.core.logger import logger
from shadowcypher.core.stealth import stealth
from shadowcypher.core.bus import bus


def _ghost_active() -> bool:
    return os.path.exists("/tmp/.ghost_mode_state")


def _tor_alive() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", 9050)) == 0
        s.close()
        return result
    except Exception:
        return False


class GhostModePage(BasePage):
    def __init__(self):
        super().__init__("\U0001f47a GHOST MODE — OPERATIONAL INVISIBILITY")

        # ── Status strip ──
        from shadowcypher.ui.components import DataPod
        self.pod_ghost  = DataPod("GHOST_MODE",   "INACTIVE", "red")
        self.pod_tor    = DataPod("TOR_CIRCUIT",  "DOWN",     "red")
        self.pod_dns    = DataPod("DNS_LEAK",     "UNKNOWN",  "amber")
        self.pod_mac    = DataPod("MAC_SPOOF",    "OFF",      "amber")
        for pod in [self.pod_ghost, self.pod_tor, self.pod_dns, self.pod_mac]:
            self.metric_strip.pack_start(pod, True, True, 0)

        # ── Main layout ──
        hbox = Gtk.Box(spacing=16)
        self.workspace.pack_start(hbox, True, True, 0)

        # Left: controls
        ctrl_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        ctrl_col.set_size_request(320, -1)
        hbox.pack_start(ctrl_col, False, False, 0)

        # Ghost Mode engage/disengage
        ghost_frame = Gtk.Frame(label="GHOST MODE (8-Layer OPSEC)")
        ghost_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        ghost_box.set_margin_top(10)
        ghost_box.set_margin_bottom(10)
        ghost_box.set_margin_start(10)
        ghost_box.set_margin_end(10)

        desc = Gtk.Label()
        desc.set_markup(
            "<span size='small' color='#94a3b8'>"
            "MAC randomization · Hostname wipe · Tor routing\n"
            "Iptables kill-switch · DNS via Tor · RAM workspace\n"
            "Log suppression · Auto-restore on disengage"
            "</span>"
        )
        desc.set_line_wrap(True)
        desc.set_xalign(0)
        ghost_box.pack_start(desc, False, False, 0)

        self.engage_btn = Gtk.Button(label="⚡ ENGAGE GHOST MODE")
        self.engage_btn.get_style_context().add_class("destructive-action")
        self.engage_btn.connect("clicked", self._on_engage)
        ghost_box.pack_start(self.engage_btn, False, False, 0)

        self.disengage_btn = Gtk.Button(label="↩ DISENGAGE (Restore)")
        self.disengage_btn.set_sensitive(False)
        self.disengage_btn.connect("clicked", self._on_disengage)
        ghost_box.pack_start(self.disengage_btn, False, False, 0)

        root_warn = Gtk.Label()
        root_warn.set_markup("<span size='x-small' color='#f59e0b'>⚠ Requires sudo/root for full effect</span>")
        root_warn.set_xalign(0)
        ghost_box.pack_start(root_warn, False, False, 0)

        ghost_frame.add(ghost_box)
        ctrl_col.pack_start(ghost_frame, False, False, 0)

        # Tor controls
        tor_frame = Gtk.Frame(label="TOR CIRCUIT")
        tor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tor_box.set_margin_top(10)
        tor_box.set_margin_bottom(10)
        tor_box.set_margin_start(10)
        tor_box.set_margin_end(10)

        self.tor_start_btn = Gtk.Button(label="▶ Start Tor")
        self.tor_start_btn.connect("clicked", self._on_tor_start)
        tor_box.pack_start(self.tor_start_btn, False, False, 0)

        self.tor_rotate_btn = Gtk.Button(label="🔄 Rotate Circuit (New IP)")
        self.tor_rotate_btn.connect("clicked", self._on_tor_rotate)
        tor_box.pack_start(self.tor_rotate_btn, False, False, 0)

        self.verify_btn = Gtk.Button(label="🔍 Verify Anonymity")
        self.verify_btn.connect("clicked", self._on_verify)
        tor_box.pack_start(self.verify_btn, False, False, 0)

        tor_frame.add(tor_box)
        ctrl_col.pack_start(tor_frame, False, False, 0)

        # Quick hardening
        harden_frame = Gtk.Frame(label="QUICK HARDENING")
        harden_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        harden_box.set_margin_top(10)
        harden_box.set_margin_bottom(10)
        harden_box.set_margin_start(10)
        harden_box.set_margin_end(10)

        self.harden_btn = Gtk.Button(label="🛡 Run Leak Assessment")
        self.harden_btn.connect("clicked", self._on_harden)
        harden_box.pack_start(self.harden_btn, False, False, 0)

        self.workspace_btn = Gtk.Button(label="💾 Open RAM Workspace")
        self.workspace_btn.connect("clicked", self._on_workspace)
        harden_box.pack_start(self.workspace_btn, False, False, 0)

        harden_frame.add(harden_box)
        ctrl_col.pack_start(harden_frame, False, False, 0)

        # Right: output console
        console_frame = Gtk.Frame(label="GHOST CONSOLE")
        console_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.console = Gtk.TextView()
        self.console.set_editable(False)
        self.console.set_cursor_visible(False)
        self.console.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.console.get_style_context().add_class("terminal-view")

        font = Pango.FontDescription("JetBrains Mono 9")
        self.console.override_font(font)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.console)
        console_box.pack_start(scroll, True, True, 0)

        clear_btn = Gtk.Button(label="Clear")
        clear_btn.set_halign(Gtk.Align.END)
        clear_btn.set_margin_top(4)
        clear_btn.set_margin_end(4)
        clear_btn.connect("clicked", lambda _: self.console.get_buffer().set_text(""))
        console_box.pack_start(clear_btn, False, False, 0)

        console_frame.add(console_box)
        hbox.pack_start(console_frame, True, True, 0)

        # Periodic status refresh when page is visible
        self._status_timer_id = None
        self.connect("map", lambda _: self._start_status_poll())
        self.connect("unmap", lambda _: self._stop_status_poll())

        # Initial status check
        GLib.idle_add(self._refresh_status)
        self._log("Ghost Mode control panel ready.")
        self._log("Run 'Verify Anonymity' to check your current exposure.")

    # ── Status polling ────────────────────────────────────────

    def _start_status_poll(self):
        if self._status_timer_id is None:
            self._status_timer_id = GLib.timeout_add(4000, self._refresh_status)

    def _stop_status_poll(self):
        if self._status_timer_id is not None:
            GLib.source_remove(self._status_timer_id)
            self._status_timer_id = None

    def _refresh_status(self):
        ghost = _ghost_active()
        tor   = _tor_alive()
        is_root = os.geteuid() == 0

        self.engage_btn.set_sensitive(not ghost)
        self.disengage_btn.set_sensitive(ghost)

        # Ghost pod
        if ghost and tor:
            self.pod_ghost.update("ACTIVE", "green")
        elif ghost:
            self.pod_ghost.update("PARTIAL", "amber")
        else:
            self.pod_ghost.update("INACTIVE", "red")

        # Tor pod
        self.pod_tor.update("UP" if tor else "DOWN", "green" if tor else "red")

        # DNS leak check (quick)
        try:
            with open("/etc/resolv.conf") as f:
                dns = f.read()
            if "Ghost Mode" in dns and "127.0.0.1" in dns:
                self.pod_dns.update("SECURED", "green")
            else:
                self.pod_dns.update("EXPOSED", "red")
        except Exception:
            self.pod_dns.update("UNKNOWN", "amber")

        # MAC check — first non-loopback iface, check locally-administered bit
        try:
            import subprocess, re
            out = subprocess.check_output(["ip", "-o", "link", "show"], text=True, timeout=2)
            for line in out.splitlines():
                m = re.search(r"(\w+): .+link/ether\s+([0-9a-f:]{17})", line)
                if m and m.group(1) != "lo":
                    first_byte = int(m.group(2).split(":")[0], 16)
                    randomized = bool(first_byte & 0x02)
                    self.pod_mac.update("RANDOM" if randomized else "REAL",
                                        "green" if randomized else "red")
                    break
        except Exception:
            self.pod_mac.update("UNKNOWN", "amber")

        return True  # keep timer alive

    # ── Console helper ────────────────────────────────────────

    def _log(self, text: str):
        def _do():
            buf = self.console.get_buffer()
            ts  = time.strftime("%H:%M:%S")
            buf.insert(buf.get_end_iter(), f"[{ts}] {text}\n")
            buf.place_cursor(buf.get_end_iter())
            self.console.scroll_to_mark(buf.get_insert(), 0.0, True, 0.0, 1.0)
        GLib.idle_add(_do)

    def _run_script(self, args: list, label: str):
        """Run a ghost_mode.py or tor_cloak.py command in a thread, stream to console."""
        import subprocess, shutil, sys

        script_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        script_map = {
            "ghost": os.path.join(script_dir, "ghost_mode.py"),
            "tor":   os.path.join(script_dir, "tor_cloak.py"),
        }
        script = script_map.get(args[0])
        if not script or not os.path.exists(script):
            self._log(f"[ERROR] Script not found: {args[0]}")
            return

        cmd = [sys.executable, script] + args[1:]
        # Prepend sudo if not root and operation needs it
        needs_root = args[1] in ("engage", "disengage", "harden") if len(args) > 1 else False
        if needs_root and os.geteuid() != 0:
            if shutil.which("pkexec"):
                cmd = ["pkexec"] + cmd
            elif shutil.which("sudo"):
                cmd = ["sudo"] + cmd

        self._log(f"[{label}] Running: {' '.join(cmd[1:])}")

        def _worker():
            try:
                import re
                ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    clean = ansi_escape.sub("", line.rstrip())
                    if clean:
                        self._log(clean)
                proc.wait()
                self._log(f"[{label}] Done (exit {proc.returncode})")
                GLib.idle_add(self._refresh_status)
                bus.publish("ghost_mode_changed", {"active": _ghost_active()})
            except Exception as e:
                self._log(f"[ERROR] {e}")

        threading.Thread(target=_worker, daemon=True, name=f"ghost-{label}").start()

    # ── Button handlers ───────────────────────────────────────

    def _on_engage(self, _btn):
        self.engage_btn.set_sensitive(False)
        self._log("Engaging Ghost Mode — all 8 layers...")
        self._run_script(["ghost", "engage"], "ENGAGE")

    def _on_disengage(self, _btn):
        self.disengage_btn.set_sensitive(False)
        self._log("Disengaging Ghost Mode — restoring system state...")
        self._run_script(["ghost", "disengage"], "DISENGAGE")

    def _on_tor_start(self, _btn):
        self._log("Starting Tor service...")
        self._run_script(["tor", "start"], "TOR")

    def _on_tor_rotate(self, _btn):
        self._log("Rotating Tor circuit (requesting new exit IP)...")
        self._run_script(["tor", "rotate"], "CIRCUIT")

    def _on_verify(self, _btn):
        self._log("Verifying anonymity — checking real vs Tor IP...")
        self._run_script(["tor", "status"], "VERIFY")

    def _on_harden(self, _btn):
        self._log("Running full leak assessment...")
        self._run_script(["tor", "harden"], "HARDEN")

    def _on_workspace(self, _btn):
        self._log("Opening RAM-only workspace in terminal...")
        import subprocess, shutil, sys, os as _os
        script = _os.path.join(_os.path.dirname(__file__), "..", "scripts", "ghost_mode.py")
        term = shutil.which("xterm") or shutil.which("gnome-terminal") or shutil.which("konsole")
        if term:
            subprocess.Popen([term, "-e", f"sudo {sys.executable} {script} workspace"])
        else:
            self._log("[ERROR] No terminal emulator found (xterm/gnome-terminal/konsole)")
