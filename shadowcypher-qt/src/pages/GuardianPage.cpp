#include "GuardianPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSplitter>
#include <QHeaderView>
#include <QJsonObject>
#include <QJsonArray>
#include <QDateTime>
#include <QPushButton>

GuardianPage::GuardianPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();

    m_timer = new QTimer(this);
    m_timer->setInterval(8000);
    connect(m_timer, &QTimer::timeout, this, &GuardianPage::refresh);
    m_timer->start();

    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &GuardianPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            m_feed->log("Guardian daemon connected — fetching network state", "SUCCESS");
            refresh();
        });
    }

    refresh();
}

void GuardianPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(12);

    // ── Header ──
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#00d4ff;letter-spacing:2px;'>NETWORK GUARDIAN</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);
    header->addStretch();

    auto* scanBtn = new QPushButton("⚡ FORCE SCAN");
    scanBtn->setStyleSheet(
        "QPushButton { background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.3); "
        "color: #00d4ff; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px; "
        "padding: 6px 16px; border-radius: 4px; }"
        "QPushButton:hover { background: rgba(0,212,255,0.15); }"
    );
    connect(scanBtn, &QPushButton::clicked, this, [this]() {
        if (m_ipc && m_ipc->isConnected()) m_ipc->call("trigger_scan");
        m_feed->log("Manual scan triggered", "INFO");
    });
    header->addWidget(scanBtn);
    lay->addLayout(header);

    // ── Summary bar ──
    m_summaryLabel = new QLabel("Waiting for daemon…");
    m_summaryLabel->setStyleSheet("color: #64748b; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;");
    lay->addWidget(m_summaryLabel);

    // ── Main splitter: devices (top) | incidents (bottom) ──
    auto* splitter = new QSplitter(Qt::Vertical);
    splitter->setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.05); height: 2px; }");

    // Device table
    auto* devBox = new QWidget;
    auto* devLay = new QVBoxLayout(devBox);
    devLay->setContentsMargins(0, 0, 0, 0);
    devLay->setSpacing(4);
    auto* devLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>NETWORK DEVICES</span>");
    devLbl->setTextFormat(Qt::RichText);
    devLay->addWidget(devLbl);

    m_deviceTable = new QTableWidget(0, 6);
    m_deviceTable->setHorizontalHeaderLabels({"IP", "MAC", "HOSTNAME", "VENDOR", "PORTS", "RISK"});
    m_deviceTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_deviceTable->horizontalHeader()->setSectionResizeMode(4, QHeaderView::ResizeToContents);
    m_deviceTable->horizontalHeader()->setSectionResizeMode(5, QHeaderView::ResizeToContents);
    m_deviceTable->verticalHeader()->hide();
    m_deviceTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_deviceTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_deviceTable->setAlternatingRowColors(true);
    m_deviceTable->setStyleSheet(R"(
        QTableWidget {
            background: #0a0d1a; color: #cbd5e1;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px; font-size: 12px;
            gridline-color: rgba(255,255,255,0.04);
        }
        QTableWidget::item { padding: 6px 8px; }
        QTableWidget::item:selected { background: rgba(0,212,255,0.1); color: #e2e8f0; }
        QTableWidget::item:alternate { background: rgba(255,255,255,0.01); }
        QHeaderView::section {
            background: #111827; color: #475569;
            font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 1px;
            padding: 6px; border: none; border-bottom: 1px solid rgba(255,255,255,0.06);
        }
    )");
    connect(m_deviceTable, &QTableWidget::cellClicked, this, &GuardianPage::onDeviceRowClicked);
    devLay->addWidget(m_deviceTable);
    splitter->addWidget(devBox);

    // Incident table
    auto* incBox = new QWidget;
    auto* incLay = new QVBoxLayout(incBox);
    incLay->setContentsMargins(0, 0, 0, 0);
    incLay->setSpacing(4);
    auto* incLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>ACTIVE INCIDENTS</span>");
    incLbl->setTextFormat(Qt::RichText);
    incLay->addWidget(incLbl);

    m_incidentTable = new QTableWidget(0, 5);
    m_incidentTable->setHorizontalHeaderLabels({"TIME", "SEVERITY", "DEVICE", "TYPE", "DESCRIPTION"});
    m_incidentTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_incidentTable->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    m_incidentTable->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    m_incidentTable->verticalHeader()->hide();
    m_incidentTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_incidentTable->setAlternatingRowColors(true);
    m_incidentTable->setStyleSheet(m_deviceTable->styleSheet());
    incLay->addWidget(m_incidentTable);
    splitter->addWidget(incBox);

    splitter->setSizes({350, 200});
    lay->addWidget(splitter, 1);

    // Live feed
    auto* feedLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>GUARDIAN FEED</span>");
    feedLbl->setTextFormat(Qt::RichText);
    lay->addWidget(feedLbl);
    m_feed = new TacticalTerminal(this);
    m_feed->setMaximumHeight(120);
    lay->addWidget(m_feed);

    m_feed->log("Guardian page ready — waiting for daemon connection", "SYSTEM");
}

void GuardianPage::refresh() {
    if (!m_ipc || !m_ipc->isConnected()) return;
    m_devicesReqId   = m_ipc->call("get_devices");
    m_incidentsReqId = m_ipc->call("get_incidents");
}

void GuardianPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_devicesReqId) {
        QJsonArray devices = result.value("devices").toArray();
        populateDevices(devices);
        int total  = devices.size();
        int trusted = 0;
        for (const auto& d : devices)
            if (d.toObject().value("trusted").toBool()) trusted++;
        m_summaryLabel->setText(
            QString("  %1 devices  ·  %2 trusted  ·  last scan: %3")
            .arg(total).arg(trusted)
            .arg(QDateTime::currentDateTime().toString("HH:mm:ss"))
        );
    } else if (id == m_incidentsReqId) {
        populateIncidents(result.value("incidents").toArray());
    }
}

void GuardianPage::populateDevices(const QJsonArray& devices) {
    m_deviceTable->setRowCount(0);
    for (const auto& val : devices) {
        QJsonObject d = val.toObject();
        int row = m_deviceTable->rowCount();
        m_deviceTable->insertRow(row);

        auto cell = [&](int col, const QString& text, const QString& color = "") {
            auto* item = new QTableWidgetItem(text);
            item->setTextAlignment(Qt::AlignVCenter | Qt::AlignLeft);
            if (!color.isEmpty())
                item->setForeground(QColor(color));
            m_deviceTable->setItem(row, col, item);
        };

        cell(0, d.value("ip").toString(), "#00d4ff");
        cell(1, d.value("mac").toString(), "#64748b");
        cell(2, d.value("hostname").toString("—"));
        cell(3, d.value("vendor").toString("Unknown"));

        QJsonArray ports = d.value("open_ports").toArray();
        QStringList portList;
        for (const auto& p : ports) portList << QString::number(p.toInt());
        cell(4, portList.isEmpty() ? "—" : portList.join(", "));

        int risk = d.value("risk_score").toInt(0);
        auto* riskItem = new QTableWidgetItem(QString::number(risk));
        riskItem->setTextAlignment(Qt::AlignCenter);
        riskItem->setForeground(QColor(riskColor(risk)));
        m_deviceTable->setItem(row, 5, riskItem);
    }
}

void GuardianPage::populateIncidents(const QJsonArray& incidents) {
    m_incidentTable->setRowCount(0);
    for (const auto& val : incidents) {
        QJsonObject inc = val.toObject();
        if (inc.value("status").toString() != "open") continue;
        int row = m_incidentTable->rowCount();
        m_incidentTable->insertRow(row);

        QString sev = inc.value("severity").toString("info");
        QString ts  = inc.value("created_at").toString().left(16).replace("T", " ");

        auto cell = [&](int col, const QString& text, const QString& color = "") {
            auto* item = new QTableWidgetItem(text);
            if (!color.isEmpty()) item->setForeground(QColor(color));
            m_incidentTable->setItem(row, col, item);
        };

        cell(0, ts, "#64748b");
        auto* sevItem = new QTableWidgetItem(sev.toUpper());
        sevItem->setForeground(QColor(severityColor(sev)));
        sevItem->setTextAlignment(Qt::AlignCenter);
        m_incidentTable->setItem(row, 1, sevItem);
        cell(2, inc.value("device_ip").toString("—"), "#00d4ff");
        cell(3, inc.value("type").toString("—"));
        cell(4, inc.value("description").toString());

        m_feed->log(
            QString("[%1] %2 — %3").arg(sev.toUpper(), inc.value("device_ip").toString(), inc.value("description").toString()),
            sev == "critical" ? "CRITICAL" : sev == "warning" ? "WARNING" : "INFO"
        );
    }
}

void GuardianPage::onDeviceRowClicked(int row, int) {
    auto* ipItem = m_deviceTable->item(row, 0);
    if (ipItem) m_feed->log("Selected device: " + ipItem->text(), "INFO");
}

QString GuardianPage::riskColor(int score) {
    if (score >= 60) return "#f43f5e";
    if (score >= 30) return "#ffb84d";
    return "#10b981";
}

QString GuardianPage::severityColor(const QString& sev) {
    if (sev == "critical") return "#f43f5e";
    if (sev == "warning")  return "#ffb84d";
    return "#38bdf8";
}
