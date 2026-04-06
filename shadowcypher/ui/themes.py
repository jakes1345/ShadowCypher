"""Professional Theme Engine — Absolute Obsidian Fidelity (Build V24)."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# ─────────────────────────────────────────────────────────────────────
# 1) THEME REPOSITORY (Absolute Obsidian Fidelity)
# ─────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "name": "Obsidian Stealth",
        "description": "Absolute 60FPS Obsidian Glassmorphic HUD",
        "animation": "pulse_cyan",
        "css": """
            /* Universal Blackout Purge */
            window, stack, notebook, .main-window, grid, box {
                background-color: #010204;
                color: #ffffff;
            }
            
            /* Obsidian Glass-Pod Design */
            .card, .glass-panel, scrolledwindow, viewport {
                background: rgba(10, 15, 20, 0.98);
                border: 1.5px solid rgba(0, 242, 255, 0.4);
                border-radius: 20px;
                padding: 24px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            }

            /* Stealth Sidebar */
            .sidebar {
                background: #010204;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }
            
            row {
                padding: 18px 30px;
                margin: 8px 15px;
                border-radius: 15px;
                color: #94a3b8;
                transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
            }
            
            row:selected {
                background: rgba(0, 242, 255, 0.15);
                color: #00f2ff;
                border: 1px solid rgba(0, 242, 255, 0.4);
            }

            /* Tactical Inputs & Buttons */
            entry {
                background: rgba(5, 7, 10, 0.98);
                border: 1.5px solid rgba(0, 242, 255, 0.3);
                border-radius: 12px;
                color: #fff;
                padding: 15px;
            }

            button {
                background: #05070a;
                border: 1.5px solid rgba(0, 242, 255, 0.3);
                border-radius: 12px;
                padding: 12px 24px;
                color: #00f2ff;
                font-weight: 800;
                text-shadow: 0 0 10px rgba(0, 242, 255, 0.4);
            }

            button:hover {
                background: #00f2ff;
                color: #000;
                box-shadow: 0 0 25px rgba(0, 242, 255, 0.6);
            }

            /* Absolute Deep-Well Terminal */
            textview, .terminal-view, textview text {
                background-color: #010204;
                border: 1px solid rgba(0, 242, 255, 0.2);
                border-radius: 18px;
                color: #00ff41;
                font-family: 'JetBrains Mono', 'CaskaydiaCove NF', 'Monospace', monospace;
                padding: 20px;
            }
        """
    }
}

# ─────────────────────────────────────────────────────────────────────
# 2) PUBLIC API
# ─────────────────────────────────────────────────────────────────────

def get_theme_names(): return list(THEMES.keys())
def get_theme(name): return THEMES.get(name, THEMES["dark"])
def get_theme_css(name): return get_theme(name)["css"]
def get_theme_animation(name): return get_theme(name)["animation"]
