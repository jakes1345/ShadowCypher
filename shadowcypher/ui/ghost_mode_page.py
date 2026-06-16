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
    return os.path.exists("/tmp/.ghost_mode_state")  # nosec B108


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

        # Identity coverage status
        id_frame = Gtk.Frame(label="IDENTITY COVERAGE")
        id_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        id_box.set_margin_top(8)
        id_box.set_margin_bottom(8)
        id_box.set_margin_start(10)
        id_box.set_margin_end(10)

        self._id_rows: dict = {}
        for key, label in [
            ("ip",      "IP address"),
            ("mac",     "MAC address"),
            ("hostname","Hostname"),
            ("dns",     "DNS queries"),
            ("ja3",     "TLS/JA3 fingerprint"),
            ("browser", "Browser fingerprint"),
        ]:
            row = Gtk.Box(spacing=6)
            dot = Gtk.Label(label="●")
            dot.get_style_context().add_class("dim-label")
            lbl = Gtk.Label(label=label, xalign=0)
            lbl.set_hexpand(True)
            status = Gtk.Label(label="?", xalign=1)
            status.get_style_context().add_class("dim-label")
            row.pack_start(dot, False, False, 0)
            row.pack_start(lbl, True, True, 0)
            row.pack_end(status, False, False, 0)
            id_box.pack_start(row, False, False, 0)
            self._id_rows[key] = (dot, status)

        id_frame.add(id_box)
        ctrl_col.pack_start(id_frame, False, False, 0)

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

        # Traffic Mirage
        mirage_frame = Gtk.Frame(label="TRAFFIC MIRAGE")
        mirage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mirage_box.set_margin_top(10)
        mirage_box.set_margin_bottom(10)
        mirage_box.set_margin_start(10)
        mirage_box.set_margin_end(10)

        mirage_desc = Gtk.Label()
        mirage_desc.set_markup(
            "<span size='x-small' color='#94a3b8'>"
            "Traffic obfuscation: timing, decoys, protocol tunneling"
            "</span>"
        )
        mirage_desc.set_xalign(0)
        mirage_box.pack_start(mirage_desc, False, False, 0)

        for label, mode in [
            ("Analyze Fingerprint", "analyze"),
            ("Generate Decoy Traffic", "decoy"),
            ("Traffic Timing Obfuscation", "shape"),
            ("DNS Tunnel", "dns-tunnel"),
            ("Configure obfs4", "obfs4"),
        ]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda b, m=mode: self._on_mirage(m))
            mirage_box.pack_start(btn, False, False, 0)

        mirage_frame.add(mirage_box)
        ctrl_col.pack_start(mirage_frame, False, False, 0)

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
            import subprocess
            import re
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

        # Identity coverage panel
        self._update_coverage(ghost, tor)

        return True  # keep timer alive

    def _update_coverage(self, ghost: bool, tor: bool):
        import shutil
        GREEN, _, RED = "#22c55e", "#f59e0b", "#f43f5e"

        def _set(key, covered: bool, text: str):
            dot, status = self._id_rows[key]
            color = GREEN if covered else RED
            dot.set_markup(f"<span color='{color}'>●</span>")
            status.set_markup(f"<span size='x-small' color='{color}'>{text}</span>")

        # IP: covered by Tor
        _set("ip",      tor,   "via Tor" if tor else "EXPOSED")
        # MAC: check locally-administered bit
        try:
            import subprocess
            import re
            out = subprocess.check_output(["ip", "-o", "link", "show"], text=True, timeout=2)
            mac_rand = False
            for line in out.splitlines():
                m = re.search(r"(\w+): .+link/ether\s+([0-9a-f:]{17})", line)
                if m and m.group(1) not in ("lo",):
                    mac_rand = bool(int(m.group(2).split(":")[0], 16) & 0x02)
                    break
            _set("mac", mac_rand, "randomized" if mac_rand else "real MAC")
        except Exception:
            _set("mac", False, "unknown")
        # Hostname: ghost mode sets it to localhost
        try:
            import socket as _s
            hn = _s.gethostname()
            _set("hostname", hn == "localhost", hn)
        except Exception:
            _set("hostname", False, "unknown")
        # DNS
        try:
            with open("/etc/resolv.conf") as f:
                dns_content = f.read()
            via_tor = "Ghost Mode" in dns_content and "127.0.0.1" in dns_content
            _set("dns", via_tor, "via Tor" if via_tor else "cleartext DNS")
        except Exception:
            _set("dns", False, "unknown")
        # JA3/TLS fingerprint — covered if curl-impersonate is installed
        ci = shutil.which("curl-impersonate") or shutil.which("curl-impersonate-chrome")
        _set("ja3", bool(ci), "curl-impersonate" if ci else "NOT INSTALLED — install curl-impersonate")
        # Browser fingerprint — only Tor Browser fully covers this
        _set("browser", False, "use Tor Browser for full isolation")

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
        import subprocess
        import shutil
        import sys

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
        import subprocess
        import shutil
        import sys
        import os as _os
        script = _os.path.join(_os.path.dirname(__file__), "..", "scripts", "ghost_mode.py")
        term = shutil.which("xterm") or shutil.which("gnome-terminal") or shutil.which("konsole")
        if term:
            subprocess.Popen([term, "-e", f"sudo {sys.executable} {script} workspace"])
        else:
            self._log("[ERROR] No terminal emulator found (xterm/gnome-terminal/konsole)")

    def _on_mirage(self, mode: str):
        self._log(f"Traffic Mirage: {mode}...")
        self.run_script("traffic_mirage.py", [mode])
