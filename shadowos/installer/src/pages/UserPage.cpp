#include "UserPage.h"
#include "../theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QMessageBox>
#include <QRegularExpression>

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

UserPage::UserPage(InstallState* state, QWidget* parent)
    : QWidget(parent), m_state(state)
{
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(48, 40, 48, 40);
    lay->setSpacing(16);

    auto* tag = new QLabel("STEP 03 — USER ACCOUNT");
    tag->setStyleSheet(QString("font-size:9px;font-weight:800;letter-spacing:5px;"
                               "color:%1;font-family:'JetBrains Mono',monospace;").arg(Theme::ACCENT));
    auto* title = new QLabel("Create Your Account");
    title->setStyleSheet("font-size:28px;font-weight:900;color:#E6EDF3;");
    auto* sub = new QLabel("This account will have sudo access. Choose a strong password.");
    sub->setStyleSheet(QString("font-size:13px;color:%1;").arg(Theme::TEXT_SEC));
    sub->setWordWrap(true);

    auto* divider = new QFrame;
    divider->setFrameShape(QFrame::HLine);
    divider->setStyleSheet("border: none; border-top: 1px solid rgba(0,224,164,0.12);");

    m_username = new QLineEdit;
    m_username->setPlaceholderText("e.g. shadow");
    m_username->setText(m_state->username);
    m_username->setStyleSheet(entryStyle());

    m_password = new QLineEdit;
    m_password->setEchoMode(QLineEdit::Password);
    m_password->setPlaceholderText("Minimum 8 characters");
    m_password->setStyleSheet(entryStyle());

    m_password2 = new QLineEdit;
    m_password2->setEchoMode(QLineEdit::Password);
    m_password2->setPlaceholderText("Confirm password");
    m_password2->setStyleSheet(entryStyle());

    m_hostname = new QLineEdit;
    m_hostname->setPlaceholderText("e.g. shadowos");
    m_hostname->setText(m_state->hostname);
    m_hostname->setStyleSheet(entryStyle());

    lay->addWidget(tag);
    lay->addWidget(title);
    lay->addWidget(sub);
    lay->addWidget(divider);
    lay->addWidget(fieldWidget("Username", m_username));
    lay->addWidget(fieldWidget("Password", m_password));
    lay->addWidget(fieldWidget("Confirm Password", m_password2));
    lay->addWidget(fieldWidget("Hostname", m_hostname));
    lay->addStretch();
}

bool UserPage::validate() {
    static QRegularExpression validUser("^[a-z_][a-z0-9_-]{0,30}$");
    static QRegularExpression validHost("^[a-zA-Z0-9][a-zA-Z0-9-]{0,62}$");

    if (!validUser.match(m_username->text()).hasMatch()) {
        QMessageBox::warning(this, "Invalid Username",
            "Username must be lowercase letters, digits, _ or -, starting with a letter or _.");
        return false;
    }
    if (m_password->text().length() < 8) {
        QMessageBox::warning(this, "Weak Password", "Password must be at least 8 characters.");
        return false;
    }
    if (m_password->text() != m_password2->text()) {
        QMessageBox::warning(this, "Mismatch", "Passwords do not match.");
        return false;
    }
    if (!validHost.match(m_hostname->text()).hasMatch()) {
        QMessageBox::warning(this, "Invalid Hostname",
            "Hostname must be alphanumeric and hyphens only, starting with a letter or digit.");
        return false;
    }
    return true;
}

void UserPage::save() {
    m_state->username = m_username->text();
    m_state->password = m_password->text();
    m_state->hostname = m_hostname->text();
}
