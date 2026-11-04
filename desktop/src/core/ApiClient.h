#pragma once
#include <QObject>
#include <QString>
#include <QJsonObject>
#include <QNetworkAccessManager>

class Config;

class ApiClient : public QObject
{
    Q_OBJECT

public:
    explicit ApiClient(Config* config, QObject* parent = nullptr);

    void setApiKey(const QString&);

    // Auth
    Q_INVOKABLE void getMe();
    // Checks a candidate key against /v1/me without adopting it.
    void verifyKey(const QString& key);

    // Incidents
    Q_INVOKABLE void postScanResult(const QJsonObject& scan);
    Q_INVOKABLE void getIncidents(int limit = 50);

    // CVE
    Q_INVOKABLE void lookupCve(const QString& cveId);
    Q_INVOKABLE void checkBreach(const QString& email);

    // IP reputation
    Q_INVOKABLE void checkIpReputation(const QString& ip);

signals:
    void meResult(const QJsonObject& user);
    void incidentsResult(const QJsonArray& items);
    void cveResult(const QJsonObject& cve);
    void breachResult(const QJsonObject& result);
    void ipReputationResult(const QJsonObject& result);
    void authError();
    void networkError(const QString& message);

    // Each carries the key that was checked, so callers can drop stale replies.
    void keyVerified(const QString& key, const QJsonObject& user);
    void keyRejected(const QString& key, const QString& reason);
    // transient: unreachable or 5xx (worth retrying later), as opposed to a wrong URL.
    void keyCheckFailed(const QString& key, const QString& message, bool transient);

private:
    void request(const QString& method, const QString& path,
                 const QJsonObject& body = {});

    Config*                m_config;
    QNetworkAccessManager  m_nam;
    QString                m_apiKey;
};
