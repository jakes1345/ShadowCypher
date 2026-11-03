#include "OllamaClient.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>

OllamaClient::OllamaClient(QObject* parent) : QObject(parent)
{
    checkAvailability();
}

void OllamaClient::checkAvailability()
{
    QNetworkRequest req(QUrl(m_baseUrl + "/api/tags"));
    auto* reply = m_nam.get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        const bool ok = (reply->error() == QNetworkReply::NoError);
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
    QJsonObject body;
    body["model"]  = m_model;
    body["prompt"] = prompt;
    body["stream"] = false;

    QNetworkRequest req(QUrl(m_baseUrl + "/api/generate"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    auto* reply = m_nam.post(req, QJsonDocument(body).toJson());

    setBusy(true);
    connect(reply, &QNetworkReply::finished, this, [this, reply, requestId]() {
        reply->deleteLater();
        setBusy(false);
        if (reply->error() != QNetworkReply::NoError) {
            emit error(reply->errorString());
            return;
        }
        const QString text = QJsonDocument::fromJson(reply->readAll())
                             .object()["response"].toString();
        emit queryResult(requestId, text);
    });
}
