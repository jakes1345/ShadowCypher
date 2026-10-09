#pragma once
#include <QColor>
#include <QString>

namespace Theme {

// Core palette — matches shadowcypher CSS variables exactly
inline constexpr auto BG_BASE     = "#0d0f1a";
inline constexpr auto BG_SURFACE  = "#111827";
inline constexpr auto BG_CARD     = "#161d2f";

inline constexpr auto ACCENT      = "#b44aff";   // --accent-primary
inline constexpr auto ACCENT_GLOW = "#7c3aed";
inline constexpr auto CYAN        = "#00d4ff";   // --accent-secondary

inline constexpr auto SUCCESS     = "#00ff9d";
inline constexpr auto WARNING     = "#ffb84d";
inline constexpr auto CRITICAL    = "#f43f5e";
inline constexpr auto INFO        = "#38bdf8";

inline constexpr auto TEXT_PRIMARY   = "#e2e8f0";
inline constexpr auto TEXT_SECONDARY = "#94a3b8";
inline constexpr auto TEXT_DIM       = "#475569";

inline constexpr auto BORDER = "rgba(255,255,255,0.06)";

// Font families
inline constexpr auto FONT_MAIN = "Inter, Outfit, sans-serif";
inline constexpr auto FONT_MONO = "JetBrains Mono, monospace";

// Sidebar width
inline constexpr int SIDEBAR_W = 220;

// Global stylesheet applied to QApplication
inline QString appStyleSheet() {
    return QStringLiteral(R"(
QWidget {
    background-color: #0d0f1a;
    color: #e2e8f0;
    font-family: "Inter", "Outfit", sans-serif;
    font-size: 13px;
}
QScrollBar:vertical {
    background: #111827;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1e293b;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { height: 6px; background: #111827; border-radius: 3px; }
QScrollBar::handle:horizontal { background: #1e293b; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QSplitter::handle { background: rgba(255,255,255,0.06); width: 1px; }
QToolTip {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid rgba(255,255,255,0.1);
    padding: 4px 8px;
    border-radius: 4px;
}
)");
}

} // namespace Theme
