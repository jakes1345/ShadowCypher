#pragma once
#include <QObject>
#include <QString>
#include <QJsonObject>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkAccessManager>
#include <functional>

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
    // Device authorization (RFC 8628 style); unauthenticated.
    void startDeviceAuth(const QString& clientLabel);
    void pollDeviceAuth(const QString& deviceCode);

    // Guardian: scans + incidents
    Q_INVOKABLE void postScanResult(const QJsonObject& scan);
    Q_INVOKABLE void getIncidents(bool openOnly = false);
    Q_INVOKABLE void ackIncident(const QString& incidentId);

    // Threat intel
    Q_INVOKABLE void getThreats(int days = 7, int limit = 10);
    Q_INVOKABLE void lookupCve(const QString& query);
    Q_INVOKABLE void checkBreach(const QString& email);
    Q_INVOKABLE void checkIpReputation(const QString& ip);

signals:
    void meResult(const QJsonObject& user);
    void incidentsResult(const QJsonArray& incidents, bool openOnly);
    void incidentAcked(const QString& incidentId);
    void threatsResult(const QJsonArray& cves);
    void scanUploaded(int newDeviceIncidents);
    void cveResult(const QJsonObject& result);
    void breachResult(const QJsonObject& result);
    void ipReputationResult(const QJsonObject& result);
    void authError();
    // path identifies which call failed, so listeners can ignore ones they didn't make.
    void networkError(const QString& path, const QString& message);

    // Each carries the key that was checked, so callers can drop stale replies.
    void keyVerified(const QString& key, const QJsonObject& user);
    void keyRejected(const QString& key, const QString& reason);
    // transient: unreachable or 5xx (worth retrying later), as opposed to a wrong URL.
    void keyCheckFailed(const QString& key, const QString& message, bool transient);

    void deviceAuthStarted(const QJsonObject& info);
    // httpStatus 0 = no response; body carries "status" (pending/authorized/expired/denied/consumed).
    void deviceAuthPolled(const QString& deviceCode, int httpStatus, const QJsonObject& body);
    void deviceAuthStartFailed(const QString& message);

private:
    using Handler = std::function<void(const QJsonDocument&)>;
    void request(const QString& method, const QString& path,
                 const QJsonObject& body, Handler onSuccess);
    QNetworkRequest jsonRequest(const QString& path) const;

    Config*                m_config;
    QNetworkAccessManager  m_nam;
    QString                m_apiKey;
};
