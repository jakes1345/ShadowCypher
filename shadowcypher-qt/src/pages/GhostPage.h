#pragma once
#include <QWidget>
#include <QLabel>
#include <QPushButton>
#include <QTimer>
#include <QProcess>
#include <QJsonObject>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class GhostPage : public QWidget {
    Q_OBJECT
public:
    explicit GhostPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void refresh();
    void onIpcResult(int id, QJsonObject result);
    void toggleGhostMode();

    // QProcess slots
    void onTorCheckFinished(int exitCode, QProcess::ExitStatus status);
    void onKillSwitchCheckFinished(int exitCode, QProcess::ExitStatus status);
    void onMacCheckFinished(int exitCode, QProcess::ExitStatus status);
    void onDnsCheckFinished(int exitCode, QProcess::ExitStatus status);

private:
    IpcClient*        m_ipc;
    QPushButton*      m_toggleBtn;
    QPushButton*      m_refreshBtn;

    // Status card value labels
    QLabel*           m_torDot;
    QLabel*           m_torStatus;
    QLabel*           m_ksDot;
    QLabel*           m_ksStatus;
    QLabel*           m_macLabel;
    QLabel*           m_dnsDot;
    QLabel*           m_dnsStatus;

    TacticalTerminal* m_terminal;
    QTimer*           m_timer;

    bool m_ghostActive = false;
    bool m_waiting     = false;

    int m_statusReqId = -1;
    int m_enableReqId = -1;

    // Running QProcess instances
    QProcess* m_torProc  = nullptr;
    QProcess* m_ksProc   = nullptr;
    QProcess* m_macProc  = nullptr;
    QProcess* m_dnsProc  = nullptr;

    void buildUi();
    QWidget* makeCard(const QString& title, QLabel*& dot, QLabel*& value, const QString& initValue);

    void applyStatus(bool tor, bool ks, const QString& mac, bool dns, bool active);
    void updateToggleButton();

    void checkViaProcess();
    void killOldProcesses();

    static QString dotHtml(const QString& color);
};
