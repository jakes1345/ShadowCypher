#pragma once
#include <QObject>
#include <QString>

class Config;
class ApiClient;
class NetworkScanner;
class OllamaClient;
class PrivacyMode;

class App : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool authenticated READ authenticated NOTIFY authChanged)
    Q_PROPERTY(bool authBusy      READ authBusy      NOTIFY authBusyChanged)
    Q_PROPERTY(bool offline       READ offline       NOTIFY authChanged)
    Q_PROPERTY(QString version READ version CONSTANT)

public:
    explicit App(Config*, ApiClient*, NetworkScanner*, OllamaClient*, PrivacyMode*, QObject* parent = nullptr);

    bool    authenticated() const { return m_authenticated; }
    bool    authBusy()      const { return m_authBusy; }
    bool    offline()       const { return m_offline; }
    QString version() const { return "1.0.0"; }

public slots:
    void login(const QString& apiKey, const QString& apiBase = {});
    void logout();

signals:
    void authChanged();
    void authBusyChanged();
    void notification(const QString& title, const QString& message, const QString& level);

private:
    bool isPending(const QString& key) const { return m_authBusy && !key.isEmpty() && key == m_candidateKey; }
    void setAuthBusy(bool b) { if (b == m_authBusy) return; m_authBusy = b; emit authBusyChanged(); }
    void setAuthenticated(bool authed, bool offline);

    Config*         m_config;
    ApiClient*      m_api;
    NetworkScanner* m_scanner;
    OllamaClient*   m_ai;
    PrivacyMode*    m_privacy;
    QString         m_candidateKey;
    bool            m_checkingStoredKey = false;
    bool            m_authenticated = false;
    bool            m_authBusy      = false;
    bool            m_offline       = false;
};
