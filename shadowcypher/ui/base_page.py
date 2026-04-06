"""Base page — shared infrastructure for all tool pages."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from shadowcypher.core.runner import runner


class BasePage(Gtk.Box):
    """Base class for tool pages with terminal output and job management.

    Provides:
    - Terminal-style output area with scrolling
    - Async output/complete callbacks (thread-safe via GLib.idle_add)
    - Job tracking and cancellation
    - Button sensitivity management
    """

    def __init__(self, title: str, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10, **kwargs)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self._job_id = None
        self._action_buttons: list[Gtk.Button] = []

        # Title
        title_label = Gtk.Label(label=title)
        title_label.get_style_context().add_class("section-title")
        title_label.set_halign(Gtk.Align.START)
        self.pack_start(title_label, False, False, 0)

    def build_terminal(self) -> Gtk.ScrolledWindow:
        """Create the terminal output area. Call this after adding controls."""
        self.output_buffer = Gtk.TextBuffer()
        output_view = Gtk.TextView(buffer=self.output_buffer)
        output_view.set_editable(False)
        output_view.set_monospace(True)
        output_view.get_style_context().add_class("terminal-view")
        output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(output_view)
        self.pack_start(scroll, True, True, 0)
        return scroll

    def build_stop_button(self) -> Gtk.Button:
        """Create a stop button. Add to a button box yourself, or it adds itself."""
        self.stop_btn = Gtk.Button(label="\u2b1b Stop")
        self.stop_btn.get_style_context().add_class("danger-btn")
        self.stop_btn.connect("clicked", self._on_stop)
        self.stop_btn.set_sensitive(False)
        return self.stop_btn

    def make_action_btn(self, label: str, handler, style: str = "action-btn") -> Gtk.Button:
        """Create a styled action button and track it for sensitivity toggling."""
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class(style)
        btn.connect("clicked", handler)
        self._action_buttons.append(btn)
        return btn

    # ── Output helpers (thread-safe) ──

    def on_output(self, text: str):
        """Thread-safe: append text to terminal."""
        GLib.idle_add(self._append, text)

    def on_complete(self, rc: int):
        """Thread-safe: show completion and re-enable buttons."""
        GLib.idle_add(self._append, f"\n[Completed: {rc}]\n")
        GLib.idle_add(self._set_running, False)
        self._job_id = None

    def _append(self, text: str):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, text)

    def clear_output(self, text: str = ""):
        """Clear terminal and optionally set initial text."""
        self.output_buffer.set_text(text)

    # ── Job management ──

    def set_running(self, running: bool):
        """Toggle button sensitivity based on whether a job is running."""
        self._set_running(running)

    def _set_running(self, running: bool):
        for btn in self._action_buttons:
            btn.set_sensitive(not running)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.set_sensitive(running)

    def _on_stop(self, btn):
        if self._job_id is not None:
            runner.cancel(self._job_id)
            self.on_output("\n[Cancelled by user]\n")
            self._set_running(False)
            self._job_id = None

    def run_job(self, job_id: int):
        """Track a running job and enable the stop button."""
        self._job_id = job_id
        self._set_running(True)
