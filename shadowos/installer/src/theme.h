#pragma once
#include <QString>

namespace Theme {

inline constexpr auto BG_BASE    = "#060C14";
inline constexpr auto BG_SURFACE = "#0C1522";
inline constexpr auto BG_CARD    = "#0F1C2E";

inline constexpr auto ACCENT     = "#00E0A4";
inline constexpr auto ACCENT2    = "#00B4D8";
inline constexpr auto SUCCESS    = "#00E0A4";
inline constexpr auto WARNING    = "#FFDD00";
inline constexpr auto DANGER     = "#F87171";

inline constexpr auto TEXT_PRI   = "#E6EDF3";
inline constexpr auto TEXT_SEC   = "#8D96A0";
inline constexpr auto TEXT_DIM   = "#3D4B5C";

inline constexpr auto BORDER     = "rgba(0,224,164,0.14)";
inline constexpr auto BORDER_DIM = "rgba(255,255,255,0.07)";

inline constexpr int SIDEBAR_W = 220;
inline constexpr int WIN_W     = 1040;
inline constexpr int WIN_H     = 700;

inline QString appStyleSheet() {
    return QStringLiteral(R"(
QWidget {
    background-color: #060C14;
    color: #E6EDF3;
    font-family: "Outfit", "Inter", sans-serif;
    font-size: 13px;
}
QScrollBar:vertical {
    background: #0C1522;
    width: 5px;
    border-radius: 2px;
}
QScrollBar::handle:vertical {
    background: #1E2D40;
    border-radius: 2px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 5px; background: #0C1522; }
QScrollBar::handle:horizontal { background: #1E2D40; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: rgba(0,224,164,0.10); width: 1px; }
QToolTip {
    background: #0C1522;
    color: #E6EDF3;
    border: 1px solid rgba(0,224,164,0.25);
    padding: 4px 8px;
    border-radius: 4px;
}
)");
}

} // namespace Theme
