"""GTK CSS theming — dark cybersecurity aesthetic."""


SHADOWCYPHER_CSS = """
/* ── Base ── */
window {
    background-color: #06080a;
    color: #cbd5e1;
    font-family: "Outfit", "Inter", sans-serif;
}

headerbar {
    background: rgba(15, 23, 42, 0.8);
    border-bottom: 1px solid rgba(56, 189, 248, 0.15);
    color: #f8fafc;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

headerbar title {
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #38bdf8;
}

/* ── Sidebar ── */
.sidebar {
    background-color: rgba(10, 15, 25, 0.9);
    border-right: 1px solid rgba(56, 189, 248, 0.1);
    padding: 12px 8px;
}

.sidebar row {
    border-radius: 10px;
    margin: 4px 8px;
    padding: 12px 16px;
    color: #94a3b8;
    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar row:hover {
    background-color: rgba(56, 189, 248, 0.08);
    color: #38bdf8;
}

.sidebar row:selected {
    background: linear-gradient(90deg, rgba(56, 189, 248, 0.2), rgba(168, 85, 247, 0.1));
    color: #38bdf8;
    font-weight: 700;
    box-shadow: inset 3px 0 0 #38bdf8;
}

/* ── Cards ── */
.card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 16px;
    padding: 20px;
    margin: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.card:hover {
    border-color: rgba(56, 189, 248, 0.3);
    background: rgba(30, 41, 59, 0.5);
}

.card-title {
    font-size: 11px;
    font-weight: 700;
    color: #7dd3fc;
    
    letter-spacing: 1.5px;
    margin-bottom: 8px;
}

.card-value {
    font-size: 26px;
    font-weight: 800;
    color: #f1f5f9;
    letter-spacing: -0.5px;
}

/* ── Terminals ── */
.terminal-view {
    background-color: rgba(2, 6, 23, 0.95);
    color: #4ade80;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 13px;
    padding: 16px;
    border: 1px solid rgba(74, 222, 128, 0.1);
    border-radius: 12px;
}

.terminal-view text {
    background-color: transparent;
    color: #4ade80;
}

/* ── Buttons ── */
.action-btn {
    background: linear-gradient(135deg, #0ea5e9, #7c3aed);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 700;
    box-shadow: 0 4px 14px rgba(14, 165, 233, 0.3);
}

.action-btn:hover {
    background: linear-gradient(135deg, #38bdf8, #8b5cf6);
    box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4);
}

.danger-btn {
    background: linear-gradient(135deg, #ef4444, #991b1b);
    color: #ffffff;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 700;
}

.success-btn {
    background: linear-gradient(135deg, #10b981, #065f46);
    color: #ffffff;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 700;
}

/* ── Form Elements ── */
entry {
    background-color: rgba(15, 23, 42, 0.6);
    color: #f1f5f9;
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 8px;
    padding: 10px 14px;
    caret-color: #38bdf8;
}

entry:focus {
    border-color: #38bdf8;
    background-color: rgba(15, 23, 42, 0.8);
}

combobox button {
    background-color: rgba(15, 23, 42, 0.6);
    color: #f1f5f9;
    border: 1px solid rgba(56, 189, 248, 0.15);
    border-radius: 8px;
}

/* ── Progress ── */
progressbar progress {
    background: linear-gradient(90deg, #38bdf8, #a855f7);
    border-radius: 10px;
}

progressbar trough {
    background-color: rgba(30, 41, 59, 0.5);
    border-radius: 10px;
}

/* ── Status ── */
.status-ok { color: #4ade80; font-weight: 700; }
.status-warn { color: #fbbf24; font-weight: 700; }
.status-error { color: #f87171; font-weight: 700; }
.cyan-text { color: #38bdf8; }
.purple-text { color: #a855f7; }

/* ── Chat ── */
.ai-message {
    background-color: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(56, 189, 248, 0.1);
    border-radius: 16px 16px 16px 4px;
    padding: 14px 18px;
    margin: 4px 40px 4px 8px;
    color: #cbd5e1;
}

.user-message {
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(124, 58, 237, 0.1));
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 4px 8px 4px 40px;
    color: #f1f5f9;
}

/* ── Team selector ── */
.team-badge {
    border-radius: 16px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
}

.team-red { background-color: #3a0a0a; color: #ff4040; border: 1px solid #5a1a1a; }
.team-blue { background-color: #0a1a3a; color: #4080ff; border: 1px solid #1a3060; }
.team-purple { background-color: #2a0a3a; color: #a855f7; border: 1px solid #4a1a6a; }
.team-white { background-color: #1a1a1a; color: #d0d0d0; border: 1px solid #3a3a3a; }
.team-grey { background-color: #181818; color: #808080; border: 1px solid #303030; }
.team-brown { background-color: #2a1a0a; color: #cc8844; border: 1px solid #4a3020; }
.team-devops { background-color: #0a2a1a; color: #44cc88; border: 1px solid #1a4a30; }
"""

def get_css() -> str:
    return SHADOWCYPHER_CSS
