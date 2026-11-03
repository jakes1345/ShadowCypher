#include "App.h"
#include "core/Config.h"
#include "core/ApiClient.h"
#include "scanner/NetworkScanner.h"
#include "ai/OllamaClient.h"
#include "privacy/PrivacyMode.h"

App::App(Config* config, ApiClient* api, NetworkScanner* scanner,
         OllamaClient* ai, PrivacyMode* privacy, QObject* parent)
    : QObject(parent)
    , m_config(config)
    , m_api(api)
    , m_scanner(scanner)
    , m_ai(ai)
    , m_privacy(privacy)
{
    m_authenticated = !m_config->apiKey().isEmpty();

    connect(m_api, &ApiClient::authError, this, [this]() {
        m_authenticated = false;
        emit authChanged();
        emit notification("Auth", "API key invalid — please log in again.", "error");
    });
}

bool App::authenticated() const { return m_authenticated; }

void App::login(const QString& apiKey)
{
    m_config->setApiKey(apiKey);
    m_api->setApiKey(apiKey);
    m_authenticated = true;
    emit authChanged();
    m_scanner->start();
}

void App::logout()
{
    m_config->setApiKey({});
    m_api->setApiKey({});
    m_scanner->stop();
    m_authenticated = false;
    emit authChanged();
}
