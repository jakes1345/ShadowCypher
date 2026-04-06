"""Animated visualizations — radar sweep, glitch effect, CRT scanlines, pulse grid."""

import random
import math
import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
import cairo


class RadarSweep(Gtk.DrawingArea):
    """Rotating radar sweep animation — for the Ghost in the Shell / blue themes."""

    def __init__(self):
        super().__init__()
        self.angle = 0.0
        self.blips: list[tuple[float, float, float]] = []  # (angle, dist, age)
        self.set_size_request(-1, 200)
        self.connect("draw", self._on_draw)
        self.connect("realize", self._start)
        self.connect("unrealize", self._stop)
        self._tick_id = None

    def _start(self, w):
        self._tick_id = GLib.timeout_add(33, self._tick)

    def _stop(self, w):
        if self._tick_id:
            GLib.source_remove(self._tick_id)

    def _tick(self):
        self.angle += 0.03
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi
        # Random blips
        if random.random() < 0.05:
            self.blips.append((random.uniform(0, 2 * math.pi), random.uniform(0.2, 0.9), 0.0))
        # Age blips
        self.blips = [(a, d, age + 0.02) for a, d, age in self.blips if age < 1.0]
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 10

        # Background
        cr.set_source_rgba(0.02, 0.04, 0.08, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Grid circles
        for i in range(1, 5):
            r = radius * i / 4
            cr.set_source_rgba(0.0, 0.4, 0.7, 0.15)
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()

        # Grid crosshairs
        cr.set_source_rgba(0.0, 0.4, 0.7, 0.1)
        cr.move_to(cx - radius, cy)
        cr.line_to(cx + radius, cy)
        cr.stroke()
        cr.move_to(cx, cy - radius)
        cr.line_to(cx, cy + radius)
        cr.stroke()

        # Sweep trail (fading arc)
        for i in range(40):
            a = self.angle - i * 0.04
            alpha = (1.0 - i / 40.0) * 0.3
            cr.set_source_rgba(0.0, 0.8, 1.0, alpha)
            x1 = cx + math.cos(a) * radius
            y1 = cy + math.sin(a) * radius
            cr.move_to(cx, cy)
            cr.line_to(x1, y1)
            cr.stroke()

        # Sweep line
        cr.set_source_rgba(0.0, 1.0, 1.0, 0.8)
        cr.set_line_width(2)
        sx = cx + math.cos(self.angle) * radius
        sy = cy + math.sin(self.angle) * radius
        cr.move_to(cx, cy)
        cr.line_to(sx, sy)
        cr.stroke()

        # Blips
        for ba, bd, age in self.blips:
            bx = cx + math.cos(ba) * bd * radius
            by = cy + math.sin(ba) * bd * radius
            alpha = 1.0 - age
            cr.set_source_rgba(0.0, 1.0, 0.6, alpha * 0.8)
            cr.arc(bx, by, 3 + age * 4, 0, 2 * math.pi)
            cr.fill()
            # Glow
            cr.set_source_rgba(0.0, 1.0, 0.6, alpha * 0.15)
            cr.arc(bx, by, 8 + age * 8, 0, 2 * math.pi)
            cr.fill()

        # Center dot
        cr.set_source_rgba(0.0, 0.9, 1.0, 0.9)
        cr.arc(cx, cy, 3, 0, 2 * math.pi)
        cr.fill()

        return False


class GlitchBanner(Gtk.DrawingArea):
    """Glitch/distortion text effect — for the Mr. Robot theme."""

    def __init__(self, text="SHADOWCYPHER"):
        super().__init__()
        self.text = text
        self.glitch_offset = 0
        self.glitch_active = False
        self.glitch_timer = 0
        self.scan_y = 0
        self.set_size_request(-1, 120)
        self.connect("draw", self._on_draw)
        self.connect("realize", self._start)
        self.connect("unrealize", self._stop)
        self._tick_id = None

    def _start(self, w):
        self._tick_id = GLib.timeout_add(40, self._tick)

    def _stop(self, w):
        if self._tick_id:
            GLib.source_remove(self._tick_id)

    def _tick(self):
        self.glitch_timer += 1
        # Trigger glitch bursts randomly
        if not self.glitch_active and random.random() < 0.03:
            self.glitch_active = True
            self.glitch_timer = 0
        if self.glitch_active and self.glitch_timer > 6:
            self.glitch_active = False

        self.scan_y += 2
        alloc = self.get_allocation()
        if self.scan_y > alloc.height:
            self.scan_y = 0

        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Background
        cr.set_source_rgba(0.04, 0.04, 0.05, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(48)
        extents = cr.text_extents(self.text)
        tx = (w - extents.width) / 2
        ty = h / 2 + extents.height / 2

        if self.glitch_active:
            # RGB split effect
            offx = random.randint(-6, 6)
            offy = random.randint(-3, 3)

            # Red channel (offset left)
            cr.set_source_rgba(1.0, 0.0, 0.0, 0.6)
            cr.move_to(tx + offx - 3, ty + offy)
            cr.show_text(self.text)

            # Blue channel (offset right)
            cr.set_source_rgba(0.0, 0.3, 1.0, 0.6)
            cr.move_to(tx + offx + 3, ty - offy)
            cr.show_text(self.text)

            # Glitch bars
            for _ in range(random.randint(1, 4)):
                by = random.randint(0, h)
                bh = random.randint(2, 8)
                bx = random.randint(-20, 20)
                cr.set_source_rgba(0.8, 0.8, 0.8, 0.15)
                cr.rectangle(0, by, w, bh)
                cr.fill()
                # Shifted copy of text in the bar
                cr.save()
                cr.rectangle(0, by, w, bh)
                cr.clip()
                cr.set_source_rgba(0.9, 0.9, 0.9, 0.8)
                cr.move_to(tx + bx, ty)
                cr.show_text(self.text)
                cr.restore()
        else:
            # Normal text with slight flicker
            alpha = 0.85 + random.uniform(-0.05, 0.05)
            cr.set_source_rgba(0.75, 0.75, 0.78, alpha)
            cr.move_to(tx, ty)
            cr.show_text(self.text)

        # CRT scanline overlay
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.03)
        for y in range(0, h, 3):
            cr.rectangle(0, y, w, 1)
            cr.fill()

        # Moving scan line
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.06)
        cr.rectangle(0, self.scan_y, w, 2)
        cr.fill()

        return False


class PulseGrid(Gtk.DrawingArea):
    """Pulsing dot grid animation — for Phantom theme."""

    def __init__(self):
        super().__init__()
        self.t = 0.0
        self.set_size_request(-1, 200)
        self.connect("draw", self._on_draw)
        self.connect("realize", self._start)
        self.connect("unrealize", self._stop)
        self._tick_id = None

    def _start(self, w):
        self._tick_id = GLib.timeout_add(40, self._tick)

    def _stop(self, w):
        if self._tick_id:
            GLib.source_remove(self._tick_id)

    def _tick(self):
        self.t += 0.06
        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Background
        cr.set_source_rgba(0.03, 0.01, 0.06, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        spacing = 24
        cols = w // spacing + 1
        rows = h // spacing + 1

        for row in range(rows):
            for col in range(cols):
                x = col * spacing + spacing // 2
                y = row * spacing + spacing // 2

                # Wave pattern from center
                dx = x - w / 2
                dy = y - h / 2
                dist = math.sqrt(dx * dx + dy * dy)

                pulse = math.sin(dist * 0.02 - self.t) * 0.5 + 0.5
                size = 1.0 + pulse * 3.0

                r = 0.45 + pulse * 0.3
                g = 0.1 + pulse * 0.1
                b = 0.7 + pulse * 0.3
                alpha = 0.2 + pulse * 0.6

                cr.set_source_rgba(r, g, b, alpha)
                cr.arc(x, y, size, 0, 2 * math.pi)
                cr.fill()

                # Connect nearby pulsing dots with lines
                if pulse > 0.7 and col > 0:
                    cr.set_source_rgba(r, g, b, alpha * 0.15)
                    cr.move_to(x, y)
                    cr.line_to(x - spacing, y)
                    cr.stroke()

        return False


class FireWall(Gtk.DrawingArea):
    """Animated firewall / burning wall effect — for Bloodshot theme."""

    def __init__(self):
        super().__init__()
        self.t = 0.0
        self.particles: list[list[float]] = []
        self.set_size_request(-1, 200)
        self.connect("draw", self._on_draw)
        self.connect("realize", self._start)
        self.connect("unrealize", self._stop)
        self._tick_id = None

    def _start(self, w):
        self._tick_id = GLib.timeout_add(33, self._tick)

    def _stop(self, w):
        if self._tick_id:
            GLib.source_remove(self._tick_id)

    def _tick(self):
        self.t += 0.05
        alloc = self.get_allocation()
        w = alloc.width

        # Spawn new particles along bottom
        for _ in range(3):
            self.particles.append([
                random.uniform(0, w),  # x
                float(alloc.height),   # y (start at bottom)
                random.uniform(-0.5, 0.5),  # vx
                random.uniform(-2.0, -5.0),  # vy (upward)
                random.uniform(3, 8),  # size
                1.0,  # life
            ])

        # Update particles
        alive = []
        for p in self.particles:
            p[0] += p[2]  # x += vx
            p[1] += p[3]  # y += vy
            p[5] -= 0.015  # decay
            p[4] *= 0.99  # shrink
            if p[5] > 0:
                alive.append(p)
        self.particles = alive[-300:]  # cap

        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Dark background
        cr.set_source_rgba(0.06, 0.02, 0.02, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        for p in self.particles:
            x, y, _, _, size, life = p
            # Color gradient: white -> yellow -> orange -> red -> dark
            if life > 0.8:
                r, g, b = 1.0, 0.95, 0.8
            elif life > 0.6:
                r, g, b = 1.0, 0.7, 0.2
            elif life > 0.3:
                r, g, b = 0.9, 0.3, 0.05
            else:
                r, g, b = 0.5, 0.1, 0.02

            cr.set_source_rgba(r, g, b, life * 0.8)
            cr.arc(x, y, size, 0, 2 * math.pi)
            cr.fill()

            # Glow
            cr.set_source_rgba(r, g, b, life * 0.1)
            cr.arc(x, y, size * 2.5, 0, 2 * math.pi)
            cr.fill()

        # Heat haze at bottom
        for x in range(0, w, 4):
            haze_h = 20 + math.sin(x * 0.05 + self.t * 3) * 10
            alpha = 0.08 + math.sin(x * 0.1 + self.t) * 0.03
            cr.set_source_rgba(1.0, 0.3, 0.0, alpha)
            cr.rectangle(x, h - haze_h, 3, haze_h)
            cr.fill()

        return False


class TerminalBoot(Gtk.DrawingArea):
    """Retro terminal boot sequence animation — for Terminal theme."""

    def __init__(self):
        super().__init__()
        self.lines: list[str] = []
        self.boot_lines = [
            "BIOS POST... OK",
            "Memory test: 47104 MB ... PASS",
            "GPU: NVIDIA RTX 2060 SUPER [8192 MB] ... DETECTED",
            "CPU: AMD Ryzen 5 3600 6-Core ... ONLINE",
            "Loading kernel... done",
            "Mounting filesystems... done",
            "Starting network services... done",
            "Initializing security modules...",
            "  [+] nmap 7.94 ............ LOADED",
            "  [+] hydra 9.5 ............ LOADED",
            "  [+] john 1.9.0 ........... LOADED",
            "  [+] hashcat 6.2.6 ........ LOADED",
            "  [+] aircrack-ng 1.7 ...... LOADED",
            "  [+] tcpdump 4.99.4 ....... LOADED",
            "",
            "╔══════════════════════════════════════╗",
            "║     SHADOWCYPHER v2.0 OPERATIONAL    ║",
            "║       All systems nominal.           ║",
            "╚══════════════════════════════════════╝",
            "",
            "root@shadow:~# _",
        ]
        self.line_index = 0
        self.char_index = 0
        self.cursor_visible = True
        self.set_size_request(-1, 200)
        self.connect("draw", self._on_draw)
        self.connect("realize", self._start)
        self.connect("unrealize", self._stop)
        self._tick_id = None
        self._cursor_id = None

    def _start(self, w):
        self._tick_id = GLib.timeout_add(25, self._tick)
        self._cursor_id = GLib.timeout_add(500, self._blink_cursor)

    def _stop(self, w):
        if self._tick_id:
            GLib.source_remove(self._tick_id)
        if self._cursor_id:
            GLib.source_remove(self._cursor_id)

    def _blink_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self.queue_draw()
        return True

    def _tick(self):
        if self.line_index < len(self.boot_lines):
            current = self.boot_lines[self.line_index]
            if self.char_index <= len(current):
                # Build partial line
                if self.char_index == len(current):
                    self.lines.append(current)
                    self.line_index += 1
                    self.char_index = 0
                else:
                    self.char_index += max(1, random.randint(1, 3))
                    if self.char_index > len(current):
                        self.char_index = len(current)
        else:
            # Loop back after a pause
            self.line_index = 0
            self.lines.clear()

        self.queue_draw()
        return True

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Black CRT background
        cr.set_source_rgba(0.01, 0.01, 0.01, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13)

        y = 16
        for line in self.lines[-15:]:  # Show last 15 lines
            if "[+]" in line:
                cr.set_source_rgba(0.0, 1.0, 0.0, 0.9)
            elif "PASS" in line or "OK" in line or "LOADED" in line or "done" in line:
                cr.set_source_rgba(0.0, 0.9, 0.3, 0.85)
            elif "SHADOWCYPHER" in line or "══" in line or "║" in line:
                cr.set_source_rgba(0.0, 1.0, 0.5, 1.0)
            else:
                cr.set_source_rgba(0.0, 0.8, 0.0, 0.75)
            cr.move_to(10, y)
            cr.show_text(line)
            y += 16

        # Partial current line
        if self.line_index < len(self.boot_lines):
            partial = self.boot_lines[self.line_index][:self.char_index]
            cr.set_source_rgba(0.0, 1.0, 0.0, 0.9)
            cr.move_to(10, y)
            cr.show_text(partial)
            # Cursor
            if self.cursor_visible:
                ext = cr.text_extents(partial)
                cr.rectangle(10 + ext.x_advance, y - 12, 8, 14)
                cr.fill()

        # Scanlines
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.04)
        for sy in range(0, h, 2):
            cr.rectangle(0, sy, w, 1)
            cr.fill()

        return False
