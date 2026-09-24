#include "LoginDialog.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QApplication>
#include <QScreen>
#include <QGuiApplication>
#include <QKeyEvent>

LoginDialog::LoginDialog(ApiClient* api, QWidget* parent)
    : QDialog(parent), m_api(api)
{
    setWindowTitle("ShadowCypher");
    setFixedSize(400, 460);
    setWindowFlags(Qt::Dialog | Qt::FramelessWindowHint);
    setModal(true);
    setStyleSheet(R"(
        LoginDialog {
            background: #080c1a;
        }
        QDialog {
            background: #080c1a;
        }
        QWidget {
            background: #080c1a;
        }
    )");
    buildUi();

    if (auto* screen = QGuiApplication::primaryScreen()) {
        QRect sg = screen->availableGeometry();
        move(sg.center() - QPoint(width() / 2, height() / 2));
    }
}

QString LoginDialog::buttonStyle() const {
    return QStringLiteral(R"(
        QPushButton {
            background: rgba(180,74,255,0.15);
            border: 1px solid rgba(180,74,255,0.5);
            color: #b44aff;
            font-family: 'JetBrains Mono';
            font-size: 12px;
            letter-spacing: 2px;
            padding: 12px 0;
            border-radius: 8px;
            font-weight: 700;
        }
        QPushButton:hover { background: rgba(180,74,255,0.25); }
        QPushButton:pressed { background: rgba(180,74,255,0.35); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )");
}

QString LoginDialog::inputStyle() const {
    return QStringLiteral(R"(
        QLineEdit {
            background: #0d1122;
            color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 12px 14px;
            font-family: 'JetBrains Mono';
            font-size: 12px;
        }
        QLineEdit:focus {
            border-color: rgba(180,74,255,0.5);
        }
        QLineEdit::placeholder {
            color: #334155;
        }
    )");
}

void LoginDialog::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(40, 40, 40, 40);
    lay->setSpacing(0);

    // ── Logo ──
    auto* logoLbl = new QLabel;
    logoLbl->setText(
        "<div style='text-align:center;'>"
        "<span style='font-weight:900;font-size:20px;color:#b44aff;letter-spacing:4px;'>SHADOW</span>"
        "<span style='font-weight:300;font-size:20px;color:#e2e8f0;letter-spacing:2px;'>CYPHER</span>"
        "</div>"
    );
    logoLbl->setTextFormat(Qt::RichText);
    logoLbl->setAlignment(Qt::AlignCenter);
    lay->addWidget(logoLbl);
    lay->addSpacing(6);

    auto* subtitleLbl = new QLabel("TACTICAL ACCESS CONTROL");
    subtitleLbl->setAlignment(Qt::AlignCenter);
    subtitleLbl->setStyleSheet(
        "color: #1e293b; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 3px;");
    lay->addWidget(subtitleLbl);
    lay->addSpacing(32);

    // ── Form stack: page 0 = handle/password, page 1 = API key ──
    m_formStack = new QStackedWidget;
    m_formStack->setStyleSheet("QStackedWidget { background: transparent; }");

    // Page 0: handle + password
    auto* pwPage = new QWidget;
    pwPage->setStyleSheet("QWidget { background: transparent; }");
    auto* pwLay = new QVBoxLayout(pwPage);
    pwLay->setContentsMargins(0, 0, 0, 0);
    pwLay->setSpacing(10);

    m_handleEdit = new QLineEdit;
    m_handleEdit->setPlaceholderText("handle");
    m_handleEdit->setStyleSheet(inputStyle());
    pwLay->addWidget(m_handleEdit);

    m_passwordEdit = new QLineEdit;
    m_passwordEdit->setPlaceholderText("password");
    m_passwordEdit->setEchoMode(QLineEdit::Password);
    m_passwordEdit->setStyleSheet(inputStyle());
    connect(m_passwordEdit, &QLineEdit::returnPressed, this, &LoginDialog::onLoginClicked);
    pwLay->addWidget(m_passwordEdit);
    m_formStack->addWidget(pwPage);

    // Page 1: API key directly
    auto* keyPage = new QWidget;
    keyPage->setStyleSheet("QWidget { background: transparent; }");
    auto* keyLay = new QVBoxLayout(keyPage);
    keyLay->setContentsMargins(0, 0, 0, 0);
    keyLay->setSpacing(10);

    m_keyEdit = new QLineEdit;
    m_keyEdit->setPlaceholderText("sc_live_…");
    m_keyEdit->setStyleSheet(inputStyle());
    connect(m_keyEdit, &QLineEdit::returnPressed, this, &LoginDialog::onLoginClicked);
    keyLay->addWidget(m_keyEdit);
    m_formStack->addWidget(keyPage);

    lay->addWidget(m_formStack);
    lay->addSpacing(6);

    // ── Toggle link ──
    m_toggleLink = new QLabel("<a href='#' style='color:#334155;text-decoration:none;"
                              "font-family:JetBrains Mono;font-size:10px;'>use api key instead</a>");
    m_toggleLink->setAlignment(Qt::AlignRight);
    m_toggleLink->setTextFormat(Qt::RichText);
    m_toggleLink->setOpenExternalLinks(false);
    connect(m_toggleLink, &QLabel::linkActivated, this, &LoginDialog::toggleKeyMode);
    lay->addWidget(m_toggleLink);
    lay->addSpacing(16);

    // ── Error label ──
    m_errorLabel = new QLabel;
    m_errorLabel->setStyleSheet(
        "color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; "
        "padding: 8px; background: rgba(244,63,94,0.08); border-radius: 6px;");
    m_errorLabel->setWordWrap(true);
    m_errorLabel->setAlignment(Qt::AlignCenter);
    m_errorLabel->hide();
    lay->addWidget(m_errorLabel);
    lay->addSpacing(8);

    // ── Login button ──
    m_loginBtn = new QPushButton("ACCESS SYSTEM");
    m_loginBtn->setStyleSheet(buttonStyle());
    m_loginBtn->setFixedHeight(46);
    connect(m_loginBtn, &QPushButton::clicked, this, &LoginDialog::onLoginClicked);
    lay->addWidget(m_loginBtn);

    lay->addStretch();

    // ── Version ──
    auto* verLbl = new QLabel("v1.0.0-qt6  ·  shadowcypher.site");
    verLbl->setAlignment(Qt::AlignCenter);
    verLbl->setStyleSheet(
        "color: #1e293b; font-family: 'JetBrains Mono'; font-size: 9px; letter-spacing: 1px;");
    lay->addWidget(verLbl);
}

void LoginDialog::toggleKeyMode() {
    m_keyMode = !m_keyMode;
    m_formStack->setCurrentIndex(m_keyMode ? 1 : 0);
    m_toggleLink->setText(
        m_keyMode
        ? "<a href='#' style='color:#334155;text-decoration:none;"
          "font-family:JetBrains Mono;font-size:10px;'>use handle/password instead</a>"
        : "<a href='#' style='color:#334155;text-decoration:none;"
          "font-family:JetBrains Mono;font-size:10px;'>use api key instead</a>"
    );
    m_errorLabel->hide();
}

void LoginDialog::onLoginClicked() {
    m_errorLabel->hide();
    setLoading(true);

    if (m_keyMode) {
        QString key = m_keyEdit->text().trimmed();
        if (!key.startsWith("sc_live_") || key.length() < 16) {
            showError("Invalid API key format — must start with sc_live_");
            setLoading(false);
            return;
        }
        m_api->setApiKey(key);
        accept();
        return;
    }

    QString handle = m_handleEdit->text().trimmed();
    QString password = m_passwordEdit->text();
    if (handle.isEmpty() || password.isEmpty()) {
        showError("Handle and password are required");
        setLoading(false);
        return;
    }

    m_api->login(handle, password, this,
                 [this](bool ok, QString errMsg) {
        setLoading(false);
        if (ok) {
            accept();
        } else {
            showError(errMsg);
        }
    });
}

void LoginDialog::setLoading(bool loading) {
    m_loginBtn->setEnabled(!loading);
    m_loginBtn->setText(loading ? "AUTHENTICATING…" : "ACCESS SYSTEM");
    if (m_formStack->currentWidget())
        m_formStack->currentWidget()->setEnabled(!loading);
}

void LoginDialog::showError(const QString& msg) {
    m_errorLabel->setText(msg);
    m_errorLabel->show();
}
