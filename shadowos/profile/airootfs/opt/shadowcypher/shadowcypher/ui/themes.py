"""Professional Theme Engine — Absolute Obsidian Fidelity (Build V30)."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from shadowcypher.ui.styles import get_css

# ─────────────────────────────────────────────────────────────────────
# 1) THEME REPOSITORY (Absolute Obsidian Fidelity)
# ─────────────────────────────────────────────────────────────────────

# We now pull the dynamic CSS from the styles.py engine to allow for 
# real-time tactical updates and mission-lockdown.
DYNAMIC_CSS = get_css()

THEMES = {
    "dark": {
        "name": "Obsidian Stealth",
        "description": "Absolute 60FPS Obsidian Glassmorphic HUD",
        "animation": "pulse_cyan",
        "css": DYNAMIC_CSS
    }
}

# ─────────────────────────────────────────────────────────────────────
# 2) PUBLIC API
# ─────────────────────────────────────────────────────────────────────

def get_theme_names(): return list(THEMES.keys())
def get_theme(name): 
    # Refresh CSS on every call during dispatch to ensure fixes are applied
    THEMES["dark"]["css"] = get_css()
    return THEMES.get(name, THEMES["dark"])

def get_theme_css(name): return get_theme(name)["css"]
def get_theme_animation(name): return get_theme(name)["animation"]
