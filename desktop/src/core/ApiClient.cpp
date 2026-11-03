#include "ApiClient.h"
#include "Config.h"
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonArray>
#include <QUrl>

ApiClient::ApiClient(Config* config, QObject* parent)
    : QObject(parent), m_config(config)
{
    m_apiKey = config->apiKey();
    connect(config, &Config::changed, this, [this]() {
        m_apiKey = m_config->apiKey();
    });
}

void ApiClient::setApiKey(const QString& key) { m_apiKey = key; }

void ApiClient::request(const QString& method, const QString& path, const QJsonObject& body)
{
    QNetworkRequest req(QUrl(m_config->apiBase() + path));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    QNetworkReply* reply = nullptr;
    if (method == "GET") {
        reply = m_nam.get(req);
    } else if (method == "POST") {
        reply = m_nam.post(req, QJsonDocument(body).toJson());
    }
    if (!reply) return;

    connect(reply, &QNetworkReply::finished, this, [this, reply, path]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            if (reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 401)
                emit authError();
            else
                emit networkError(reply->errorString());
            return;
        }
        const QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
        if (path == "/v1/me")              emit meResult(doc.object());
        else if (path.startsWith("/v1/cve"))   emit cveResult(doc.object());
        else if (path.startsWith("/v1/breach")) emit breachResult(doc.object());
        else if (path.startsWith("/v1/ip"))     emit ipReputationResult(doc.object());
        else if (path.startsWith("/v1/incident")) emit incidentsResult(doc.array());
    });
}

void ApiClient::getMe()                               { request("GET",  "/v1/me"); }
void ApiClient::getIncidents(int limit)               { request("GET",  QString("/v1/incidents?limit=%1").arg(limit)); }
void ApiClient::lookupCve(const QString& id)          { request("GET",  "/v1/cve/" + id); }
void ApiClient::checkBreach(const QString& email)     { request("GET",  "/v1/breach?email=" + email); }
void ApiClient::checkIpReputation(const QString& ip)  { request("GET",  "/v1/ip-rep?ip=" + ip); }
void ApiClient::postScanResult(const QJsonObject& scan) { request("POST", "/v1/scan", scan); }
