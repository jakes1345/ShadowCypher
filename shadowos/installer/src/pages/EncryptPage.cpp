#include "EncryptPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QMessageBox>

static QString entryStyle() {
    return QString(
        "QLineEdit { background:%1; border:1px solid rgba(255,255,255,0.10);"
        " border-radius:8px; padding:9px 12px; color:#E6EDF3;"
        " font-family:'JetBrains Mono',monospace; font-size:12px; }"
        "QLineEdit:focus { border-color:%2; }"
    ).arg(Theme::BG_SURFACE, Theme::ACCENT);
}

static QWidget* fieldWidget(const QString& label, QLineEdit* entry) {
    auto* box = new QWidget;
    auto* lay = new QVBoxLayout(box);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(4);
    auto* lbl = new QLabel(label);
    lbl->setStyleSheet(QString("font-size:11px;font-weight:600;color:%1;").arg(Theme::TEXT_SEC));
    lay->addWidget(lbl);
    lay->addWidget(entry);
    return box;
}

EncryptPage::EncryptPage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 02 — ENCRYPTION");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Full-Disk Encryption");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");
    auto* sub = new QLabel(
        "LUKS2 encrypts your entire drive. Your passphrase is required every boot — "
        "without it the data is unreadable."
    );
    sub->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    auto* toggleRow = new QHBoxLayout;
    m_enableBox = new QCheckBox("Enable LUKS2 full-disk encryption  (strongly recommended)");
    m_enableBox->setChecked(m_state->luks);
    m_enableBox->setStyleSheet(QString(
        "QCheckBox { font-size:13px; font-weight:600; color:#E6EDF3; spacing:10px; }"
        "QCheckBox::indicator { width:20px; height:20px; border-radius:5px;"
        " border:2px solid %1; background:transparent; }"
        "QCheckBox::indicator:checked { background:%2; border-color:%2; }"
    ).arg(Theme::TEXT_DIM, Theme::ACCENT));
    toggleRow->addWidget(m_enableBox);
    toggleRow->addStretch();

    m_fields = new QWidget;
    auto* fl = new QVBoxLayout(m_fields);
    fl->setContentsMargins(0, 0, 0, 0);
    fl->setSpacing(12);

    m_pass1 = new QLineEdit;
    m_pass1->setEchoMode(QLineEdit::Password);
    m_pass1->setPlaceholderText("Minimum 8 characters");
    m_pass1->setStyleSheet(entryStyle());

    m_pass2 = new QLineEdit;
    m_pass2->setEchoMode(QLineEdit::Password);
    m_pass2->setPlaceholderText("Repeat passphrase");
    m_pass2->setStyleSheet(entryStyle());

    fl->addWidget(fieldWidget("LUKS Passphrase", m_pass1));
    fl->addWidget(fieldWidget("Confirm Passphrase", m_pass2));

    m_fields->setVisible(m_state->luks);
    connect(m_enableBox, &QCheckBox::toggled, m_fields, &QWidget::setVisible);
    connect(m_enableBox, &QCheckBox::toggled, this, [this](bool v) { m_state->luks = v; });

    auto* warn = new QLabel(
        "  ⚠  Write your passphrase down and store it securely. "
        "If lost, your data cannot be recovered — there is no bypass."
    );
    warn->setStyleSheet(QString(
        "font-size:12px;color:%1;"
        "background:rgba(255,221,0,0.05);"
        "border:1px solid rgba(255,221,0,0.28);"
        "border-radius:7px;padding:10px 14px;"
    ).arg(Theme::WARNING));
    warn->setWordWrap(true);

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(divider);
    lay->addLayout(toggleRow);
    lay->addWidget(m_fields);
    lay->addWidget(warn);
    lay->addStretch();
}

void EncryptPage::save() {
    m_state->luks     = m_enableBox->isChecked();
    m_state->luksPass = m_pass1->text();
}

bool EncryptPage::validate() {
    if (!m_enableBox->isChecked()) return true;
    if (m_pass1->text().length() < 8) {
        QMessageBox::warning(this, "Weak Passphrase",
                             "LUKS passphrase must be at least 8 characters.");
        return false;
    }
    if (m_pass1->text() != m_pass2->text()) {
        QMessageBox::warning(this, "Mismatch", "Passphrases do not match.");
        return false;
    }
    m_state->luksPass = m_pass1->text();
    return true;
}
