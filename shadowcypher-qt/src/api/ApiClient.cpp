#include "ApiClient.h"
#include <QSettings>
#include <QDir>
#include <QPointer>
#include <QSslConfiguration>
#include <QUrl>

ApiClient* ApiClient::s_instance = nullptr;
ApiClient* ApiClient::instance() { return s_instance; }
void ApiClient::setInstance(ApiClient* a) { s_instance = a; }

QString ApiClient::configIniPath() {
    QString dir = QDir::homePath() + "/.config/shadowcypher";
    QDir().mkpath(dir);
    return dir + "/config.ini";
}

ApiClient::ApiClient(QObject* parent) : QObject(parent) {
    m_nam = new QNetworkAccessManager(this);
    QSettings s(configIniPath(), QSettings::IniFormat);
    m_apiKey = s.value("api_key").toString();

    // A self-hosted server may be set in config.ini. The key is sent to it, so only
    // HTTPS is accepted, except plain HTTP to this machine for local development.
    m_apiBase = DEFAULT_API_BASE;
    const QUrl custom(s.value("api_base").toString().trimmed());
    const bool local = custom.host() == "127.0.0.1" || custom.host() == "localhost";
    if (custom.isValid() && !custom.host().isEmpty()
        && (custom.scheme() == "https" || (custom.scheme() == "http" && local)))
        m_apiBase = custom.toString(QUrl::StripTrailingSlash);
}

void ApiClient::setApiKey(const QString& key) {
    m_apiKey = key;
    QSettings s(configIniPath(), QSettings::IniFormat);
    s.setValue("api_key", key);
    s.sync();
}

QNetworkRequest ApiClient::makeRequest(const QString& path) const {
    QUrl url(m_apiBase + path);
    QNetworkRequest req(url);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_apiKey.isEmpty())
        req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());
    req.setAttribute(QNetworkRequest::RedirectPolicyAttribute,
                     QNetworkRequest::NoLessSafeRedirectPolicy);
    return req;
}

void ApiClient::dispatchReply(QNetworkReply* reply, QObject* ctx, ApiCallback cb) {
    QPointer<QObject> guard(ctx);
    connect(reply, &QNetworkReply::finished, reply,
            [reply, guard, ctx, cb = std::move(cb)]() mutable {
        int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        QByteArray data = reply->readAll();
        bool httpOk = (reply->error() == QNetworkReply::NoError);
        reply->deleteLater();
        if (ctx != nullptr && guard.isNull()) return;
        QJsonDocument doc = QJsonDocument::fromJson(data);
        cb(httpOk && status >= 200 && status < 300, doc, status);
    });
}

void ApiClient::get(const QString& path, QObject* ctx, ApiCallback cb) {
    auto* reply = m_nam->get(makeRequest(path));
    dispatchReply(reply, ctx, std::move(cb));
}

void ApiClient::post(const QString& path, const QJsonObject& body,
                     QObject* ctx, ApiCallback cb) {
    auto* reply = m_nam->post(makeRequest(path),
                               QJsonDocument(body).toJson(QJsonDocument::Compact));
    dispatchReply(reply, ctx, std::move(cb));
}

void ApiClient::getBytes(const QString& path, QObject* ctx, BytesCallback cb) {
    auto* reply = m_nam->get(makeRequest(path));
    QPointer<QObject> guard(ctx);
    connect(reply, &QNetworkReply::finished, reply,
            [reply, guard, ctx, cb = std::move(cb)]() {
        int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        QByteArray data = reply->readAll();
        bool ok = reply->error() == QNetworkReply::NoError && status >= 200 && status < 300;
        reply->deleteLater();
        if (ctx != nullptr && guard.isNull()) return;
        cb(ok, data, status);
    });
}

void ApiClient::upload(const QString& path, const QByteArray& data, const QString& fileName,
                       const QString& mime, QObject* ctx, ApiCallback cb) {
    QNetworkRequest req = makeRequest(path);
    req.setHeader(QNetworkRequest::ContentTypeHeader, mime);
    QString safe = fileName;
    safe.replace('"', '_');
    req.setRawHeader("Content-Disposition", ("attachment; filename=\"" + safe + "\"").toUtf8());
    dispatchReply(m_nam->post(req, data), ctx, std::move(cb));
}

void ApiClient::patch(const QString& path, const QJsonObject& body,
                      QObject* ctx, ApiCallback cb) {
    auto* reply = m_nam->sendCustomRequest(makeRequest(path), "PATCH",
                                           QJsonDocument(body).toJson(QJsonDocument::Compact));
    dispatchReply(reply, ctx, std::move(cb));
}

void ApiClient::del(const QString& path, QObject* ctx, ApiCallback cb) {
    auto* reply = m_nam->deleteResource(makeRequest(path));
    dispatchReply(reply, ctx, std::move(cb));
}

void ApiClient::verifyKey(const QString& key, QObject* ctx,
                          std::function<void(bool ok, int status, QString handle)> cb) {
    QNetworkRequest req = makeRequest("/v1/me");
    req.setRawHeader("Authorization", ("Bearer " + key).toUtf8());
    dispatchReply(m_nam->get(req), ctx, [cb = std::move(cb)](bool ok, QJsonDocument doc, int status) {
        cb(ok, status, doc.object().value("handle").toString());
    });
}

void ApiClient::startDeviceAuth(const QString& clientLabel, QObject* ctx, ApiCallback cb) {
    QNetworkRequest req = makeRequest("/v1/auth/device");
    req.setRawHeader("Authorization", QByteArray());   // no key yet, and don't leak an old one
    dispatchReply(m_nam->post(req, QJsonDocument(QJsonObject{{"client_label", clientLabel}})
                                       .toJson(QJsonDocument::Compact)),
                  ctx, std::move(cb));
}

void ApiClient::pollDeviceAuth(const QString& deviceCode, QObject* ctx, ApiCallback cb) {
    QNetworkRequest req = makeRequest("/v1/auth/device/poll");
    req.setRawHeader("Authorization", QByteArray());
    dispatchReply(m_nam->post(req, QJsonDocument(QJsonObject{{"device_code", deviceCode}})
                                       .toJson(QJsonDocument::Compact)),
                  ctx, std::move(cb));
}
