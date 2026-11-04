#pragma once
#include <QObject>
#include <QJsonArray>
#include <QTimer>

class ApiClient;
class Config;
class NetworkScanner;

// Account-side data shown on the dashboard (open incidents, CVE feed) and the
// opt-in scan upload. Only talks to the API while active (signed in and online).
class CloudData : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool       active    READ active    NOTIFY activeChanged)
    Q_PROPERTY(QJsonArray incidents READ incidents NOTIFY incidentsChanged)
    Q_PROPERTY(int        openCount READ openCount NOTIFY incidentsChanged)
    Q_PROPERTY(bool       incidentsLoaded READ incidentsLoaded NOTIFY incidentsChanged)
    Q_PROPERTY(QJsonArray threats   READ threats   NOTIFY threatsChanged)
    Q_PROPERTY(bool       threatsLoaded READ threatsLoaded NOTIFY threatsChanged)
    Q_PROPERTY(QString    incidentsError READ incidentsError NOTIFY errorChanged)
    Q_PROPERTY(QString    threatsError   READ threatsError   NOTIFY errorChanged)
    Q_PROPERTY(QString    syncStatus READ syncStatus NOTIFY syncStatusChanged)

public:
    CloudData(ApiClient* api, Config* config, NetworkScanner* scanner, QObject* parent = nullptr);

    bool       active()    const { return m_active; }
    QJsonArray incidents() const { return m_incidents; }
    int        openCount() const { return int(m_incidents.size()); }
    bool       incidentsLoaded() const { return m_incidentsLoaded; }
    QJsonArray threats()   const { return m_threats; }
    bool       threatsLoaded() const { return m_threatsLoaded; }
    QString    incidentsError() const { return m_incidentsError; }
    QString    threatsError()   const { return m_threatsError; }
    QString    syncStatus() const { return m_syncStatus; }

    void setActive(bool active);

public slots:
    void refresh();
    void acknowledge(const QString& incidentId);

signals:
    void activeChanged();
    void incidentsChanged();
    void threatsChanged();
    void errorChanged();
    void syncStatusChanged();

private:
    void setIncidentsError(const QString& e) { if (e == m_incidentsError) return; m_incidentsError = e; emit errorChanged(); }
    void setThreatsError(const QString& e)   { if (e == m_threatsError) return; m_threatsError = e; emit errorChanged(); }
    void setSyncStatus(const QString& s) { m_syncStatus = s; emit syncStatusChanged(); }
    void uploadScan();

    ApiClient*      m_api;
    Config*         m_config;
    NetworkScanner* m_scanner;
    QTimer          m_timer;
    int             m_ticks = 0;
    bool            m_active = false;
    bool            m_incidentsLoaded = false;
    bool            m_threatsLoaded = false;
    QJsonArray      m_incidents;
    QJsonArray      m_threats;
    QString         m_incidentsError;
    QString         m_threatsError;
    QString         m_syncStatus;
};
