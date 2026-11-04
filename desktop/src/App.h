#pragma once
#include <QObject>
#include <QString>
#include <QTimer>
#include <QDeadlineTimer>

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
    // Browser (device-code) sign-in state.
    Q_PROPERTY(bool    deviceAuthActive READ deviceAuthActive NOTIFY deviceAuthChanged)
    Q_PROPERTY(QString deviceUserCode   READ deviceUserCode   NOTIFY deviceAuthChanged)
    Q_PROPERTY(QString deviceVerifyUrl  READ deviceVerifyUrl  NOTIFY deviceAuthChanged)

public:
    explicit App(Config*, ApiClient*, NetworkScanner*, OllamaClient*, PrivacyMode*, QObject* parent = nullptr);

    bool    authenticated() const { return m_authenticated; }
    bool    authBusy()      const { return m_authBusy; }
    bool    offline()       const { return m_offline; }
    QString version() const { return "1.0.0"; }
    bool    deviceAuthActive() const { return m_deviceAuthActive; }
    QString deviceUserCode()   const { return m_deviceUserCode; }
    QString deviceVerifyUrl()  const { return m_deviceVerifyUrl; }

public slots:
    void login(const QString& apiKey, const QString& apiBase = {});
    void logout();
    void startDeviceLogin(const QString& apiBase = {});
    void cancelDeviceLogin();
    void openDeviceVerifyPage();

signals:
    void authChanged();
    void authBusyChanged();
    void deviceAuthChanged();
    void notification(const QString& title, const QString& message, const QString& level);

private:
    bool isPending(const QString& key) const { return m_authBusy && !key.isEmpty() && key == m_candidateKey; }
    void setAuthBusy(bool b) { if (b == m_authBusy) return; m_authBusy = b; emit authBusyChanged(); }
    void setAuthenticated(bool authed, bool offline);
    void stopDeviceLogin(const QString& errorMessage = {});

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

    // The device code is the secret half of the pair; it stays in memory only.
    QString         m_deviceCode;
    QString         m_deviceUserCode;
    QString         m_deviceVerifyUrl;
    bool            m_deviceAuthActive = false;
    QTimer          m_devicePoll;
    QDeadlineTimer  m_deviceDeadline;
};
