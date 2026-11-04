#pragma once
#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QJsonObject>
#include <QJsonDocument>
#include <functional>

using ApiCallback = std::function<void(bool ok, QJsonDocument doc, int status)>;

class ApiClient : public QObject {
    Q_OBJECT
public:
    explicit ApiClient(QObject* parent = nullptr);

    void setApiKey(const QString& key);
    QString apiKey() const { return m_apiKey; }
    bool isAuthenticated() const { return !m_apiKey.isEmpty(); }

    // ctx: if non-null and destroyed before reply, callback is skipped
    void get(const QString& path, QObject* ctx, ApiCallback cb);
    void post(const QString& path, const QJsonObject& body, QObject* ctx, ApiCallback cb);
    void patch(const QString& path, const QJsonObject& body, QObject* ctx, ApiCallback cb);
    void del(const QString& path, QObject* ctx, ApiCallback cb);

    using BytesCallback = std::function<void(bool ok, QByteArray data, int status)>;
    void getBytes(const QString& path, QObject* ctx, BytesCallback cb);
    // Raw-body upload; the server reads the name from Content-Disposition.
    void upload(const QString& path, const QByteArray& data, const QString& fileName,
                const QString& mime, QObject* ctx, ApiCallback cb);

    // Calls GET /v1/me with `key` (not the stored one). ok=true means the key is valid.
    // status 0 means the server couldn't be reached.
    void verifyKey(const QString& key, QObject* ctx,
                   std::function<void(bool ok, int status, QString handle)> cb);

    // Browser sign-in (device authorization):
    //   startDeviceAuth → user approves at verification_uri → pollDeviceAuth until "authorized".
    void startDeviceAuth(const QString& clientLabel, QObject* ctx, ApiCallback cb);
    void pollDeviceAuth(const QString& deviceCode, QObject* ctx, ApiCallback cb);

    // API server, from `api_base` in config.ini (for self-hosting); defaults to production.
    QString apiBase() const { return m_apiBase; }

    static QString configIniPath();
    static ApiClient* instance();
    static void setInstance(ApiClient* a);

private:
    static ApiClient* s_instance;
    QNetworkAccessManager* m_nam;
    QString m_apiKey;
    QString m_apiBase;

    static constexpr auto DEFAULT_API_BASE = "https://api.shadowcypher.site";

    QNetworkRequest makeRequest(const QString& path) const;
    void dispatchReply(QNetworkReply* reply, QObject* ctx, ApiCallback cb);
};
