"""GTK CSS theming — dark cybersecurity aesthetic."""

import os

def get_css() -> str:
    css_path = os.path.join(os.path.dirname(__file__), "index.css")
    if os.path.exists(css_path):
        try:
            with open(css_path, "r") as f:
                return f.read()
        except Exception:
            pass
    
    # High-Fidelity Fallback (Absolute Obsidian)
    return """
    * { color: #f8fafc; }
    window, grid, box, stack, scrolledwindow, viewport, list, listbox, row {
        background-color: #010204;
    }
    .card, .glass-panel {
        background: rgba(8, 12, 18, 0.98);
        border: 1.5px solid rgba(0, 242, 255, 0.45);
        border-radius: 24px;
    }
    entry {
        background: rgba(15, 23, 42, 0.6);
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    button {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        color: #00f2ff;
        border: 1px solid rgba(0, 242, 255, 0.45);
    }
    .terminal-view {
        background: #020617;
        color: #00ff41;
    }
    """
