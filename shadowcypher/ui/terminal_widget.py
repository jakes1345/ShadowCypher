import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gtk, Vte, GLib, Gdk
import os

class TacticalTerminal(Vte.Terminal):
    """
    ShadowCypher High-Fidelity Tactical Terminal.
    A real Virtual Terminal Emulator (VTE) integrated directly into the HUD.
    Features Obsidian themes and zero-latency interaction.
    """

    def __init__(self):
        super().__init__()
        self._prime_terminal()

    def _prime_terminal(self):
        # Premium Obsidian Aesthetic
        bg_color = Gdk.RGBA()
        bg_color.parse("#020617")
        fg_color = Gdk.RGBA()
        fg_color.parse("#4ade80") # Matrix Green
        palette = [Gdk.RGBA() for _ in range(16)]
        
        # Build a custom cyber-palette
        for i, color in enumerate([
            "#0a0f14", "#ef4444", "#22c55e", "#f59e0b",
            "#3b82f6", "#a855f7", "#06b6d4", "#f8fafc",
            "#475569", "#f87171", "#4ade80", "#fbbf24",
            "#60a5fa", "#c084fc", "#22d3ee", "#ffffff"
        ]):
            palette[i].parse(color)

        self.set_colors(fg_color, bg_color, palette)
        self.set_scrollback_lines(10000)
        self.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        self.set_cursor_shape(Vte.CursorShape.BLOCK)
        self.set_font_scale(1.1)
        
        # Transparent background support (if compositor active)
        self.set_opacity(0.95)

    def spawn_shell(self, cmd=None, cwd=None):
        """Spawn a professional interactive shell."""
        if not cmd:
            cmd = [os.environ.get("SHELL", "/bin/bash")]
        
        if not cwd:
            cwd = os.getcwd()

        self.spawn_sync(
            Vte.PtyFlags.DEFAULT,
            cwd,
            cmd,
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None
        )

class TerminalPage(Gtk.Box):
    """The 'Grand Central' CLI page for ShadowCypher."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.get_style_context().add_class("card")
        self.set_margin_all(10)
        
        # Tactical Header
        header = Gtk.Box(spacing=10)
        header.set_margin_bottom(10)
        lbl = Gtk.Label(xalign=0)
        lbl.set_markup("<span color='#38bdf8' font_weight='bold' font_size='large'>\u2328 TACTICAL_CONTROL_UNIT (OVERLORD_CLI)</span>")
        header.pack_start(lbl, True, True, 0)
        
        btn_clear = Gtk.Button(label="\u232b CLEAR")
        btn_clear.connect("clicked", lambda w: self.terminal.reset(True, True))
        header.pack_end(btn_clear, False, False, 0)
        
        self.pack_start(header, False, False, 0)

        # The Real CLI
        self.terminal = TacticalTerminal()
        self.terminal.spawn_shell()
        
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.terminal)
        self.pack_start(scroll, True, True, 0)
        
        self.show_all()
