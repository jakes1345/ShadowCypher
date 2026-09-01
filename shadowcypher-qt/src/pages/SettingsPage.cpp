#include "SettingsPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QFrame>
#include <QSettings>
#include <QDir>
#include <QTimer>

// Config file path: ~/.config/shadowcypher/config.ini
static QString configPath() {
    return QDir::homePath() + "/.config/shadowcypher/config.ini";
}

// ── Static style helpers ──────────────────────────────────────────────────────

QString SettingsPage::buttonStyle() {
    return QStringLiteral(R"(
        QPushButton {
            background: rgba(180,74,255,0.15);
            border: 1px solid rgba(180,74,255,0.4);
            color: #b44aff;
            font-family: 'JetBrains Mono';
            font-size: 11px;
            letter-spacing: 1px;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: 700;
        }
        QPushButton:hover { background: rgba(180,74,255,0.25); }
        QPushButton:pressed { background: rgba(180,74,255,0.35); }
    )");
}

QString SettingsPage::inputStyle() {
    return QStringLiteral(R"(
        QLineEdit {
            background: #060810;
            color: #e2e8f0;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            padding: 6px 10px;
            font-family: 'JetBrains Mono';
            font-size: 12px;
        }
        QLineEdit:focus {
            border-color: rgba(180,74,255,0.5);
        }
    )");
}

QString SettingsPage::checkStyle() {
    return QStringLiteral(R"(
        QCheckBox {
            color: #e2e8f0;
            font-family: 'JetBrains Mono';
            font-size: 12px;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.15);
            background: #060810;
        }
        QCheckBox::indicator:checked {
            background: rgba(180,74,255,0.7);
            border-color: #b44aff;
        }
        QCheckBox::indicator:hover {
            border-color: rgba(180,74,255,0.4);
        }
        QCheckBox::indicator:checked:hover {
            background: rgba(180,74,255,0.85);
        }
    )");
}

// ── Constructor ───────────────────────────────────────────────────────────────

SettingsPage::SettingsPage(QWidget* parent) : QWidget(parent) {
    // Ensure config directory exists so QSettings can write on first save
    QDir().mkpath(QDir::homePath() + "/.config/shadowcypher");
    buildUi();
    loadSettings();
}

// ── UI construction ───────────────────────────────────────────────────────────

void SettingsPage::buildUi() {
    auto* outerLay = new QVBoxLayout(this);
    outerLay->setContentsMargins(0, 0, 0, 0);
    outerLay->setSpacing(0);

    // Scroll area wraps all content so the page works on small screens
    auto* scroll = new QScrollArea(this);
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    scroll->setStyleSheet("QScrollArea { background: #0d0f1a; border: none; }");

    auto* content = new QWidget;
    content->setStyleSheet("QWidget { background: #0d0f1a; }");
    auto* lay = new QVBoxLayout(content);
    lay->setContentsMargins(28, 20, 28, 28);
    lay->setSpacing(20);

    // ── Page header ──
    auto* titleLbl = new QLabel;
    titleLbl->setText(
        "<span style='font-weight:900;font-size:16px;color:#b44aff;letter-spacing:3px;'>"
        "SETTINGS</span>"
    );
    titleLbl->setTextFormat(Qt::RichText);
    lay->addWidget(titleLbl);

    // ─────────────────────────────────────────────────────────────────────────
    // Section 1: API Key Manager
    // ─────────────────────────────────────────────────────────────────────────
    {
        auto* card = new QWidget;
        card->setStyleSheet(
            "QWidget { background: #111827; border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 10px; }"
        );
        auto* cardLay = new QVBoxLayout(card);
        cardLay->setContentsMargins(20, 16, 20, 16);
        cardLay->setSpacing(12);

        auto* heading = new QLabel;
        heading->setText(
            "<span style='font-weight:800;color:#94a3b8;font-size:11px;"
            "letter-spacing:2px;'>API KEY MANAGER</span>"
        );
        heading->setTextFormat(Qt::RichText);
        cardLay->addWidget(heading);

        // Input + show/hide toggle
        auto* inputRow = new QHBoxLayout;

        m_apiKeyEdit = new QLineEdit;
        m_apiKeyEdit->setEchoMode(QLineEdit::Password);
        m_apiKeyEdit->setPlaceholderText(
            "sc_live_••••••••••••"
            "••••••••••••"
        );
        m_apiKeyEdit->setStyleSheet(inputStyle());
        inputRow->addWidget(m_apiKeyEdit, 1);

        m_showHideBtn = new QPushButton("SHOW");
        m_showHideBtn->setCheckable(true);
        m_showHideBtn->setStyleSheet(QStringLiteral(R"(
            QPushButton {
                background: rgba(180,74,255,0.10);
                border: 1px solid rgba(180,74,255,0.3);
                color: #b44aff;
                font-family: 'JetBrains Mono';
                font-size: 10px;
                letter-spacing: 1px;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 700;
            }
            QPushButton:hover   { background: rgba(180,74,255,0.20); }
            QPushButton:checked { background: rgba(180,74,255,0.15); color: #d08aff; }
        )"));
        connect(m_showHideBtn, &QPushButton::toggled,
                this, &SettingsPage::toggleApiKeyVisibility);
        inputRow->addWidget(m_showHideBtn);
        cardLay->addLayout(inputRow);

        // Save button row
        auto* btnRow = new QHBoxLayout;
        auto* saveBtn = new QPushButton("SAVE API KEY");
        saveBtn->setStyleSheet(buttonStyle());
        connect(saveBtn, &QPushButton::clicked, this, &SettingsPage::saveApiKey);
        btnRow->addWidget(saveBtn);
        btnRow->addStretch();

        m_apiSavedLbl = new QLabel("Saved");
        m_apiSavedLbl->setStyleSheet(
            "color: #00ff9d; font-family: 'JetBrains Mono'; font-size: 11px;"
        );
        m_apiSavedLbl->setVisible(false);
        btnRow->addWidget(m_apiSavedLbl);
        cardLay->addLayout(btnRow);

        lay->addWidget(card);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Section 2: Ollama Endpoint
    // ─────────────────────────────────────────────────────────────────────────
    {
        auto* card = new QWidget;
        card->setStyleSheet(
            "QWidget { background: #111827; border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 10px; }"
        );
        auto* cardLay = new QVBoxLayout(card);
        cardLay->setContentsMargins(20, 16, 20, 16);
        cardLay->setSpacing(12);

        auto* heading = new QLabel;
        heading->setText(
            "<span style='font-weight:800;color:#94a3b8;font-size:11px;"
            "letter-spacing:2px;'>OLLAMA ENDPOINT</span>"
        );
        heading->setTextFormat(Qt::RichText);
        cardLay->addWidget(heading);

        auto* hint = new QLabel("Used by the local AI assistant");
        hint->setStyleSheet(
            "color: #475569; font-family: 'JetBrains Mono'; font-size: 11px;"
        );
        cardLay->addWidget(hint);

        m_ollamaEdit = new QLineEdit;
        m_ollamaEdit->setPlaceholderText("http://localhost:11434");
        m_ollamaEdit->setStyleSheet(inputStyle());
        cardLay->addWidget(m_ollamaEdit);

        auto* btnRow = new QHBoxLayout;
        auto* saveBtn = new QPushButton("SAVE ENDPOINT");
        saveBtn->setStyleSheet(buttonStyle());
        connect(saveBtn, &QPushButton::clicked, this, &SettingsPage::saveOllamaEndpoint);
        btnRow->addWidget(saveBtn);
        btnRow->addStretch();

        m_ollamaSavedLbl = new QLabel("Saved");
        m_ollamaSavedLbl->setStyleSheet(
            "color: #00ff9d; font-family: 'JetBrains Mono'; font-size: 11px;"
        );
        m_ollamaSavedLbl->setVisible(false);
        btnRow->addWidget(m_ollamaSavedLbl);
        cardLay->addLayout(btnRow);

        lay->addWidget(card);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Section 3: Notification Preferences
    // ─────────────────────────────────────────────────────────────────────────
    {
        auto* card = new QWidget;
        card->setStyleSheet(
            "QWidget { background: #111827; border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 10px; }"
        );
        auto* cardLay = new QVBoxLayout(card);
        cardLay->setContentsMargins(20, 16, 20, 16);
        cardLay->setSpacing(12);

        auto* heading = new QLabel;
        heading->setText(
            "<span style='font-weight:800;color:#94a3b8;font-size:11px;"
            "letter-spacing:2px;'>NOTIFICATION PREFERENCES</span>"
        );
        heading->setTextFormat(Qt::RichText);
        cardLay->addWidget(heading);

        m_desktopNotifChk = new QCheckBox("Desktop notifications (system tray)");
        m_desktopNotifChk->setStyleSheet(checkStyle());
        cardLay->addWidget(m_desktopNotifChk);

        m_soundAlertChk = new QCheckBox("Sound alerts for critical incidents");
        m_soundAlertChk->setStyleSheet(checkStyle());
        cardLay->addWidget(m_soundAlertChk);

        auto* btnRow = new QHBoxLayout;
        auto* saveBtn = new QPushButton("SAVE PREFERENCES");
        saveBtn->setStyleSheet(buttonStyle());
        connect(saveBtn, &QPushButton::clicked, this, &SettingsPage::saveNotifications);
        btnRow->addWidget(saveBtn);
        btnRow->addStretch();

        m_notifSavedLbl = new QLabel("Saved");
        m_notifSavedLbl->setStyleSheet(
            "color: #00ff9d; font-family: 'JetBrains Mono'; font-size: 11px;"
        );
        m_notifSavedLbl->setVisible(false);
        btnRow->addWidget(m_notifSavedLbl);
        cardLay->addLayout(btnRow);

        lay->addWidget(card);
    }

    lay->addStretch();
    scroll->setWidget(content);
    outerLay->addWidget(scroll);
}

// ── Settings persistence ──────────────────────────────────────────────────────

void SettingsPage::loadSettings() {
    QSettings cfg(configPath(), QSettings::IniFormat);
    m_apiKeyEdit->setText(cfg.value("auth/api_key").toString());
    m_ollamaEdit->setText(
        cfg.value("ollama/endpoint", "http://localhost:11434").toString()
    );
    m_desktopNotifChk->setChecked(cfg.value("notifications/desktop", true).toBool());
    m_soundAlertChk->setChecked(cfg.value("notifications/sound", false).toBool());
}

void SettingsPage::saveApiKey() {
    QSettings cfg(configPath(), QSettings::IniFormat);
    cfg.setValue("auth/api_key", m_apiKeyEdit->text().trimmed());
    cfg.sync();
    showSavedFeedback(m_apiSavedLbl);
}

void SettingsPage::toggleApiKeyVisibility(bool checked) {
    m_apiKeyEdit->setEchoMode(checked ? QLineEdit::Normal : QLineEdit::Password);
    m_showHideBtn->setText(checked ? "HIDE" : "SHOW");
}

void SettingsPage::saveOllamaEndpoint() {
    QSettings cfg(configPath(), QSettings::IniFormat);
    QString endpoint = m_ollamaEdit->text().trimmed();
    if (endpoint.isEmpty()) endpoint = QStringLiteral("http://localhost:11434");
    cfg.setValue("ollama/endpoint", endpoint);
    cfg.sync();
    showSavedFeedback(m_ollamaSavedLbl);
}

void SettingsPage::saveNotifications() {
    QSettings cfg(configPath(), QSettings::IniFormat);
    cfg.setValue("notifications/desktop", m_desktopNotifChk->isChecked());
    cfg.setValue("notifications/sound",   m_soundAlertChk->isChecked());
    cfg.sync();
    showSavedFeedback(m_notifSavedLbl);
}

void SettingsPage::showSavedFeedback(QLabel* label) {
    label->setVisible(true);
    QTimer::singleShot(2000, label, [label]() {
        label->setVisible(false);
    });
}
