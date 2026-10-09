#pragma once
#include <QWidget>
#include <QTimer>
#include <QProcess>
#include <QTableWidget>
#include <QTabWidget>
#include <QLineEdit>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class NetworkPage : public QWidget {
    Q_OBJECT
public:
    explicit NetworkPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void tick();
    void runArpScan();
    void runPortScan();
    void runCapture();
    void stopAll();
    void onProcessOutput();
    void onProcessFinished(int code, QProcess::ExitStatus status);

private:
    void buildUi();
    void refreshInterfaces();
    void refreshConnections();
    void startProcess(const QStringList& cmd, const QString& label);

    IpcClient*      m_ipc;
    QTimer*         m_timer;

    // Interface tab
    QTableWidget*   m_ifaceTable;

    // Connections tab
    QTableWidget*   m_connTable;

    // Scan controls
    QLineEdit*      m_targetEdit;
    QLineEdit*      m_portsEdit;
    QComboBox*      m_ifaceCombo;
    QPushButton*    m_arpBtn;
    QPushButton*    m_scanBtn;
    QPushButton*    m_captureBtn;
    QPushButton*    m_stopBtn;

    TacticalTerminal* m_output;
    QProcess*         m_proc{nullptr};
    QString           m_activeOp;

    static QString hexToIp(const QString& hex);
    static QString hexToPort(const QString& hex);
    static QString connState(const QString& st);
};
