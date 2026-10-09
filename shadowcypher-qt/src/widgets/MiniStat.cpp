#include "MiniStat.h"
#include <QVBoxLayout>

MiniStat::MiniStat(const QString& title, const QString& value,
                   const QString& accent, QWidget* parent)
    : QWidget(parent), m_accent(accent)
{
    setStyleSheet(
        "QWidget { background: rgba(255,255,255,0.02); "
        "border: 1px solid rgba(255,255,255,0.05); border-radius: 6px; }"
    );

    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(10, 8, 10, 8);
    lay->setSpacing(2);

    auto* titleLbl = new QLabel(title.toUpper(), this);
    titleLbl->setStyleSheet("color: #475569; font-size: 9px; letter-spacing: 1.5px; background: transparent; border: none;");
    lay->addWidget(titleLbl);

    m_valLabel = new QLabel(this);
    m_valLabel->setStyleSheet(
        QString("color: %1; font-weight: 800; font-size: 13px; background: transparent; border: none;")
        .arg(accent)
    );
    m_valLabel->setText(value);
    lay->addWidget(m_valLabel);
}

void MiniStat::setValue(const QString& val) {
    m_valLabel->setText(val);
}
