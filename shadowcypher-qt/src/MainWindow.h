#pragma once
#include <QMainWindow>
#include <QStackedWidget>
#include <QListWidget>
#include <QPushButton>
#include "ipc/IpcClient.h"

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget* parent = nullptr);

private slots:
    void onNavChanged(int row);
    void onIpcConnected();
    void onIpcDisconnected();

private:
    IpcClient*     m_ipc;
    QStackedWidget* m_stack;
    QListWidget*   m_nav;
    QLabel*        m_connectionDot;

    void buildSidebar(QWidget* parent);
    void buildPages();
    void applyWindowStyle();

    struct NavItem { QString icon; QString label; };
    static constexpr int PAGE_DASHBOARD     = 0;
    static constexpr int PAGE_GUARDIAN      = 1;
    static constexpr int PAGE_NETWORK       = 2;
    static constexpr int PAGE_THREAT        = 3;
    static constexpr int PAGE_OSINT         = 4;
    static constexpr int PAGE_VULN          = 5;
    static constexpr int PAGE_COUNTER_INTEL = 6;
    static constexpr int PAGE_ARSENAL       = 7;
    static constexpr int PAGE_AI            = 8;
    static constexpr int PAGE_SHADOWSCRIPT  = 9;
    static constexpr int PAGE_CHAT          = 10;
    static constexpr int PAGE_GHOST         = 11;
    static constexpr int PAGE_MAIL          = 12;
    static constexpr int PAGE_CVE_FEED      = 13;
    static constexpr int PAGE_SETTINGS      = 14;
};
