#include "CloudData.h"
#include "ApiClient.h"
#include "Config.h"
#include "scanner/NetworkScanner.h"
#include <QDateTime>
#include <QJsonObject>

static constexpr int kRefreshMs       = 5 * 60 * 1000;
// The threat feed is NVD data cached server-side for an hour; refresh it hourly.
static constexpr int kThreatEveryTick = 12;

CloudData::CloudData(ApiClient* api, Config* config, NetworkScanner* scanner, QObject* parent)
    : QObject(parent), m_api(api), m_config(config), m_scanner(scanner)
{
    m_timer.setInterval(kRefreshMs);
    connect(&m_timer, &QTimer::timeout, this, [this]() {
        if (!m_active) return;
        m_api->getIncidents(true);
        if (++m_ticks % kThreatEveryTick == 0) m_api->getThreats();
    });

    connect(m_api, &ApiClient::incidentsResult, this, [this](const QJsonArray& items, bool openOnly) {
        if (!m_active || !openOnly) return;
        m_incidents = items;
        m_incidentsLoaded = true;
        setIncidentsError({});
        emit incidentsChanged();
    });

    connect(m_api, &ApiClient::incidentAcked, this, [this](const QString& id) {
        for (qsizetype i = 0; i < m_incidents.size(); ++i) {
            if (m_incidents[i].toObject()["id"].toString() == id) {
                m_incidents.removeAt(i);
                emit incidentsChanged();
                break;
            }
        }
    });

    connect(m_api, &ApiClient::threatsResult, this, [this](const QJsonArray& cves) {
        if (!m_active) return;
        m_threats = cves;
        m_threatsLoaded = true;
        setThreatsError({});
        emit threatsChanged();
    });

    connect(m_api, &ApiClient::scanUploaded, this, [this](int newDevices) {
        const QString when = QDateTime::currentDateTime().toString("hh:mm");
        setSyncStatus(newDevices > 0
            ? QString("Synced at %1 · %2 new device%3").arg(when).arg(newDevices).arg(newDevices == 1 ? "" : "s")
            : QString("Synced at %1").arg(when));
        if (newDevices > 0) m_api->getIncidents(true);
    });

    connect(m_api, &ApiClient::networkError, this, [this](const QString& path, const QString& msg) {
        if (!m_active) return;
        if (path.startsWith("/v1/scans"))
            setSyncStatus("Sync failed: " + msg);
        else if (path.startsWith("/v1/incidents"))
            setIncidentsError("Couldn't load incidents (" + msg + ")");
        else if (path.startsWith("/v1/threats"))
            setThreatsError("Threat feed unavailable (" + msg + ")");
    });

    connect(m_scanner, &NetworkScanner::scanComplete, this, [this]() {
        if (m_active && m_config->syncScans()) uploadScan();
    });
}

void CloudData::setActive(bool active)
{
    if (active == m_active) return;
    m_active = active;
    if (active) {
        m_ticks = 0;
        m_timer.start();
        refresh();
    } else {
        // Don't keep account data around after sign-out or when going offline.
        m_timer.stop();
        m_incidents = {};
        m_threats = {};
        m_incidentsLoaded = m_threatsLoaded = false;
        m_incidentsError.clear();
        m_threatsError.clear();
        m_syncStatus.clear();
        emit incidentsChanged();
        emit threatsChanged();
        emit errorChanged();
        emit syncStatusChanged();
    }
    emit activeChanged();
}

void CloudData::refresh()
{
    if (!m_active) return;
    m_api->getIncidents(true);
    m_api->getThreats();
}

void CloudData::acknowledge(const QString& incidentId)
{
    if (m_active && !incidentId.isEmpty()) m_api->ackIncident(incidentId);
}

void CloudData::uploadScan()
{
    QJsonArray devices;
    for (const auto& v : m_scanner->devicesJson()) {
        const QJsonObject d = v.toObject();
        QJsonObject out{{"mac", d["mac"]}, {"ip", d["ip"]}};
        if (!d["hostname"].toString().isEmpty()) out["hostname"] = d["hostname"];
        devices.append(out);
    }
    m_api->postScanResult(QJsonObject{
        {"scan_type",   "arp"},
        {"duration_ms", m_scanner->lastScanDurationMs()},
        {"devices",     devices},
    });
}
