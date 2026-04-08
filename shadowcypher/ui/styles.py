"""GTK CSS theming — dark cybersecurity aesthetic."""

SHADOWCYPHER_CSS = """
/* ── Tactical Obsidian Reset ── */
* {
    color: #cbd5e1;
}

window {
    background-color: #06080a;
}

headerbar {
    background: #06080a;
    border-bottom: 2px solid #1e293b;
    min-height: 52px;
}

headerbar label { color: #f8fafc; font-weight: bold; font-size: 13px; }
headerbar subtitle { color: #64748b; font-size: 10px; }

headerbar button {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #38bdf8;
    padding: 4px 10px;
}

headerbar button:hover {
    background: #1e293b;
}

/* ── Sidebar Mission Grid ── */
.sidebar {
    background-color: #06080a;
    border-right: 1px solid #1e293b;
}

.sidebar row {
    padding: 12px 25px;
    color: #94a3b8;
}

.sidebar row:selected {
    background: #0f172a;
    color: #38bdf8;
    font-weight: bold;
}

/* ── Absolute Blackout Containers ── */
list, listbox, row, viewport, scrolledwindow, stack {
    background-color: #06080a;
    color: #cbd5e1;
}

.mission-log, .mission-log *, .mission-log list, .mission-log listbox, .mission-log row {
    background-color: #06080a;
    color: #e2e8f0;
}

/* ── Tactical Cards ── */
.card, .glass-pod {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
}

.card-title { font-size: 11px; font-weight: bold; color: #38bdf8; }
.card-value { font-size: 28px; font-weight: bold; color: #f1f5f9; }

actionbar {
    background: #06080a;
    border-top: 1px solid #1e293b;
    padding: 10px;
}

.terminal-view {
    background-color: #010204;
    color: #4ade80;
    font-family: monospace;
    border: 1px solid #1e293b;
}

.text-muted { color: #64748b; font-size: 11px; }
.cyan-text { color: #38bdf8; }
.purple-text { color: #a855f7; }
.green-text { color: #4ade80; }

.sidebar-header {
    font-size: 10px;
    font-weight: bold;
    color: #38bdf8;
    padding: 25px 20px 8px 20px;
}
"""

def get_css() -> str:
    return SHADOWCYPHER_CSS
