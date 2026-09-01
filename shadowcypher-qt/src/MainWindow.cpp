#include "MainWindow.h"
#include "theme.h"
#include "pages/DashboardPage.h"
#include "pages/GuardianPage.h"
#include "pages/CounterIntelPage.h"
#include "pages/ArsenalPage.h"
#include "pages/AiPage.h"
#include "pages/ShadowScriptPage.h"
#include "pages/PlaceholderPage.h"
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QLabel>
#include <QSplitter>
#include <QListWidgetItem>
#include <QStatusBar>

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle("ShadowCypher");
    setMinimumSize(1100, 700);
    resize(1360, 820);
    applyWindowStyle();

    m_ipc = new IpcClient(this);
    connect(m_ipc, &IpcClient::connected,    this, &MainWindow::onIpcConnected);
    connect(m_ipc, &IpcClient::disconnected, this, &MainWindow::onIpcDisconnected);

    // Central splitter: sidebar | content
    auto* central = new QWidget(this);
    setCentralWidget(central);

    auto* rootLayout = new QHBoxLayout(central);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    // ── Sidebar ──
    auto* sidebar = new QWidget;
    sidebar->setFixedWidth(Theme::SIDEBAR_W);
    sidebar->setStyleSheet(
        "QWidget { background: #080c1a; border-right: 1px solid rgba(255,255,255,0.05); }"
    );
    auto* sideLayout = new QVBoxLayout(sidebar);
    sideLayout->setContentsMargins(0, 0, 0, 0);
    sideLayout->setSpacing(0);

    // Logo
    auto* logoBox = new QWidget;
    logoBox->setFixedHeight(64);
    logoBox->setStyleSheet("border-bottom: 1px solid rgba(255,255,255,0.05);");
    auto* logoLay = new QHBoxLayout(logoBox);
    logoLay->setContentsMargins(16, 0, 16, 0);
    auto* logoLbl = new QLabel;
    logoLbl->setText(
        "<span style='font-weight:900;font-size:14px;color:#b44aff;letter-spacing:3px;'>"
        "SHADOW</span>"
        "<span style='font-weight:300;font-size:14px;color:#e2e8f0;letter-spacing:1px;'>"
        "CYPHER</span>"
    );
    logoLbl->setTextFormat(Qt::RichText);
    logoLay->addWidget(logoLbl);

    m_connectionDot = new QLabel("●");
    m_connectionDot->setStyleSheet("color: #334155; font-size: 10px;");
    m_connectionDot->setToolTip("Daemon connection status");
    logoLay->addStretch();
    logoLay->addWidget(m_connectionDot);
    sideLayout->addWidget(logoBox);

    // Nav list
    m_nav = new QListWidget;
    m_nav->setStyleSheet(R"(
        QListWidget {
            background: transparent;
            border: none;
            outline: none;
            padding: 8px 0;
        }
        QListWidget::item {
            padding: 10px 20px;
            color: #64748b;
            font-size: 12px;
            letter-spacing: 1.5px;
            font-family: "JetBrains Mono";
            border-left: 3px solid transparent;
        }
        QListWidget::item:hover {
            color: #94a3b8;
            background: rgba(255,255,255,0.03);
        }
        QListWidget::item:selected {
            color: #b44aff;
            background: rgba(180,74,255,0.08);
            border-left: 3px solid #b44aff;
        }
    )");

    struct NavDef { const char* label; };
    static const NavDef navItems[] = {
        {"  DASHBOARD"},
        {"  GUARDIAN"},
        {"  COUNTER-INTEL"},
        {"  ARSENAL"},
        {"  AI ASSISTANT"},
        {"  SHADOWSCRIPT"},
        {"  SETTINGS"},
    };
    for (const auto& item : navItems)
        m_nav->addItem(item.label);
    m_nav->setCurrentRow(0);

    connect(m_nav, &QListWidget::currentRowChanged, this, &MainWindow::onNavChanged);
    sideLayout->addWidget(m_nav);
    sideLayout->addStretch();

    // Version badge
    auto* verLbl = new QLabel("v1.0.0-qt6");
    verLbl->setStyleSheet("color: #1e293b; font-size: 10px; padding: 8px 20px; font-family: 'JetBrains Mono';");
    sideLayout->addWidget(verLbl);
    rootLayout->addWidget(sidebar);

    // ── Page stack ──
    m_stack = new QStackedWidget;
    m_stack->setStyleSheet("QStackedWidget { background: #0d0f1a; }");

    m_stack->addWidget(new DashboardPage(m_ipc, this));      // 0
    m_stack->addWidget(new GuardianPage(m_ipc, this));       // 1
    m_stack->addWidget(new CounterIntelPage(m_ipc, this));   // 2
    m_stack->addWidget(new ArsenalPage(this));               // 3
    m_stack->addWidget(new AiPage(m_ipc, this));             // 4
    m_stack->addWidget(new ShadowScriptPage(m_ipc, this));   // 5
    m_stack->addWidget(new PlaceholderPage("SETTINGS", this)); // 6

    rootLayout->addWidget(m_stack);

    // Status bar
    statusBar()->setStyleSheet(
        "QStatusBar { background: #080c1a; color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; "
        "border-top: 1px solid rgba(255,255,255,0.04); }"
    );
    statusBar()->showMessage("SHADOWCYPHER TACTICAL OS  |  Qt6 Native  |  Daemon: disconnected");

    // Start IPC
    m_ipc->connectToDaemon();
}

void MainWindow::onNavChanged(int row) {
    m_stack->setCurrentIndex(row);
}

void MainWindow::onIpcConnected() {
    m_connectionDot->setStyleSheet("color: #00ff9d; font-size: 10px;");
    m_connectionDot->setToolTip("Daemon connected");
    statusBar()->showMessage("SHADOWCYPHER TACTICAL OS  |  Qt6 Native  |  Daemon: CONNECTED");
}

void MainWindow::onIpcDisconnected() {
    m_connectionDot->setStyleSheet("color: #334155; font-size: 10px;");
    m_connectionDot->setToolTip("Daemon offline");
    statusBar()->showMessage("SHADOWCYPHER TACTICAL OS  |  Qt6 Native  |  Daemon: reconnecting…");
}

void MainWindow::applyWindowStyle() {
    setStyleSheet(Theme::appStyleSheet());
}
