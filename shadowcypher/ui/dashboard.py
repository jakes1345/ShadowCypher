import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Gdk, Pango, PangoCairo
import cairo
import math
import psutil
import time
import random


class TacticalHUD(Gtk.DrawingArea):
    """Premium Cairo-rendered Mission Command Dashboard with Cyber-OSINT Map."""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 580)
        self.angle = 0.0
        self._prev_net = psutil.net_io_counters().bytes_sent

        self.pings = []
        for _ in range(12):  # Increased density
            self.pings.append(
                {
                    "x": random.uniform(0.1, 0.9),
                    "y": random.uniform(0.2, 0.8),
                    "life": random.random(),
                }
            )

        self.metrics = {
            "cpu": "0%",
            "ram": "0%",
            "net": "0 KB/s TX",
            "disk": "0%",
            "uptime": "0h 0m",
            "procs": "0",
            "ai_load": "IDLE",
            "enc_state": "NONE",
            "sb_state": "OFF",
        }

        self._update_metrics()
        self.connect("draw", self._on_draw)
        GLib.timeout_add(33, self._tick_vis)
        GLib.timeout_add(2000, self._tick_tel)

    def _update_metrics(self):
        try:
            self.metrics["cpu"] = f"{psutil.cpu_percent(interval=0):.0f}%"
            self.metrics["ram"] = f"{psutil.virtual_memory().percent:.0f}%"
            curr_net = psutil.net_io_counters().bytes_sent
            if hasattr(self, "_prev_net"):
                delta = (curr_net - self._prev_net) // 1024
                # Filter spikes
                self.metrics["net"] = f"{delta if delta < 2000000 else 0} KB/s TX"
            self._prev_net = curr_net
            self.metrics["disk"] = f"{psutil.disk_usage('/').percent:.0f}%"
            boot = time.time() - psutil.boot_time()
            self.metrics["uptime"] = f"{int(boot // 3600)}h {int((boot % 3600) // 60)}m"
            self.metrics["procs"] = str(len(psutil.pids()))
            self.metrics["ai_load"] = (
                "ACTIVE" if float(self.metrics["cpu"][:-1]) > 5 else "IDLE"
            )

            # Real-time Integrity Audit
            import subprocess

            try:
                sb = subprocess.check_output(
                    ["mokutil", "--sb-state"], stderr=subprocess.STDOUT
                ).decode()
                self.metrics["sb_state"] = "ON" if "enabled" in sb.lower() else "OFF"
            except (FileNotFoundError, subprocess.CalledProcessError, OSError):
                self.metrics["sb_state"] = "UNKN"

            try:
                luks = subprocess.check_output(
                    ["lsblk", "-f"], stderr=subprocess.STDOUT
                ).decode()
                self.metrics["enc_state"] = "LUKS" if "crypto_LUKS" in luks else "NONE"
            except (FileNotFoundError, subprocess.CalledProcessError, OSError):
                self.metrics["enc_state"] = "NONE"

        except (AttributeError, OSError, ValueError):
            pass

    def _tick_tel(self):
        self._update_metrics()
        return True

    def _tick_vis(self):
        self.angle += 0.03
        for p in self.pings:
            p["life"] -= 0.008
            if p["life"] <= 0:
                p["x"], p["y"] = random.uniform(0.1, 0.9), random.uniform(0.2, 0.8)
                p["life"] = 1.0
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        cx, cy = width / 2, height / 2

        # 1. Background (Obsidian Depth)
        cr.set_source_rgba(0.015, 0.02, 0.03, 1.0)
        cr.paint()

        # 2. Cyber-Grid (Subtle)
        cr.set_source_rgba(0, 0.6, 1.0, 0.03)
        cr.set_line_width(0.4)
        for i in range(0, width, 50):
            cr.move_to(i, 0)
            cr.line_to(i, height)
            cr.stroke()
        for i in range(0, height, 50):
            cr.move_to(0, i)
            cr.line_to(width, i)
            cr.stroke()

        # 3. OSINT Pings (Geospatial markers)
        for p in self.pings:
            alpha = p["life"] * 0.45
            px, py = p["x"] * width, p["y"] * height
            cr.set_source_rgba(0, 0.9, 1.0, alpha)
            cr.arc(px, py, (1.0 - p["life"]) * 40, 0, 2 * math.pi)
            cr.stroke()
            cr.arc(px, py, 2, 0, 2 * math.pi)
            cr.fill()

        # 4. Mission Radar
        radius = min(width, height) * 0.38
        cr.set_line_width(0.8)
        for i, r_frac in enumerate([0.2, 0.4, 0.6, 0.8, 1.0]):
            cr.set_source_rgba(0, 0.8, 1.0, 0.05 + (i * 0.02))
            cr.arc(cx, cy, radius * r_frac, 0, 2 * math.pi)
            cr.stroke()

        # Dynamic Sweep
        for i in range(30):
            ta = self.angle - (i * 0.045)
            tx, ty = cx + radius * math.cos(ta), cy + radius * math.sin(ta)
            cr.set_source_rgba(0, 0.95, 1.0, 0.18 * (1.0 - i / 30.0))
            cr.set_line_width(2.5)
            cr.move_to(cx, cy)
            cr.line_to(tx, ty)
            cr.stroke()

        # Core Pulsar
        pulse = 7 + 5 * math.sin(time.monotonic() * 2.5)
        cr.set_source_rgba(0, 1.0, 1.0, 0.9)
        cr.arc(cx, cy, pulse, 0, 2 * math.pi)
        cr.fill()

        # 5. Data Pods (Final Density Calibration)
        pods = [
            (50, 50, "PROCESSOR", self.metrics["cpu"], "Engine Load"),
            (50, 210, "MEMORY", self.metrics["ram"], "Neural Sync"),
            (50, 370, "NETWORK", self.metrics["net"], "Data Stream"),
            (50, 530, "AI_ENGINE", self.metrics["ai_load"], "Thinking..."),
            (width - 370, 50, "STORAGE", self.metrics["disk"], "Loot Cache"),
            (width - 370, 210, "UPTIME", self.metrics["uptime"], "Uptime Focus"),
            (width - 370, 370, "PROCESSES", self.metrics["procs"], "Active Swarm"),
            (
                width - 370,
                530,
                "SECURITY",
                f"SB:{self.metrics['sb_state']}",
                f"ENC:{self.metrics['enc_state']}",
            ),
        ]
        for x, y, title, val, subtitle in pods:
            self._draw_pod(cr, x, y, 320, 130, title, val, subtitle, cx, cy)

    def _draw_pod(self, cr, x, y, pw, ph, title, val, subtitle, cx, cy):
        # Neural Connection Line
        cr.set_source_rgba(0, 1.0, 1.0, 0.03)
        cr.set_line_width(0.7)
        cr.move_to(cx, cy)
        cr.line_to(x + pw / 2, y + ph / 2)
        cr.stroke()
        # High-Fidelity Pod Body
        r = 12
        cr.set_source_rgba(0.04, 0.08, 0.12, 0.92)
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x + pw - r, y + r, r, 1.5 * math.pi, 2 * math.pi)
        cr.arc(x + pw - r, y + ph - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + ph - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgba(0, 0.9, 1.0, 0.18)
        cr.stroke()
        # Data
        cr.set_source_rgba(0, 0.85, 1.0, 0.85)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(10)
        cr.move_to(x + 18, y + 25)
        cr.show_text(title)
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.set_font_size(30)
        cr.move_to(x + 18, y + 75)
        cr.show_text(str(val))
        cr.set_source_rgba(0.5, 0.65, 0.75, 0.65)
        cr.set_font_size(9)
        cr.move_to(x + 18, y + ph - 15)
        cr.show_text(subtitle)


class DashboardPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.hud = TacticalHUD()
        self.pack_start(self.hud, True, True, 0)

        # Log Box (Hardened Workspace)
        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        log_box.set_margin_start(40)
        log_box.set_margin_end(40)
        log_box.set_margin_bottom(20)

        lbl = Gtk.Label(xalign=0)
        lbl.set_markup(
            "<span color='#38bdf8' font_weight='bold' letter_spacing='2000'>\U0001f575\ufe0f MISSION_TELEMETRY_LOG</span>"
        )
        log_box.pack_start(lbl, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(140)
        scroller.get_style_context().add_class("glass-pod")
        scroller.get_style_context().add_class("mission-log")
        self.log_list = Gtk.ListBox()
        self.log_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.add(self.log_list)
        log_box.pack_start(scroller, True, True, 0)

        self.pack_start(log_box, False, False, 0)
        GLib.timeout_add(3000, self._process_mission_logs)
        self.show_all()

    def _process_mission_logs(self):
        """High-Fidelity Log Telemetry — Real-time tailing of mission activity."""
        log_path = "/home/jack/ShadowCypher/logs/ai_debug.log"
        if not os.path.exists(log_path):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w") as f: f.write("[SYSTEM] Operational Log Initialized.\n")
        
        # Track file position across calls
        if not hasattr(self, "_log_offset"):
            self._log_offset = os.path.getsize(log_path)
            return True

        try:
            current_size = os.path.getsize(log_path)
            if current_size < self._log_offset: # Log rotated
                self._log_offset = 0

            if current_size > self._log_offset:
                with open(log_path, "r") as f:
                    f.seek(self._log_offset)
                    new_lines = f.readlines()
                    self._log_offset = f.tell()
                    
                    for line in new_lines:
                        clean_line = line.strip()
                        if not clean_line or "---" in clean_line: continue
                        
                        row = Gtk.ListBoxRow()
                        lbl = Gtk.Label(xalign=0)
                        # Trim for UI stability but keep enough context
                        display_text = clean_line[-120:] if len(clean_line) > 120 else clean_line
                        lbl.set_markup(f"<span font_family='monospace' size='small' color='#94a3b8'>> {display_text}</span>")
                        lbl.set_margin_start(15)
                        lbl.set_margin_top(2)
                        lbl.set_margin_bottom(2)
                        row.add(lbl)
                        self.log_list.prepend(row)
                        
                        # Keep maximum 25 rows
                        children = self.log_list.get_children()
                        if len(children) > 25:
                            self.log_list.remove(children[-1])
            
            self.show_all()
        except Exception as e:
            logger.error("ui", f"Telemetry failure: {e}")

        return True
