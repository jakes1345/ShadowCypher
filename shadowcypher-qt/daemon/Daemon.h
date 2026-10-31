#pragma once
#include "../core/NativeTools.h"
#include <QObject>
#include <QJsonArray>
#include <QJsonObject>
#include <QMutex>
#include <QElapsedTimer>
#include <atomic>

#ifdef Q_OS_WIN
#  include <QTcpServer>
#  include <QTcpSocket>
using Server = QTcpServer;
using Socket = QTcpSocket;
#else
#  include <QLocalServer>
#  include <QLocalSocket>
using Server = QLocalServer;
using Socket = QLocalSocket;
#endif

// ── CounterIntel scan state ───────────────────────────────────────────────────
struct CiCheck {
    QString status;   // "ok" | "warning" | "alert" | "pending" | "error"
    QString detail;
};
struct CiState {
    QMap<QString, CiCheck> checks;
    QJsonArray findings;
    bool complete = false;
    int alertCount = 0;
    QString maxSeverity = "none";
};

// ── Daemon ────────────────────────────────────────────────────────────────────
class Daemon : public QObject {
    Q_OBJECT
public:
    explicit Daemon(QObject* parent = nullptr);
    bool start();

private slots:
    void onNewConnection();
    void onReadyRead();
    void onDisconnected();

private:
    // ── Dispatch ──────────────────────────────────────────────────────────────
    QJsonValue dispatch(const QString& method, const QJsonObject& params);

    // ── Handlers ──────────────────────────────────────────────────────────────
    QJsonValue handleGetTacticalSummary();
    QJsonValue handleGetDevices();
    QJsonValue handleGetIncidents();
    QJsonValue handleTriggerScan();
    QJsonValue handleAiChat(const QJsonObject& p);
    QJsonValue handleGetAiModel();
    QJsonValue handleCveFeedRecent(const QJsonObject& p);
    QJsonValue handleCveFeedSearch(const QJsonObject& p);
    QJsonValue handleCveFeedScan(const QJsonObject& p);
    QJsonValue handleCounterIntelScan();
    QJsonValue handleCounterIntelStatus();
    QJsonValue handleGhostStatus();
    QJsonValue handleGhostEnable();
    QJsonValue handleGhostDisable();

    // ── Counter-intel background helpers ─────────────────────────────────────
    void runCounterIntelAsync();
    CiCheck checkArpSpoofing();
    CiCheck checkPromiscuous();
    CiCheck checkDnsLeak();
    CiCheck checkTrafficAnomaly();
    CiCheck checkRogueDhcp();
    CiCheck checkSslInterception();
    CiCheck checkOsintSelf();

    // ── Incident helpers ─────────────────────────────────────────────────────
    void loadState();
    void saveState();
    void addIncident(const QString& deviceIp, const QString& type,
                     const QString& description, const QString& severity);
    void reconcileDevices(const QJsonArray& fresh);

    // ── Util ─────────────────────────────────────────────────────────────────
    void respond(QIODevice* sock, const QJsonValue& id, const QJsonValue& result);
    void respondError(QIODevice* sock, const QJsonValue& id, const QString& msg, int code = -32601);
    QJsonObject nvdSearch(const QString& query, int days = 0);
    QJsonArray  parseCveResponse(const QJsonObject& nvdResp);

    Server*            m_server;
    shadow::NativeTools m_tools;
    QElapsedTimer      m_uptime;
    QString            m_stateDir;
    QString            m_statePath;

    // ── Shared state (protected by m_mutex) ──────────────────────────────────
    mutable QMutex m_mutex;
    QJsonArray     m_devices;
    QJsonArray     m_incidents;

    // ── Scan state ────────────────────────────────────────────────────────────
    std::atomic<bool>  m_scanRunning{false};
    shadow::Cancel     m_scanCancel;

    // ── Counter-intel state (protected by m_ciMutex) ─────────────────────────
    mutable QMutex     m_ciMutex;
    CiState            m_ciState;
    std::atomic<bool>  m_ciRunning{false};
};
