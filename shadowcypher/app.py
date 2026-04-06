"""ShadowCypher Security Suite — Elite Mission Command Center Build V19."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk
import sys
import os
import threading

# Tactical Internal Imports
from shadowcypher.ui.themes import get_theme, get_theme_animation
from shadowcypher.ui.dashboard import DashboardPage
from shadowcypher.core.logger import logger
from shadowcypher.core.session import session

class ShadowCypherWindow(Gtk.ApplicationWindow):
    """Deep-Obsidian Mission Control Window."""
    def __init__(self, app):
        super().__init__(application=app, title="ShadowCypher | MISSION_ACTIVE")
        self.set_default_size(1400, 900)
        
        # 1. THEME INJECTION
        theme = get_theme("dark")
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(theme["css"].encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # 2. SHELL LAYOUT
        self._main_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self._main_grid)
        
        # Sidebar & Registry
        self._sidebar = self._build_sidebar()
        self._main_grid.pack_start(self._sidebar, False, False, 0)
        
        self._page_container = Gtk.Stack()
        self._main_grid.pack_start(self._page_container, True, True, 0)
        self._page_registry = {}

        # INITIAL DASHBOARD ACTIVATION
        self._switch_to_page("Operational Overview")
        self.show_all()

    def _build_sidebar(self):
        sidebar = Gtk.ListBox()
        sidebar.get_style_context().add_class("sidebar")
        
        pages = [
            ("\U0001f4ca Operational Overview"),
            ("\U0001f4c2 Mission Records"),
            ("\U0001f4e1 Signal Recon"),
            ("\U0001f916 Tactical Swarm AI")
        ]
        
        for name in pages:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=name, xalign=0)
            row.add(lbl)
            sidebar.add(row)
            
        sidebar.connect("row-activated", self._on_sidebar_selected)
        return sidebar

    def _on_sidebar_selected(self, listbox, row):
        name_with_icon = row.get_child().get_text()
        name = name_with_icon.split(" ", 1)[1] if " " in name_with_icon else name_with_icon
        self._switch_to_page(name)

    def _switch_to_page(self, name):
        """Elite JIT Lazy-Loading Engine."""
        if name not in self._page_registry:
            if name == "Operational Overview":
                from shadowcypher.ui.dashboard import DashboardPage
                self._page_registry[name] = DashboardPage()
            elif name == "Signal Recon":
                from shadowcypher.ui.recon_page import ReconPage
                self._page_registry[name] = ReconPage()
            elif name == "Tactical Swarm AI":
                from shadowcypher.ui.ai_page import AIPage
                self._page_registry[name] = AIPage()
            elif name == "Mission Records":
                from shadowcypher.ui.projects_page import ProjectsPage
                self._page_registry[name] = ProjectsPage()
            else:
                lbl = Gtk.Label(label=f"[SYSTEM] ACCESSING_{name.upper()}...")
                lbl.get_style_context().add_class("card")
                self._page_registry[name] = lbl
                
            self._page_container.add_named(self._page_registry[name], name)
        
        self._page_container.set_visible_child_name(name)

class ShadowCypherApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.shadow.cypher")
        
    def do_activate(self):
        try:
            self._window = ShadowCypherWindow(self)
        except Exception as e:
            logger.error("shell", f"FAILED_WINDOW_INITIALIZATION: {str(e)}")
            print(f"[ShadowCypher] FATAL: {str(e)}")

if __name__ == "__main__":
    app = ShadowCypherApp()
    app.run(sys.argv)
