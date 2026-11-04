#include "App.h"
#include "core/Config.h"
#include "core/ApiClient.h"
#include "scanner/NetworkScanner.h"
#include "ai/OllamaClient.h"
#include "privacy/PrivacyMode.h"
#include <QJsonObject>
#include <QRegularExpression>
#include <QDesktopServices>
#include <QUrl>

App::App(Config* config, ApiClient* api, NetworkScanner* scanner,
         OllamaClient* ai, PrivacyMode* privacy, QObject* parent)
    : QObject(parent)
    , m_config(config)
    , m_api(api)
    , m_scanner(scanner)
    , m_ai(ai)
    , m_privacy(privacy)
{
    m_scanner->setIntervalSeconds(m_config->scanInterval());
    connect(m_config, &Config::changed, this, [this]() {
        m_scanner->setIntervalSeconds(m_config->scanInterval());
    });

    connect(m_scanner, &NetworkScanner::arpSpoofDetected, this,
            [this](const QString& ip, const QString& knownMac, const QString& currentMac) {
        emit notification("ARP spoof suspected",
            QString("%1 changed from %2 to %3").arg(ip, knownMac, currentMac), "error");
    });

    connect(m_api, &ApiClient::keyVerified, this, [this](const QString& key, const QJsonObject&) {
        if (!isPending(key)) return;
        if (m_candidateKey != m_config->apiKey())
            m_config->setApiKey(m_candidateKey);
        m_api->setApiKey(m_candidateKey);
        m_checkingStoredKey = false;
        m_candidateKey.clear();
        setAuthBusy(false);
        setAuthenticated(true, false);
    });

    connect(m_api, &ApiClient::keyRejected, this, [this](const QString& key, const QString&) {
        if (!isPending(key)) return;
        const bool stored = m_checkingStoredKey;
        m_checkingStoredKey = false;
        m_candidateKey.clear();
        setAuthBusy(false);
        setAuthenticated(false, false);
        emit notification("Sign in",
            stored ? "Your saved API key was rejected by the server. Sign in again."
                   : "The server doesn't recognise that API key.",
            "error");
    });

    connect(m_api, &ApiClient::keyCheckFailed, this, [this](const QString& key, const QString& msg, bool transient) {
        if (!isPending(key)) return;
        const bool stored = m_checkingStoredKey;
        m_checkingStoredKey = false;
        m_candidateKey.clear();
        setAuthBusy(false);
        if (stored && transient) {
            // Local tools don't need the API, so a saved key gets offline access.
            setAuthenticated(true, true);
            emit notification("Offline", "Couldn't reach the API (" + msg + "). Local tools still work.", "warn");
        } else {
            setAuthenticated(false, false);
            emit notification("Sign in", msg + ". Check the API server address.", "error");
        }
    });

    connect(m_api, &ApiClient::authError, this, [this]() {
        setAuthenticated(false, false);
        emit notification("Auth", "API key invalid — please log in again.", "error");
    });

    m_devicePoll.setSingleShot(true);
    connect(&m_devicePoll, &QTimer::timeout, this, [this]() {
        if (!m_deviceAuthActive || m_deviceCode.isEmpty()) return;
        if (m_deviceDeadline.hasExpired()) {
            stopDeviceLogin("The sign-in code expired. Start again.");
            return;
        }
        m_api->pollDeviceAuth(m_deviceCode);
    });

    connect(m_api, &ApiClient::deviceAuthStarted, this, [this](const QJsonObject& info) {
        if (!m_deviceAuthActive || !m_deviceCode.isEmpty()) return;
        m_deviceCode      = info["device_code"].toString();
        m_deviceUserCode  = info["user_code"].toString();
        m_deviceVerifyUrl = info["verification_uri_complete"].toString(info["verification_uri"].toString());
        m_deviceDeadline.setRemainingTime(qint64(qMax(60, info["expires_in"].toInt(600))) * 1000);
        m_devicePoll.setInterval(qMax(2, info["interval"].toInt(5)) * 1000);
        m_devicePoll.start();
        emit deviceAuthChanged();
    });

    connect(m_api, &ApiClient::deviceAuthStartFailed, this, [this](const QString& msg) {
        if (m_deviceAuthActive && m_deviceCode.isEmpty())
            stopDeviceLogin("Couldn't start browser sign-in: " + msg);
    });

    connect(m_api, &ApiClient::deviceAuthPolled, this,
            [this](const QString& code, int http, const QJsonObject& body) {
        if (!m_deviceAuthActive || code != m_deviceCode) return;   // cancelled or stale
        const QString status = body["status"].toString();

        if (http == 200 && status == "authorized") {
            const QString key = body["api_key"].toString();
            stopDeviceLogin();
            if (key.isEmpty()) {
                emit notification("Sign in", "The server authorized sign-in but sent no API key.", "error");
                return;
            }
            // Same verified path as a pasted key: format check, then /v1/me.
            login(key);
            return;
        }
        if (http == 200 && status == "pending") { m_devicePoll.start(); return; }
        if (status == "denied")                 { stopDeviceLogin("Sign-in was denied in the browser."); return; }
        if (http == 410 || status == "expired" || status == "consumed") {
            stopDeviceLogin("The sign-in code expired. Start again.");
            return;
        }
        // No response or a server error: keep trying until the code expires.
        if (http == 0 || http >= 500) { m_devicePoll.start(); return; }
        stopDeviceLogin(QString("Browser sign-in failed (HTTP %1).").arg(http));
    });

    if (!m_config->apiKey().isEmpty()) {
        m_checkingStoredKey = true;
        m_candidateKey = m_config->apiKey();
        setAuthBusy(true);
        m_api->verifyKey(m_candidateKey);
    }
}

void App::setAuthenticated(bool authed, bool offline)
{
    const bool changed = authed != m_authenticated || offline != m_offline;
    m_authenticated = authed;
    m_offline = offline;
    if (authed && !m_scanner->running()) m_scanner->start();
    if (!authed && m_scanner->running()) m_scanner->stop();
    if (changed) emit authChanged();
}

void App::login(const QString& apiKey, const QString& apiBase)
{
    if (m_authBusy) return;
    const QString key = apiKey.trimmed();
    static const QRegularExpression pattern("^sc_live_[a-f0-9]{48}$");
    if (!pattern.match(key).hasMatch()) {
        emit notification("Sign in", "Invalid key format. Expected sc_live_ + 48 hex chars.", "error");
        return;
    }
    if (!apiBase.trimmed().isEmpty() && apiBase.trimmed() != m_config->apiBase())
        m_config->setApiBase(apiBase);

    m_candidateKey = key;
    setAuthBusy(true);
    m_api->verifyKey(key);
}

void App::startDeviceLogin(const QString& apiBase)
{
    if (m_authBusy || m_deviceAuthActive) return;
    if (!apiBase.trimmed().isEmpty() && apiBase.trimmed() != m_config->apiBase())
        m_config->setApiBase(apiBase);
    m_deviceAuthActive = true;
    emit deviceAuthChanged();
    m_api->startDeviceAuth("ShadowCypher Desktop");
}

void App::cancelDeviceLogin() { stopDeviceLogin(); }

void App::stopDeviceLogin(const QString& errorMessage)
{
    m_devicePoll.stop();
    const bool wasActive = m_deviceAuthActive;
    m_deviceCode.clear();
    m_deviceUserCode.clear();
    m_deviceVerifyUrl.clear();
    m_deviceAuthActive = false;
    if (wasActive) emit deviceAuthChanged();
    if (!errorMessage.isEmpty()) emit notification("Sign in", errorMessage, "error");
}

void App::openDeviceVerifyPage()
{
    // The URL comes from the API server; only hand web URLs to the desktop.
    const QUrl url(m_deviceVerifyUrl);
    const bool loopback = url.host() == "127.0.0.1" || url.host() == "localhost";
    if (url.isValid() && (url.scheme() == "https" || (url.scheme() == "http" && loopback)))
        QDesktopServices::openUrl(url);
}

void App::logout()
{
    stopDeviceLogin();
    // Drop any in-flight check so a late reply can't sign the user back in.
    m_candidateKey.clear();
    m_checkingStoredKey = false;
    setAuthBusy(false);
    m_config->setApiKey({});
    m_api->setApiKey({});
    setAuthenticated(false, false);
}
