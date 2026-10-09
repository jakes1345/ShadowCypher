#include "SummaryPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QGridLayout>
#include <QFrame>

static QWidget* summaryRow(const QString& key, QLabel*& valOut) {
    auto* box = new QWidget;
    auto* lay = new QHBoxLayout(box);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(0);

    auto* k = new QLabel(key);
    k->setStyleSheet(QString("font-size:12px;font-weight:600;color:%1;"
                             "font-family:'JetBrains Mono',monospace;").arg(Theme::TEXT_SEC));
    k->setFixedWidth(160);

    valOut = new QLabel("—");
    valOut->setStyleSheet("font-size:12px;color:#E6EDF3;");

    lay->addWidget(k);
    lay->addWidget(valOut);
    lay->addStretch();
    return box;
}

SummaryPage::SummaryPage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 05 — REVIEW");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Confirm Installation");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");
    auto* sub = new QLabel(
        "Review your choices below. Clicking  Install  will erase the selected disk "
        "and begin the installation — this cannot be undone."
    );
    sub->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    auto* card = new QWidget;
    card->setStyleSheet(QString(
        "QWidget { background:%1; border:1px solid %2; border-radius:12px; }"
    ).arg(Theme::BG_SURFACE, Theme::BORDER_DIM));
    auto* cl = new QVBoxLayout(card);
    cl->setContentsMargins(0, 4, 0, 4);
    cl->setSpacing(0);

    auto* addSep = [&]() {
        auto* sep = new QFrame;
        sep->setFrameShape(QFrame::HLine);
        sep->setStyleSheet(QString("border: none; border-top: 1px solid %1;").arg(Theme::BORDER_DIM));
        cl->addWidget(sep);
    };

    cl->addWidget(summaryRow("Disk", m_disk));      addSep();
    cl->addWidget(summaryRow("Encryption", m_luks)); addSep();
    cl->addWidget(summaryRow("Username", m_user));   addSep();
    cl->addWidget(summaryRow("Hostname", m_host));   addSep();
    cl->addWidget(summaryRow("Profile", m_profile)); addSep();
    cl->addWidget(summaryRow("Locale", m_locale));   addSep();
    cl->addWidget(summaryRow("Timezone", m_tz));

    auto* danger = new QLabel(
        "  ◬  ALL DATA on the selected disk will be PERMANENTLY DESTROYED. "
        "There is no undo once installation begins."
    );
    danger->setStyleSheet(QString(
        "font-size:12px;color:%1;"
        "background:rgba(248,113,113,0.07);"
        "border:1px solid rgba(248,113,113,0.32);"
        "border-radius:7px;padding:10px 14px;"
    ).arg(Theme::DANGER));
    danger->setWordWrap(true);

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(divider);
    lay->addWidget(card);
    lay->addWidget(danger);
    lay->addStretch();
}

void SummaryPage::refresh() {
    m_disk->setText(m_state->disk.isEmpty() ? "—" : m_state->disk);
    m_luks->setText(m_state->luks ? QString("LUKS2 enabled") : "None");
    m_user->setText(m_state->username);
    m_host->setText(m_state->hostname);

    QString prof = m_state->profile;
    if (prof == "standard") prof = "Standard (Privacy-hardened daily driver)";
    else if (prof == "pentest") prof = "Pentest (Offensive security suite)";
    else if (prof == "privacy") prof = "Privacy / Ghost (Maximum anonymity)";
    else if (prof == "gaming")  prof = "Gaming (SteamOS-inspired)";
    m_profile->setText(prof);

    m_locale->setText(m_state->locale);
    m_tz->setText(m_state->timezone);
}
