#pragma once
#include <QWidget>
#include <QLabel>
#include <QVBoxLayout>

// Stub page shown for sections not yet ported from Python
class PlaceholderPage : public QWidget {
    Q_OBJECT
public:
    explicit PlaceholderPage(const QString& name, QWidget* parent = nullptr)
        : QWidget(parent)
    {
        auto* lay = new QVBoxLayout(this);
        lay->setAlignment(Qt::AlignCenter);

        auto* icon = new QLabel("⚙", this);
        icon->setAlignment(Qt::AlignCenter);
        icon->setStyleSheet("font-size: 48px; color: #1e293b;");
        lay->addWidget(icon);

        auto* lbl = new QLabel(name + "\nCOMING IN Qt6 PHASE 2", this);
        lbl->setAlignment(Qt::AlignCenter);
        lbl->setStyleSheet(
            "color: #334155; font-family: 'JetBrains Mono'; font-size: 14px; "
            "letter-spacing: 2px; line-height: 1.8;"
        );
        lay->addWidget(lbl);
    }
};
