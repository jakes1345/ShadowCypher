#include "OllamaClient.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>

static const char* kSystemPrompt =
    "You are the ShadowCypher assistant, running locally on the user's own machine. "
    "Help them understand their network, devices, security alerts, CVEs and privacy settings. "
    "Be concise and practical.";

// Keeps the request body bounded on long conversations.
static constexpr int kMaxHistoryMessages = 20;

OllamaClient::OllamaClient(QObject* parent) : QObject(parent)
{
    m_recheck.setInterval(30'000);
    connect(&m_recheck, &QTimer::timeout, this, &OllamaClient::checkAvailability);
    m_recheck.start();
    checkAvailability();
}

void OllamaClient::checkAvailability()
{
    QNetworkRequest req(QUrl(m_baseUrl + "/api/tags"));
    req.setTransferTimeout(3000);
    auto* reply = m_nam.get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        bool ok = false;
        if (reply->error() == QNetworkReply::NoError) {
            const QJsonArray models = QJsonDocument::fromJson(reply->readAll()).object()["models"].toArray();
            // Embedding models can't chat; when the configured model isn't
            // installed, fall back to the largest chat-capable one.
            QString best;
            double bestSize = -1;
            bool configuredInstalled = false;
            for (const auto& v : models) {
                const QJsonObject m = v.toObject();
                const QString name = m["name"].toString();
                if (name.contains("embed", Qt::CaseInsensitive)) continue;
                if (name == m_model) configuredInstalled = true;
                const double size = m["size"].toDouble();
                if (size > bestSize) { bestSize = size; best = name; }
            }
            if (!configuredInstalled && !best.isEmpty()) {
                m_model = best;
                m_history = {};
                emit modelChanged();
            }
            ok = configuredInstalled || !best.isEmpty();
        }
        if (ok != m_available) {
            m_available = ok;
            emit availableChanged();
        }
    });
}

void OllamaClient::listModels()
{
    QNetworkRequest req(QUrl(m_baseUrl + "/api/tags"));
    auto* reply = m_nam.get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) { emit error(reply->errorString()); return; }
        const QJsonArray models = QJsonDocument::fromJson(reply->readAll()).object()["models"].toArray();
        QStringList names;
        for (const auto& m : models)
            names << m.toObject()["name"].toString();
        emit modelsListed(names);
    });
}

void OllamaClient::query(const QString& prompt, const QString& requestId)
{
    if (m_busy) return;

    const QJsonObject userMsg{{"role", "user"}, {"content", prompt}};
    QJsonArray messages{QJsonObject{{"role", "system"}, {"content", kSystemPrompt}}};
    const int start = qMax(0, int(m_history.size()) - kMaxHistoryMessages);
    for (int i = start; i < m_history.size(); ++i) messages.append(m_history[i]);
    messages.append(userMsg);

    QJsonObject body;
    body["model"]    = m_model;
    body["messages"] = messages;
    body["stream"]   = false;

    QNetworkRequest req(QUrl(m_baseUrl + "/api/chat"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    // Cold model loads on CPU can take a while.
    req.setTransferTimeout(180'000);
    auto* reply = m_nam.post(req, QJsonDocument(body).toJson());

    setBusy(true);
    connect(reply, &QNetworkReply::finished, this, [this, reply, requestId, userMsg]() {
        reply->deleteLater();
        setBusy(false);
        const QJsonObject obj = QJsonDocument::fromJson(reply->readAll()).object();
        if (reply->error() != QNetworkReply::NoError) {
            const QString detail = obj["error"].toString();
            emit error(detail.isEmpty() ? reply->errorString() : detail);
            checkAvailability();
            return;
        }
        const QString text = obj["message"].toObject()["content"].toString().trimmed();
        m_history.append(userMsg);
        m_history.append(QJsonObject{{"role", "assistant"}, {"content", text}});
        emit queryResult(requestId, text);
    });
}
