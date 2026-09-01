#pragma once
#include <QPlainTextEdit>

// Scrolling telemetry terminal — monospace dark glass widget
class TacticalTerminal : public QPlainTextEdit {
    Q_OBJECT
public:
    explicit TacticalTerminal(QWidget* parent = nullptr);

    void log(const QString& text, const QString& level = "INFO");

private:
    static QString colorForLevel(const QString& level);
    static constexpr int MAX_LINES = 500;
};
