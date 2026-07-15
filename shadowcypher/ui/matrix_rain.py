"""Matrix digital rain — real animated falling characters using Cairo rendering."""

import math
import random

import gi

gi.require_version("Gtk", "3.0")
import cairo
from gi.repository import GLib, Gtk

# Characters used in the rain (katakana + latin + digits + symbols)
MATRIX_CHARS = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモ"
    "ヤユヨラリルレロワヲン"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "!@#$%^&*(){}[]<>=/\\|~`"
)


class MatrixColumn:
    """A single column of falling characters."""

    __slots__ = ("x", "y", "speed", "chars", "length", "char_indices", "brightness")

    def __init__(self, x: float, height: int, char_size: int):
        self.x = x
        self.length = random.randint(8, 32)
        self.speed = random.uniform(1.5, 6.0)
        self.y = random.uniform(-self.length * char_size, 0)
        self.char_indices = [random.randint(0, len(MATRIX_CHARS) - 1) for _ in range(self.length)]
        self.brightness = [0.0] * self.length

        # Brightness gradient: head is brightest, fades to tail
        for i in range(self.length):
            t = i / max(self.length - 1, 1)
            self.brightness[i] = max(0.05, 1.0 - t * 0.9)

    def tick(self, char_size: int, canvas_height: int):
        self.y += self.speed
        # Randomly mutate characters for the flicker effect
        for i in range(self.length):
            if random.random() < 0.08:
                self.char_indices[i] = random.randint(0, len(MATRIX_CHARS) - 1)

        # Reset when fully off screen
        if self.y - self.length * char_size > canvas_height:
            self.y = random.uniform(-self.length * char_size * 2, -char_size)
            self.speed = random.uniform(1.5, 6.0)
            self.length = random.randint(8, 32)
            self.char_indices = [random.randint(0, len(MATRIX_CHARS) - 1) for _ in range(self.length)]
            self.brightness = [0.0] * self.length
            for i in range(self.length):
                t = i / max(self.length - 1, 1)
                self.brightness[i] = max(0.05, 1.0 - t * 0.9)


class MatrixRain(Gtk.DrawingArea):
    """GTK widget that renders the Matrix digital rain animation with Cairo."""

    def __init__(self, color_mode="green"):
        """color_mode: 'green' (Matrix), 'red' (Bloodshot), 'blue' (Ghost), 'amber' (MrRobot)"""
        super().__init__()
        self.color_mode = color_mode
        self.columns: list[MatrixColumn] = []
        self.char_size = 14
        self._initialized = False
        self._tick_id = None

        self.set_size_request(-1, 200)
        self.connect("draw", self._on_draw)
        self.connect("size-allocate", self._on_size_allocate)
        self.connect("realize", self._on_realize)
        self.connect("unrealize", self._on_unrealize)

    def _on_realize(self, widget):
        self._tick_id = GLib.timeout_add(33, self._tick)  # ~30 FPS

    def _on_unrealize(self, widget):
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = None

    def _on_size_allocate(self, widget, allocation):
        if not self._initialized or len(self.columns) == 0:
            self._init_columns(allocation.width, allocation.height)
            self._initialized = True

    def _init_columns(self, width, height):
        self.columns.clear()
        num_cols = width // self.char_size
        for i in range(num_cols):
            x = i * self.char_size + self.char_size // 2
            col = MatrixColumn(x, height, self.char_size)
            self.columns.append(col)

    def _tick(self):
        alloc = self.get_allocation()
        for col in self.columns:
            col.tick(self.char_size, alloc.height)
        self.queue_draw()
        return True

    def _get_color(self, brightness: float, is_head: bool = False):
        """Get RGBA color based on mode and brightness."""
        if self.color_mode == "green":
            if is_head:
                return (0.8, 1.0, 0.85, 1.0)
            return (0.0, brightness * 0.9, 0.0, brightness * 0.85)
        elif self.color_mode == "red":
            if is_head:
                return (1.0, 0.8, 0.8, 1.0)
            return (brightness * 0.9, 0.0, 0.0, brightness * 0.85)
        elif self.color_mode == "blue":
            if is_head:
                return (0.8, 0.9, 1.0, 1.0)
            return (0.0, brightness * 0.4, brightness * 0.9, brightness * 0.85)
        elif self.color_mode == "amber":
            if is_head:
                return (1.0, 0.95, 0.7, 1.0)
            return (brightness * 0.8, brightness * 0.6, 0.0, brightness * 0.75)
        else:
            if is_head:
                return (0.9, 0.9, 1.0, 1.0)
            return (0.0, brightness * 0.9, 0.0, brightness * 0.85)

    def _on_draw(self, widget, cr):
        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height

        # Black background
        cr.set_source_rgba(0.0, 0.0, 0.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Set font
        cr.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(self.char_size)

        for col in self.columns:
            for i in range(col.length):
                cy = col.y - i * self.char_size
                if cy < -self.char_size or cy > h + self.char_size:
                    continue

                is_head = (i == 0)
                color = self._get_color(col.brightness[i], is_head)
                cr.set_source_rgba(*color)

                char = MATRIX_CHARS[col.char_indices[i]]
                cr.move_to(col.x, cy)
                cr.show_text(char)

                # Glow effect on head character
                if is_head:
                    cr.set_source_rgba(color[0], color[1], color[2], 0.15)
                    cr.arc(col.x + self.char_size // 4, cy - self.char_size // 3,
                           self.char_size * 1.5, 0, 2 * math.pi)
                    cr.fill()

        return False

    def set_color_mode(self, mode: str):
        """Switch color mode: 'green', 'red', 'blue', 'amber'"""
        self.color_mode = mode
