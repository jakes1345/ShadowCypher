#include "LoginDialog.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGuiApplication>
#include <QScreen>
#include <QDesktopServices>
#include <QRegularExpression>
#include <QSysInfo>
#include <QUrl>

LoginDialog::LoginDialog(ApiClient* api, QWidget* parent)
    : QDialog(parent), m_api(api)
{
    setWindowTitle("ShadowCypher");
    setFixedSize(400, 460);
    setWindowFlags(Qt::Dialog | Qt::FramelessWindowHint);
    setModal(true);
    setStyleSheet("LoginDialog, QDialog, QWidget { background: #080c1a; }");
    buildUi();

    m_pollTimer.setSingleShot(true);
    connect(&m_pollTimer, &QTimer::timeout, this, &LoginDialog::poll);

    if (auto* screen = QGuiApplication::primaryScreen()) {
        QRect sg = screen->availableGeometry();
        move(sg.center() - QPoint(width() / 2, height() / 2));
    }
}

QString LoginDialog::buttonStyle(bool primary) const {
    if (!primary) {
        return QStringLiteral(R"(
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255,255,255,0.10);
                color: #64748b;
                font-family: 'JetBrains Mono';
                font-size: 11px;
                letter-spacing: 1px;
                padding: 10px 0;
                border-radius: 8px;
            }
            QPushButton:hover { color: #94a3b8; border-color: rgba(255,255,255,0.2); }
        )");
    }
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
        QLineEdit:focus { border-color: rgba(180,74,255,0.5); }
    )");
}

static QLabel* hint(const QString& text) {
    auto* l = new QLabel(text);
    l->setWordWrap(true);
    l->setAlignment(Qt::AlignCenter);
    l->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 10px; background: transparent;");
    return l;
}

void LoginDialog::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(40, 40, 40, 40);
    lay->setSpacing(0);

    auto* logoLbl = new QLabel(
        "<div style='text-align:center;'>"
        "<span style='font-weight:900;font-size:20px;color:#b44aff;letter-spacing:4px;'>SHADOW</span>"
        "<span style='font-weight:300;font-size:20px;color:#e2e8f0;letter-spacing:2px;'>CYPHER</span>"
        "</div>");
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

    m_stack = new QStackedWidget;
    m_stack->setStyleSheet("QStackedWidget { background: transparent; }");

    // Start: sign in through the browser
    auto* startPage = new QWidget;
    auto* startLay = new QVBoxLayout(startPage);
    startLay->setContentsMargins(0, 0, 0, 0);
    startLay->setSpacing(12);
    startLay->addWidget(hint("Sign in on shadowcypher.site in your browser. "
                             "Your password is never entered in this app."));
    m_browserBtn = new QPushButton("SIGN IN WITH BROWSER");
    m_browserBtn->setStyleSheet(buttonStyle());
    m_browserBtn->setFixedHeight(46);
    connect(m_browserBtn, &QPushButton::clicked, this, &LoginDialog::startBrowserSignIn);
    startLay->addWidget(m_browserBtn);
    startLay->addStretch();
    m_stack->addWidget(startPage);

    // Waiting: show the code and wait for approval
    auto* waitPage = new QWidget;
    auto* waitLay = new QVBoxLayout(waitPage);
    waitLay->setContentsMargins(0, 0, 0, 0);
    waitLay->setSpacing(10);
    waitLay->addWidget(hint("Check that the browser shows this code, then approve:"));
    m_codeLabel = new QLabel;
    m_codeLabel->setAlignment(Qt::AlignCenter);
    m_codeLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);
    m_codeLabel->setStyleSheet(
        "color: #e2e8f0; font-family: 'JetBrains Mono'; font-size: 26px; font-weight: 700; "
        "letter-spacing: 6px; padding: 10px; background: #0d1122; border-radius: 8px;");
    waitLay->addWidget(m_codeLabel);
    m_waitLabel = hint("Waiting for approval…");
    waitLay->addWidget(m_waitLabel);
    m_openBtn = new QPushButton("OPEN SIGN-IN PAGE");
    m_openBtn->setStyleSheet(buttonStyle());
    connect(m_openBtn, &QPushButton::clicked, this, &LoginDialog::openVerifyPage);
    waitLay->addWidget(m_openBtn);
    auto* cancelBtn = new QPushButton("CANCEL");
    cancelBtn->setStyleSheet(buttonStyle(false));
    connect(cancelBtn, &QPushButton::clicked, this, &LoginDialog::cancelBrowserSignIn);
    waitLay->addWidget(cancelBtn);
    m_stack->addWidget(waitPage);

    // Key: paste an API key
    auto* keyPage = new QWidget;
    auto* keyLay = new QVBoxLayout(keyPage);
    keyLay->setContentsMargins(0, 0, 0, 0);
    keyLay->setSpacing(12);
    m_keyEdit = new QLineEdit;
    m_keyEdit->setPlaceholderText("sc_live_…");
    m_keyEdit->setEchoMode(QLineEdit::Password);
    m_keyEdit->setStyleSheet(inputStyle());
    connect(m_keyEdit, &QLineEdit::returnPressed, this, &LoginDialog::submitKey);
    keyLay->addWidget(m_keyEdit);
    m_keyBtn = new QPushButton("SIGN IN WITH KEY");
    m_keyBtn->setStyleSheet(buttonStyle());
    m_keyBtn->setFixedHeight(46);
    connect(m_keyBtn, &QPushButton::clicked, this, &LoginDialog::submitKey);
    keyLay->addWidget(m_keyBtn);
    keyLay->addStretch();
    m_stack->addWidget(keyPage);

    lay->addWidget(m_stack);
    lay->addSpacing(8);

    m_errorLabel = new QLabel;
    m_errorLabel->setStyleSheet(
        "color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; "
        "padding: 8px; background: rgba(244,63,94,0.08); border-radius: 6px;");
    m_errorLabel->setWordWrap(true);
    m_errorLabel->setAlignment(Qt::AlignCenter);
    m_errorLabel->hide();
    lay->addWidget(m_errorLabel);
    lay->addSpacing(8);

    m_toggleLink = new QLabel;
    m_toggleLink->setAlignment(Qt::AlignCenter);
    m_toggleLink->setTextFormat(Qt::RichText);
    connect(m_toggleLink, &QLabel::linkActivated, this, &LoginDialog::toggleKeyMode);
    lay->addWidget(m_toggleLink);

    lay->addStretch();

    auto* bottom = new QHBoxLayout;
    auto* verLbl = new QLabel("v1.0.0-qt6  ·  shadowcypher.site");
    verLbl->setStyleSheet(
        "color: #1e293b; font-family: 'JetBrains Mono'; font-size: 9px; letter-spacing: 1px;");
    bottom->addWidget(verLbl);
    bottom->addStretch();
    auto* quitLink = new QLabel("<a href='#' style='color:#334155;text-decoration:none;"
                                "font-family:JetBrains Mono;font-size:9px;'>quit</a>");
    quitLink->setTextFormat(Qt::RichText);
    connect(quitLink, &QLabel::linkActivated, this, &QDialog::reject);
    bottom->addWidget(quitLink);
    lay->addLayout(bottom);

    showPage(Start);
}

void LoginDialog::showPage(Page p) {
    m_stack->setCurrentIndex(p);
    m_toggleLink->setVisible(p != Waiting);
    m_toggleLink->setText(QString("<a href='#' style='color:#475569;text-decoration:none;"
                                  "font-family:JetBrains Mono;font-size:10px;'>%1</a>")
                              .arg(p == Key ? "sign in with browser instead" : "paste an API key instead"));
    if (p == Key) m_keyEdit->setFocus();
}

void LoginDialog::toggleKeyMode() {
    m_errorLabel->hide();
    showPage(m_stack->currentIndex() == Key ? Start : Key);
}

void LoginDialog::showError(const QString& msg) {
    m_errorLabel->setText(msg);
    m_errorLabel->show();
}

// ── Browser sign-in ───────────────────────────────────────────────────────────

void LoginDialog::startBrowserSignIn() {
    m_errorLabel->hide();
    m_browserBtn->setEnabled(false);
    m_browserBtn->setText("STARTING…");
    const QString label = "ShadowCypher desktop on " + QSysInfo::machineHostName();
    m_api->startDeviceAuth(label, this, [this](bool ok, QJsonDocument doc, int status) {
        m_browserBtn->setEnabled(true);
        m_browserBtn->setText("SIGN IN WITH BROWSER");
        const QJsonObject o = doc.object();
        const QString code = o.value("device_code").toString();
        const QString userCode = o.value("user_code").toString();
        if (!ok || code.isEmpty() || userCode.isEmpty()) {
            showError(status == 0 ? "Can't reach ShadowCypher. Check your connection."
                                  : QString("Couldn't start sign-in (HTTP %1).").arg(status));
            return;
        }
        m_deviceCode = code;
        m_verifyUrl = o.value("verification_uri_complete").toString(o.value("verification_uri").toString());
        m_codeLabel->setText(userCode);
        m_waitLabel->setText("Waiting for approval…");
        m_deadline.setRemainingTime(qBound(60, o.value("expires_in").toInt(600), 1800) * 1000);
        m_pollTimer.setInterval(qBound(2, o.value("interval").toInt(5), 30) * 1000);
        showPage(Waiting);
        openVerifyPage();
        m_pollTimer.start();
    });
}

void LoginDialog::openVerifyPage() {
    // The URL comes from the server; only hand the browser a web page.
    const QUrl url(m_verifyUrl);
    const bool local = url.host() == "127.0.0.1" || url.host() == "localhost";
    if (url.scheme() == "https" || (url.scheme() == "http" && local))
        QDesktopServices::openUrl(url);
    else
        showError("The server sent an unexpected sign-in address.");
}

void LoginDialog::cancelBrowserSignIn() {
    stopPolling();
    showPage(Start);
}

void LoginDialog::stopPolling(const QString& error) {
    m_pollTimer.stop();
    m_deviceCode.clear();
    if (!error.isEmpty()) {
        showPage(Start);
        showError(error);
    }
}

void LoginDialog::poll() {
    if (m_deviceCode.isEmpty()) return;
    if (m_deadline.hasExpired()) {
        stopPolling("The sign-in code expired. Start again.");
        return;
    }
    const QString code = m_deviceCode;
    m_api->pollDeviceAuth(code, this, [this, code](bool ok, QJsonDocument doc, int status) {
        if (code != m_deviceCode) return;   // cancelled or restarted meanwhile
        const QJsonObject o = doc.object();
        const QString state = o.value("status").toString();
        if (ok && state == "authorized") {
            const QString key = o.value("api_key").toString();
            stopPolling();
            if (key.isEmpty()) { showPage(Start); showError("Sign-in finished without a key. Try again."); return; }
            finishWithKey(key);
            return;
        }
        if (state == "denied" || status == 403) { stopPolling("Sign-in was denied in the browser."); return; }
        if (state == "expired" || state == "consumed" || status == 410) {
            stopPolling("The sign-in code expired. Start again.");
            return;
        }
        if (status == 404 || status == 400) { stopPolling("The sign-in code wasn't recognised. Start again."); return; }
        // pending, offline (0), rate-limited or a server error: keep waiting
        m_waitLabel->setText(status == 0 || status >= 500 ? "Connection problem, still trying…"
                                                          : "Waiting for approval…");
        m_pollTimer.start();
    });
}

// ── API key ───────────────────────────────────────────────────────────────────

void LoginDialog::submitKey() {
    m_errorLabel->hide();
    const QString key = m_keyEdit->text().trimmed();
    static const QRegularExpression keyRe("^sc_live_[a-f0-9]{48}$");
    if (!keyRe.match(key).hasMatch()) {
        showError("That doesn't look like an API key (sc_live_ followed by 48 characters).");
        return;
    }
    finishWithKey(key);
}

// Every key is checked with the server before it's saved.
void LoginDialog::finishWithKey(const QString& key) {
    m_keyBtn->setEnabled(false);
    m_keyBtn->setText("CHECKING…");
    m_api->verifyKey(key, this, [this, key](bool ok, int status, QString) {
        m_keyBtn->setEnabled(true);
        m_keyBtn->setText("SIGN IN WITH KEY");
        if (ok) {
            m_api->setApiKey(key);
            accept();
            return;
        }
        if (m_stack->currentIndex() != Key) showPage(Start);
        showError(status == 0 ? "Can't reach ShadowCypher. Check your connection."
                  : status == 401 || status == 403 ? "That key was rejected. It may have been revoked."
                  : QString("Couldn't check the key (HTTP %1).").arg(status));
    });
}
