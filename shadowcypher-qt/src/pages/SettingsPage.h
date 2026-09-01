#pragma once
#include <QWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QCheckBox>

// Local-only settings page — reads/writes ~/.config/shadowcypher/config.ini
// via QSettings. No IPC client needed.
class SettingsPage : public QWidget {
    Q_OBJECT
public:
    explicit SettingsPage(QWidget* parent = nullptr);

private slots:
    void saveApiKey();
    void toggleApiKeyVisibility(bool checked);
    void saveOllamaEndpoint();
    void saveNotifications();

private:
    // Section 1 — API Key
    QLineEdit*   m_apiKeyEdit    = nullptr;
    QPushButton* m_showHideBtn   = nullptr;
    QLabel*      m_apiSavedLbl   = nullptr;

    // Section 2 — Ollama Endpoint
    QLineEdit*   m_ollamaEdit    = nullptr;
    QLabel*      m_ollamaSavedLbl = nullptr;

    // Section 3 — Notifications
    QCheckBox*   m_desktopNotifChk = nullptr;
    QCheckBox*   m_soundAlertChk   = nullptr;
    QLabel*      m_notifSavedLbl   = nullptr;

    void buildUi();
    void loadSettings();
    void showSavedFeedback(QLabel* label);

    static QString buttonStyle();
    static QString inputStyle();
    static QString checkStyle();
};
