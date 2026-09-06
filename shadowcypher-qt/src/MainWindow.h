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
    static constexpr int PAGE_DASHBOARD    = 0;
    static constexpr int PAGE_GUARDIAN     = 1;
    static constexpr int PAGE_COUNTER_INTEL = 2;
    static constexpr int PAGE_ARSENAL      = 3;
    static constexpr int PAGE_AI           = 4;
    static constexpr int PAGE_SHADOWSCRIPT = 5;
    static constexpr int PAGE_CHAT         = 6;
    static constexpr int PAGE_GHOST        = 7;
    static constexpr int PAGE_MAIL         = 8;
    static constexpr int PAGE_SETTINGS     = 9;
};
