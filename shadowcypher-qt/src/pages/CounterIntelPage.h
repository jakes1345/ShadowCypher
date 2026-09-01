#pragma once
#include <QWidget>
#include <QLabel>
#include <QTimer>
#include <QListWidget>
#include <QPushButton>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

// Real-time counter-intelligence detection feed
// Drives shadowcypher.modules.counter_intel.CounterIntelEngine via IPC
class CounterIntelPage : public QWidget {
    Q_OBJECT
public:
    explicit CounterIntelPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void startFullScan();
    void onIpcResult(int id, QJsonObject result);
    void pollStatus();

private:
    IpcClient*    m_ipc;
    QTimer*       m_pollTimer;
    QPushButton*  m_scanBtn;
    QLabel*       m_statusLabel;
    QListWidget*  m_findingsList;
    TacticalTerminal* m_feed;
    bool          m_scanning = false;
    int           m_scanReqId = -1;
    int           m_pollReqId = -1;

    void buildUi();
    void setScanningState(bool scanning);
    void addFinding(const QJsonObject& finding);

    struct CheckRow {
        QString name;
        QLabel* statusDot;
        QLabel* resultLabel;
    };
    QList<CheckRow> m_checks;

    QWidget* makeCheckRow(const QString& name, const QString& description);
    void setCheckStatus(const QString& name, const QString& status, const QString& detail = {});
};
