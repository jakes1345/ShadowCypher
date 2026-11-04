#include "App.h"
#include "core/Config.h"
#include "core/ApiClient.h"
#include "scanner/NetworkScanner.h"
#include "ai/OllamaClient.h"
#include "privacy/PrivacyMode.h"
#include <QJsonObject>
#include <QRegularExpression>

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

void App::logout()
{
    // Drop any in-flight check so a late reply can't sign the user back in.
    m_candidateKey.clear();
    m_checkingStoredKey = false;
    setAuthBusy(false);
    m_config->setApiKey({});
    m_api->setApiKey({});
    setAuthenticated(false, false);
}
