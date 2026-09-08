#pragma once
#include <QWidget>
#include <QTabWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QCheckBox>
#include <QComboBox>
#include <QLabel>
#include <QJsonObject>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class OsintPage : public QWidget {
    Q_OBJECT
public:
    explicit OsintPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void runDomainScan();
    void runIdentityScan();
    void onIpcResult(int id, QJsonObject result);

private:
    IpcClient*  m_ipc;
    QTabWidget* m_tabs;

    // ── Domain Intel tab ─────────────────────────────────
    QLineEdit*    m_domainInput;
    QPushButton*  m_domainRunBtn;
    QCheckBox*    m_chkWhois;
    QCheckBox*    m_chkDns;
    QCheckBox*    m_chkSsl;
    QCheckBox*    m_chkHeaders;
    QCheckBox*    m_chkTech;
    QCheckBox*    m_chkMx;
    QCheckBox*    m_chkSubnet;
    QCheckBox*    m_chkZone;
    QCheckBox*    m_chkWayback;
    TacticalTerminal* m_domainTerminal;
    QLabel*       m_domainStatusLbl;

    // ── Identity Intel tab ───────────────────────────────
    QLineEdit*    m_identInput;
    QComboBox*    m_modeBox;
    QPushButton*  m_identRunBtn;
    TacticalTerminal* m_identTerminal;
    QLabel*       m_identStatusLbl;

    int  m_domainReqId = -1;
    int  m_identReqId  = -1;
    bool m_domainRunning = false;
    bool m_identRunning  = false;

    void buildUi();
    QWidget* buildDomainTab();
    QWidget* buildIdentityTab();

    static QCheckBox* makeCheck(const QString& label, bool checked = true);
};
