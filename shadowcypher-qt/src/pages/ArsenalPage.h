#pragma once
#include <QWidget>
#include <QLabel>
#include <QTimer>

class ArsenalPage : public QWidget {
    Q_OBJECT
public:
    explicit ArsenalPage(QWidget* parent = nullptr);

private slots:
    void audit();

private:
    struct ToolCard {
        QString cmd;
        QString label;
        QString category;
        QString installHint;
        QLabel* dot;
        QLabel* statusLabel;
    };
    QList<ToolCard> m_tools;

    void buildUi();
    QWidget* makeCard(ToolCard& tool);
};
