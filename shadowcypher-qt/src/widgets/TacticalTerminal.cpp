#include "TacticalTerminal.h"
#include <QScrollBar>
#include <QDateTime>
#include <QTextCursor>

TacticalTerminal::TacticalTerminal(QWidget* parent) : QPlainTextEdit(parent) {
    setReadOnly(true);
    setMaximumBlockCount(MAX_LINES);
    setStyleSheet(R"(
        QPlainTextEdit {
            background-color: #060810;
            color: #94a3b8;
            font-family: "JetBrains Mono", monospace;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
            padding: 8px;
        }
    )");
}

QString TacticalTerminal::colorForLevel(const QString& level) {
    if (level == "CRITICAL" || level == "ERROR")  return "#f43f5e";
    if (level == "WARNING")  return "#ffb84d";
    if (level == "SUCCESS")  return "#00ff9d";
    if (level == "SYSTEM")   return "#b44aff";
    if (level == "INTEL")    return "#00d4ff";
    return "#94a3b8"; // INFO / default
}

void TacticalTerminal::log(const QString& text, const QString& level) {
    QString ts   = QDateTime::currentDateTime().toString("HH:mm:ss");
    QString col  = colorForLevel(level);
    QString html = QString(
        "<span style='color:#475569;'>[%1]</span> "
        "<span style='color:%2;font-weight:700;'>%3</span> "
        "<span style='color:#cbd5e1;'>%4</span>"
    ).arg(ts, col, level, text.toHtmlEscaped());

    appendHtml(html);
    verticalScrollBar()->setValue(verticalScrollBar()->maximum());
}
