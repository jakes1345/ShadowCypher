#pragma once
#include <QWidget>
#include <QLabel>
#include <QTimer>
#include "../widgets/ArcGauge.h"
#include "../widgets/MiniStat.h"
#include "../widgets/TacticalTerminal.h"
#include "../ipc/IpcClient.h"

class DashboardPage : public QWidget {
    Q_OBJECT
public:
    explicit DashboardPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void tick();
    void onIpcResult(int id, QJsonObject result);

private:
    IpcClient* m_ipc;
    QTimer*    m_timer;

    // Gauges
    ArcGauge* m_cpuGauge;
    ArcGauge* m_ramGauge;
    ArcGauge* m_diskGauge;

    // Stats
    MiniStat* m_statAi;
    MiniStat* m_statMissions;
    MiniStat* m_statUptime;
    MiniStat* m_statStealth;
    MiniStat* m_statThreats;
    MiniStat* m_statIntegrity;
    MiniStat* m_statRelay;
    MiniStat* m_statNet;
    MiniStat* m_statEntropy;

    TacticalTerminal* m_terminal;
    QLabel* m_statusLabel;

    // Rolling net counter
    qint64 m_lastNetBytes = 0;
    qint64 m_lastNetTime  = 0;

    void buildUi();
    void refreshLocalMetrics();
    void requestDaemonStats();
    void updateNetSpeed();
    void updateEntropy();
};
