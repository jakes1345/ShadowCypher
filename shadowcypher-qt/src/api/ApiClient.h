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
    void del(const QString& path, QObject* ctx, ApiCallback cb);

    // Login: posts /v1/auth/login, stores key on success
    void login(const QString& handle, const QString& password,
               QObject* ctx,
               std::function<void(bool ok, QString errorMsg)> cb);

    static QString configIniPath();
    static ApiClient* instance();
    static void setInstance(ApiClient* a);

private:
    static ApiClient* s_instance;
    QNetworkAccessManager* m_nam;
    QString m_apiKey;

    static constexpr auto API_BASE = "https://api.shadowcypher.site";

    QNetworkRequest makeRequest(const QString& path) const;
    void dispatchReply(QNetworkReply* reply, QObject* ctx, ApiCallback cb);
};
