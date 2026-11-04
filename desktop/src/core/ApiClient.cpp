#include "ApiClient.h"
#include "Config.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QUrl>

static QString enc(const QString& s) { return QString::fromUtf8(QUrl::toPercentEncoding(s)); }

ApiClient::ApiClient(Config* config, QObject* parent)
    : QObject(parent), m_config(config)
{
    m_apiKey = config->apiKey();
    connect(config, &Config::changed, this, [this]() {
        m_apiKey = m_config->apiKey();
    });
}

void ApiClient::setApiKey(const QString& key) { m_apiKey = key; }

QNetworkRequest ApiClient::jsonRequest(const QString& path) const
{
    QNetworkRequest req(QUrl(m_config->apiBase() + path));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setTransferTimeout(20000);
    return req;
}

void ApiClient::request(const QString& method, const QString& path,
                        const QJsonObject& body, Handler onSuccess)
{
    QNetworkRequest req = jsonRequest(path);
    req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    QNetworkReply* reply = method == "POST"
        ? m_nam.post(req, QJsonDocument(body).toJson(QJsonDocument::Compact))
        : m_nam.get(req);

    connect(reply, &QNetworkReply::finished, this, [this, reply, path, onSuccess]() {
        reply->deleteLater();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        if (reply->error() != QNetworkReply::NoError) {
            if (status == 401)
                emit authError();
            else
                emit networkError(path, status ? QString("HTTP %1").arg(status) : reply->errorString());
            return;
        }
        onSuccess(QJsonDocument::fromJson(reply->readAll()));
    });
}

void ApiClient::verifyKey(const QString& key)
{
    QNetworkRequest req(QUrl(m_config->apiBase() + "/v1/me"));
    req.setRawHeader("Authorization", ("Bearer " + key).toUtf8());
    req.setTransferTimeout(15000);

    QNetworkReply* reply = m_nam.get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, key]() {
        reply->deleteLater();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QJsonObject body = QJsonDocument::fromJson(reply->readAll()).object();

        if (status == 200) {
            emit keyVerified(key, body);
        } else if (status == 401 || status == 403) {
            emit keyRejected(key, body["error"].toString("unauthorized"));
        } else if (status != 0) {
            emit keyCheckFailed(key, QString("API at %1 answered HTTP %2").arg(m_config->apiBase()).arg(status),
                                status >= 500);
        } else {
            emit keyCheckFailed(key, reply->errorString(), true);
        }
    });
}

void ApiClient::startDeviceAuth(const QString& clientLabel)
{
    QNetworkReply* reply = m_nam.post(jsonRequest("/v1/auth/device"),
        QJsonDocument(QJsonObject{{"client_label", clientLabel}}).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QJsonObject body = QJsonDocument::fromJson(reply->readAll()).object();
        if (status == 200 && !body["device_code"].toString().isEmpty() && !body["user_code"].toString().isEmpty())
            emit deviceAuthStarted(body);
        else
            emit deviceAuthStartFailed(status ? QString("API at %1 answered HTTP %2").arg(m_config->apiBase()).arg(status)
                                              : reply->errorString());
    });
}

void ApiClient::pollDeviceAuth(const QString& deviceCode)
{
    QNetworkReply* reply = m_nam.post(jsonRequest("/v1/auth/device/poll"),
        QJsonDocument(QJsonObject{{"device_code", deviceCode}}).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply, deviceCode]() {
        reply->deleteLater();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        emit deviceAuthPolled(deviceCode, status, QJsonDocument::fromJson(reply->readAll()).object());
    });
}

void ApiClient::getMe()
{
    request("GET", "/v1/me", {}, [this](const QJsonDocument& d) { emit meResult(d.object()); });
}

void ApiClient::getIncidents(bool openOnly)
{
    request("GET", openOnly ? "/v1/incidents?open=1" : "/v1/incidents", {},
            [this, openOnly](const QJsonDocument& d) {
        emit incidentsResult(d.object()["incidents"].toArray(), openOnly);
    });
}

void ApiClient::ackIncident(const QString& incidentId)
{
    request("POST", "/v1/incidents/ack?incident_id=" + enc(incidentId), {},
            [this, incidentId](const QJsonDocument&) { emit incidentAcked(incidentId); });
}

void ApiClient::postScanResult(const QJsonObject& scan)
{
    request("POST", "/v1/scans", scan, [this](const QJsonDocument& d) {
        emit scanUploaded(d.object()["new_device_incidents"].toInt());
    });
}

void ApiClient::getThreats(int days, int limit)
{
    request("GET", QString("/v1/threats?days=%1&limit=%2").arg(days).arg(limit), {},
            [this](const QJsonDocument& d) { emit threatsResult(d.object()["cves"].toArray()); });
}

void ApiClient::lookupCve(const QString& query)
{
    request("GET", "/v1/shadow/cve?limit=5&q=" + enc(query), {},
            [this](const QJsonDocument& d) { emit cveResult(d.object()); });
}

void ApiClient::checkBreach(const QString& email)
{
    request("GET", "/v1/shadow/breach?email=" + enc(email), {},
            [this](const QJsonDocument& d) { emit breachResult(d.object()); });
}

void ApiClient::checkIpReputation(const QString& ip)
{
    request("GET", "/v1/shadow/ip?addr=" + enc(ip), {},
            [this](const QJsonDocument& d) { emit ipReputationResult(d.object()); });
}
