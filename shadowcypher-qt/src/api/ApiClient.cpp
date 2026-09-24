#include "ApiClient.h"
#include <QSettings>
#include <QDir>
#include <QPointer>
#include <QSslConfiguration>

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
}

void ApiClient::setApiKey(const QString& key) {
    m_apiKey = key;
    QSettings s(configIniPath(), QSettings::IniFormat);
    s.setValue("api_key", key);
    s.sync();
}

QNetworkRequest ApiClient::makeRequest(const QString& path) const {
    QUrl url(QString(API_BASE) + path);
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

void ApiClient::del(const QString& path, QObject* ctx, ApiCallback cb) {
    auto* reply = m_nam->deleteResource(makeRequest(path));
    dispatchReply(reply, ctx, std::move(cb));
}

void ApiClient::login(const QString& handle, const QString& password,
                      QObject* ctx,
                      std::function<void(bool ok, QString errorMsg)> cb) {
    QJsonObject body{{"handle", handle}, {"password", password}};
    post("/v1/auth/login", body, ctx,
         [this, cb = std::move(cb)](bool ok, QJsonDocument doc, int /*status*/) {
        if (ok) {
            QString key = doc.object().value("api_key").toString();
            if (key.isEmpty()) { cb(false, "No API key in response"); return; }
            setApiKey(key);
            cb(true, {});
        } else {
            QString msg = doc.object().value("error").toString("Login failed");
            cb(false, msg);
        }
    });
}
