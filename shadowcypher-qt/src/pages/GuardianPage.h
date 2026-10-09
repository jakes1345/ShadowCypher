#pragma once
#include <QWidget>
#include <QTableWidget>
#include <QLabel>
#include <QTimer>
#include <QJsonArray>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class GuardianPage : public QWidget {
    Q_OBJECT
public:
    explicit GuardianPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void refresh();
    void onIpcResult(int id, QJsonObject result);
    void onDeviceRowClicked(int row, int col);

private:
    IpcClient*        m_ipc;
    QTimer*           m_timer;
    QTableWidget*     m_deviceTable;
    QTableWidget*     m_incidentTable;
    QLabel*           m_summaryLabel;
    TacticalTerminal* m_feed;

    int m_devicesReqId   = -1;
    int m_incidentsReqId = -1;

    void buildUi();
    void populateDevices(const QJsonArray& devices);
    void populateIncidents(const QJsonArray& incidents);

    static QString riskColor(int score);
    static QString severityColor(const QString& sev);
};
