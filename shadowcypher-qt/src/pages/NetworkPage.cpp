#include "NetworkPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QHeaderView>
#include <QGroupBox>
#include <QSplitter>
#include <QFile>
#include <QNetworkInterface>
#include <QNetworkAddressEntry>
#include <QDateTime>

// ── Helper: decode /proc/net/tcp hex addr:port ────────────────────────────
QString NetworkPage::hexToIp(const QString& hex) {
    bool ok;
    quint32 ip = hex.toUInt(&ok, 16);
    if (!ok) return hex;
    return QString("%1.%2.%3.%4")
        .arg(ip & 0xff).arg((ip >> 8) & 0xff)
        .arg((ip >> 16) & 0xff).arg((ip >> 24) & 0xff);
}
QString NetworkPage::hexToPort(const QString& hex) {
    bool ok;
    int p = hex.toInt(&ok, 16);
    return ok ? QString::number(p) : hex;
}
QString NetworkPage::connState(const QString& st) {
    static const QMap<QString, QString> states = {
        {"01","ESTABLISHED"}, {"02","SYN_SENT"}, {"03","SYN_RECV"},
        {"04","FIN_WAIT1"}, {"05","FIN_WAIT2"}, {"06","TIME_WAIT"},
        {"07","CLOSE"}, {"08","CLOSE_WAIT"}, {"09","LAST_ACK"},
        {"0A","LISTEN"}, {"0B","CLOSING"},
    };
    return states.value(st.toUpper(), st);
}

// ── Shared button style ───────────────────────────────────────────────────
static QString btnStyle(const QString& color) {
    return QString(R"(
        QPushButton {
            background: rgba(%1,0.1); border: 1px solid rgba(%1,0.35);
            color: #%1_c; font-family: 'JetBrains Mono'; font-size: 11px;
            letter-spacing: 1px; padding: 6px 14px; border-radius: 4px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(%1,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )").replace("%1", color);
}

NetworkPage::NetworkPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();

    m_timer = new QTimer(this);
    m_timer->setInterval(3000);
    connect(m_timer, &QTimer::timeout, this, &NetworkPage::tick);
    m_timer->start();

    refreshInterfaces();
    refreshConnections();
}

void NetworkPage::buildUi() {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(20, 14, 20, 14);
    outer->setSpacing(10);

    // Header
    auto* hdr = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#38bdf8;letter-spacing:2px;'>NETWORK_OPS</span>");
    title->setTextFormat(Qt::RichText);
    hdr->addWidget(title);
    hdr->addStretch();
    outer->addLayout(hdr);

    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->setChildrenCollapsible(false);

    // ── Top: Tabs (Interfaces / Connections) ──
    auto* tabs = new QTabWidget;
    tabs->setStyleSheet(R"(
        QTabWidget::pane { border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
        QTabBar::tab { background: transparent; color: #475569; font-family: 'JetBrains Mono';
            font-size: 11px; letter-spacing: 1px; padding: 6px 16px; }
        QTabBar::tab:selected { color: #38bdf8; border-bottom: 2px solid #38bdf8; }
        QTabBar::tab:hover { color: #94a3b8; }
    )");

    // Interfaces table
    m_ifaceTable = new QTableWidget(0, 5);
    m_ifaceTable->setHorizontalHeaderLabels({"Interface", "State", "IP Address", "MAC", "RX / TX"});
    m_ifaceTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_ifaceTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_ifaceTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_ifaceTable->setStyleSheet(R"(
        QTableWidget { background: #060810; border: none; color: #94a3b8;
            font-family: 'JetBrains Mono'; font-size: 12px; gridline-color: rgba(255,255,255,0.04); }
        QTableWidget::item:selected { background: rgba(56,189,248,0.1); color: #38bdf8; }
        QHeaderView::section { background: #111827; color: #475569; border: none;
            font-size: 10px; letter-spacing: 1px; padding: 6px; }
    )");
    m_ifaceTable->verticalHeader()->setVisible(false);
    tabs->addTab(m_ifaceTable, "  INTERFACES  ");

    // Connections table
    m_connTable = new QTableWidget(0, 5);
    m_connTable->setHorizontalHeaderLabels({"Proto", "Local Address", "Remote Address", "State", "PID"});
    m_connTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_connTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_connTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_connTable->setStyleSheet(m_ifaceTable->styleSheet());
    m_connTable->verticalHeader()->setVisible(false);
    tabs->addTab(m_connTable, "  CONNECTIONS  ");

    splitter->addWidget(tabs);

    // ── Bottom: scan controls + terminal ──
    auto* bottom = new QWidget;
    auto* botLay = new QVBoxLayout(bottom);
    botLay->setContentsMargins(0, 0, 0, 0);
    botLay->setSpacing(8);

    // Controls row
    auto* ctrlRow = new QHBoxLayout;
    ctrlRow->setSpacing(8);

    m_targetEdit = new QLineEdit;
    m_targetEdit->setPlaceholderText("Target (IP / subnet / host)");
    m_targetEdit->setStyleSheet(R"(
        QLineEdit { background: #060810; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px; color: #e2e8f0; font-family: 'JetBrains Mono';
            font-size: 12px; padding: 6px 10px; }
        QLineEdit:focus { border-color: #38bdf8; }
    )");
    ctrlRow->addWidget(m_targetEdit, 2);

    m_portsEdit = new QLineEdit;
    m_portsEdit->setPlaceholderText("Ports (1-1024)");
    m_portsEdit->setText("1-1024");
    m_portsEdit->setFixedWidth(130);
    m_portsEdit->setStyleSheet(m_targetEdit->styleSheet());
    ctrlRow->addWidget(m_portsEdit);

    m_ifaceCombo = new QComboBox;
    m_ifaceCombo->setStyleSheet(R"(
        QComboBox { background: #060810; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 4px; color: #94a3b8; font-family: 'JetBrains Mono';
            font-size: 11px; padding: 6px 10px; min-width: 100px; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #111827; color: #e2e8f0; border: 1px solid rgba(255,255,255,0.1); }
    )");
    m_ifaceCombo->addItem("auto");
    for (const auto& iface : QNetworkInterface::allInterfaces()) {
        if (iface.flags().testFlag(QNetworkInterface::IsLoBack)) continue;
        m_ifaceCombo->addItem(iface.name());
    }
    ctrlRow->addWidget(m_ifaceCombo);

    m_arpBtn = new QPushButton("ARP SCAN");
    m_arpBtn->setStyleSheet(R"(
        QPushButton { background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.35);
            color: #38bdf8; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; font-weight: 700; }
        QPushButton:hover { background: rgba(56,189,248,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; } )");
    connect(m_arpBtn, &QPushButton::clicked, this, &NetworkPage::runArpScan);
    ctrlRow->addWidget(m_arpBtn);

    m_scanBtn = new QPushButton("PORT SCAN");
    m_scanBtn->setStyleSheet(R"(
        QPushButton { background: rgba(180,74,255,0.1); border: 1px solid rgba(180,74,255,0.35);
            color: #b44aff; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; font-weight: 700; }
        QPushButton:hover { background: rgba(180,74,255,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; } )");
    connect(m_scanBtn, &QPushButton::clicked, this, &NetworkPage::runPortScan);
    ctrlRow->addWidget(m_scanBtn);

    m_captureBtn = new QPushButton("CAPTURE");
    m_captureBtn->setStyleSheet(R"(
        QPushButton { background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.35);
            color: #fbbf24; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; font-weight: 700; }
        QPushButton:hover { background: rgba(251,191,36,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; } )");
    connect(m_captureBtn, &QPushButton::clicked, this, &NetworkPage::runCapture);
    ctrlRow->addWidget(m_captureBtn);

    m_stopBtn = new QPushButton("■ STOP");
    m_stopBtn->setEnabled(false);
    m_stopBtn->setStyleSheet(R"(
        QPushButton { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.35);
            color: #f43f5e; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing:1px;
            padding: 6px 14px; border-radius: 4px; }
        QPushButton:hover { background: rgba(244,63,94,0.2); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; } )");
    connect(m_stopBtn, &QPushButton::clicked, this, &NetworkPage::stopAll);
    ctrlRow->addWidget(m_stopBtn);
    botLay->addLayout(ctrlRow);

    m_output = new TacticalTerminal(this);
    m_output->setMinimumHeight(200);
    botLay->addWidget(m_output);

    splitter->addWidget(bottom);
    splitter->setSizes({260, 340});

    outer->addWidget(splitter, 1);
}

void NetworkPage::tick() {
    if (!isVisible()) return;
    refreshInterfaces();
    refreshConnections();
}

void NetworkPage::refreshInterfaces() {
    m_ifaceTable->setRowCount(0);

    // Read /proc/net/dev for byte counters
    QMap<QString, QPair<qint64,qint64>> rxTx;
    QFile netdev("/proc/net/dev");
    if (netdev.open(QIODevice::ReadOnly)) {
        netdev.readLine(); netdev.readLine();
        while (!netdev.atEnd()) {
            QByteArray line = netdev.readLine().trimmed();
            int colon = line.indexOf(':');
            if (colon < 0) continue;
            QString name = QString(line.left(colon)).trimmed();
            QByteArray rest = line.mid(colon + 1).trimmed();
            QList<QByteArray> cols = rest.split(' ');
            cols.removeAll("");
            if (cols.size() >= 9)
                rxTx[name] = {cols[0].toLongLong(), cols[8].toLongLong()};
        }
        netdev.close();
    }

    auto fmtBytes = [](qint64 b) -> QString {
        if (b >= 1073741824) return QString::number(b / 1073741824.0, 'f', 1) + " GB";
        if (b >= 1048576)    return QString::number(b / 1048576.0,    'f', 1) + " MB";
        if (b >= 1024)       return QString::number(b / 1024.0,       'f', 1) + " KB";
        return QString::number(b) + " B";
    };

    for (const auto& iface : QNetworkInterface::allInterfaces()) {
        int row = m_ifaceTable->rowCount();
        m_ifaceTable->insertRow(row);

        m_ifaceTable->setItem(row, 0, new QTableWidgetItem(iface.name()));

        bool up = iface.flags().testFlag(QNetworkInterface::IsUp);
        bool running = iface.flags().testFlag(QNetworkInterface::IsRunning);
        auto* stItem = new QTableWidgetItem(up && running ? "UP" : up ? "DOWN" : "INACTIVE");
        stItem->setForeground(up && running ? QColor("#00ff9d") : QColor("#f43f5e"));
        m_ifaceTable->setItem(row, 1, stItem);

        QStringList ips;
        for (const auto& entry : iface.addressEntries())
            ips << entry.ip().toString();
        m_ifaceTable->setItem(row, 2, new QTableWidgetItem(ips.join(", ")));
        m_ifaceTable->setItem(row, 3, new QTableWidgetItem(iface.hardwareAddress()));

        auto it = rxTx.find(iface.name());
        if (it != rxTx.end())
            m_ifaceTable->setItem(row, 4, new QTableWidgetItem(
                "↓ " + fmtBytes(it->first) + " / ↑ " + fmtBytes(it->second)));
        else
            m_ifaceTable->setItem(row, 4, new QTableWidgetItem("—"));
    }
}

void NetworkPage::refreshConnections() {
    m_connTable->setRowCount(0);

    auto parseProc = [this](const QString& path, const QString& proto) {
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) return;
        f.readLine(); // header
        while (!f.atEnd()) {
            QString line = f.readLine().trimmed();
            QStringList cols = line.split(' ', Qt::SkipEmptyParts);
            if (cols.size() < 10) continue;

            QString localAddrPort = cols[1];
            QString remAddrPort   = cols[2];
            QString state         = cols[3];
            QString uid           = cols[7];

            QStringList lp = localAddrPort.split(':');
            QStringList rp = remAddrPort.split(':');
            if (lp.size() < 2 || rp.size() < 2) continue;

            QString localStr = hexToIp(lp[0]) + ":" + hexToPort(lp[1]);
            QString remStr   = hexToIp(rp[0]) + ":" + hexToPort(rp[1]);
            QString stStr    = connState(state);

            // Only show established, listen, close_wait
            if (stStr != "ESTABLISHED" && stStr != "LISTEN" && stStr != "CLOSE_WAIT") continue;

            int row = m_connTable->rowCount();
            m_connTable->insertRow(row);
            m_connTable->setItem(row, 0, new QTableWidgetItem(proto));
            m_connTable->setItem(row, 1, new QTableWidgetItem(localStr));
            m_connTable->setItem(row, 2, new QTableWidgetItem(remStr));
            auto* stItem = new QTableWidgetItem(stStr);
            stItem->setForeground(stStr == "ESTABLISHED" ? QColor("#00ff9d") :
                                  stStr == "LISTEN"       ? QColor("#38bdf8") : QColor("#fbbf24"));
            m_connTable->setItem(row, 3, stItem);
            m_connTable->setItem(row, 4, new QTableWidgetItem(uid));
        }
        f.close();
    };

    parseProc("/proc/net/tcp",  "TCP");
    parseProc("/proc/net/tcp6", "TCP6");
}

void NetworkPage::startProcess(const QStringList& cmd, const QString& label) {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_output->log("Process already running — stop first", "WARNING");
        return;
    }
    delete m_proc;
    m_proc = new QProcess(this);
    m_activeOp = label;

    connect(m_proc, &QProcess::readyReadStandardOutput, this, &NetworkPage::onProcessOutput);
    connect(m_proc, &QProcess::readyReadStandardError,  this, [this]() {
        QString err = m_proc->readAllStandardError().trimmed();
        if (!err.isEmpty()) m_output->log(err, "WARNING");
    });
    connect(m_proc, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &NetworkPage::onProcessFinished);

    m_output->log("▶ " + label + ": " + cmd.join(" "), "SYSTEM");
    m_proc->start(cmd[0], cmd.mid(1));
    m_stopBtn->setEnabled(true);
    m_arpBtn->setEnabled(false);
    m_scanBtn->setEnabled(false);
    m_captureBtn->setEnabled(false);
}

void NetworkPage::runArpScan() {
    QString target = m_targetEdit->text().trimmed();
    if (target.isEmpty()) target = "192.168.1.0/24";
    QString iface = m_ifaceCombo->currentText();

    // Prefer arp-scan, fall back to nmap -sn
    QStringList cmd;
    if (QProcess::execute("which", {"arp-scan"}) == 0)
        cmd = {"arp-scan", "--localnet",
               iface != "auto" ? "--interface=" + iface : "", target};
    else
        cmd = {"nmap", "-sn", "-PR", target};

    cmd.removeAll("");
    startProcess(cmd, "ARP_SCAN");
}

void NetworkPage::runPortScan() {
    QString target = m_targetEdit->text().trimmed();
    if (target.isEmpty()) {
        m_output->log("Enter a target IP/hostname", "WARNING");
        return;
    }
    QString ports = m_portsEdit->text().trimmed();
    if (ports.isEmpty()) ports = "1-1024";

    QStringList cmd = {"nmap", "-sV", "--open", "-p", ports, target};
    startProcess(cmd, "PORT_SCAN");
}

void NetworkPage::runCapture() {
    QString iface = m_ifaceCombo->currentText();
    if (iface == "auto") {
        // Pick first non-loopback
        for (const auto& i : QNetworkInterface::allInterfaces())
            if (!i.flags().testFlag(QNetworkInterface::IsLoBack) &&
                 i.flags().testFlag(QNetworkInterface::IsRunning)) {
                iface = i.name();
                break;
            }
    }
    if (iface.isEmpty()) {
        m_output->log("No suitable interface found", "WARNING");
        return;
    }
    QStringList cmd = {"tcpdump", "-i", iface, "-n", "-c", "200",
                       "--immediate-mode", "-l"};
    startProcess(cmd, "PACKET_CAPTURE[" + iface + "]");
}

void NetworkPage::stopAll() {
    if (m_proc && m_proc->state() != QProcess::NotRunning) {
        m_proc->terminate();
        m_proc->waitForFinished(2000);
        if (m_proc->state() != QProcess::NotRunning) m_proc->kill();
        m_output->log("■ Stopped: " + m_activeOp, "WARNING");
    }
    m_stopBtn->setEnabled(false);
    m_arpBtn->setEnabled(true);
    m_scanBtn->setEnabled(true);
    m_captureBtn->setEnabled(true);
}

void NetworkPage::onProcessOutput() {
    while (m_proc->canReadLine()) {
        QString line = m_proc->readLine().trimmed();
        if (!line.isEmpty()) m_output->log(line, "INFO");
    }
}

void NetworkPage::onProcessFinished(int code, QProcess::ExitStatus) {
    QString rest = m_proc->readAll().trimmed();
    if (!rest.isEmpty()) m_output->log(rest, "INFO");
    m_output->log(QString("✓ %1 finished (exit %2)").arg(m_activeOp).arg(code), "SUCCESS");
    m_stopBtn->setEnabled(false);
    m_arpBtn->setEnabled(true);
    m_scanBtn->setEnabled(true);
    m_captureBtn->setEnabled(true);
}
