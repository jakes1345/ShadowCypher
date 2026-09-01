#include "CounterIntelPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QScrollArea>
#include <QFrame>
#include <QJsonObject>
#include <QJsonArray>
#include <QListWidgetItem>
#include <QSplitter>

static const QList<QPair<QString,QString>> CHECKS = {
    {"arp_spoofing",      "ARP Spoofing / MITM"},
    {"promiscuous",       "Promiscuous Interfaces"},
    {"ssl_interception",  "SSL Interception"},
    {"dns_leak",          "DNS Leak"},
    {"rogue_dhcp",        "Rogue DHCP Server"},
    {"traffic_anomaly",   "Traffic Anomalies"},
    {"osint_self",        "OSINT Self-Audit"},
};

CounterIntelPage::CounterIntelPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();

    m_pollTimer = new QTimer(this);
    m_pollTimer->setInterval(2000);
    connect(m_pollTimer, &QTimer::timeout, this, &CounterIntelPage::pollStatus);

    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &CounterIntelPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            m_feed->log("Daemon connected — ready for counter-intel scan", "SUCCESS");
        });
    }
}

void CounterIntelPage::buildUi() {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 14, 20, 14);
    lay->setSpacing(12);

    // ── Header ──
    auto* header = new QHBoxLayout;
    auto* title = new QLabel;
    title->setText("<span style='font-weight:900;font-size:16px;color:#b44aff;letter-spacing:2px;'>COUNTER-INTELLIGENCE</span>");
    title->setTextFormat(Qt::RichText);
    header->addWidget(title);

    auto* sub = new QLabel("Detect when YOU are the target");
    sub->setStyleSheet("color: #475569; font-size: 12px; margin-left: 10px;");
    header->addWidget(sub);
    header->addStretch();

    m_scanBtn = new QPushButton("▶ RUN FULL SCAN");
    m_scanBtn->setStyleSheet(R"(
        QPushButton {
            background: rgba(180,74,255,0.12); border: 1px solid rgba(180,74,255,0.4);
            color: #b44aff; font-family: 'JetBrains Mono'; font-size: 11px; letter-spacing: 1px;
            padding: 7px 20px; border-radius: 4px; font-weight: 700;
        }
        QPushButton:hover { background: rgba(180,74,255,0.22); }
        QPushButton:disabled { color: #334155; border-color: #1e293b; }
    )");
    connect(m_scanBtn, &QPushButton::clicked, this, &CounterIntelPage::startFullScan);
    header->addWidget(m_scanBtn);
    lay->addLayout(header);

    m_statusLabel = new QLabel("STANDBY — no scan running");
    m_statusLabel->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;");
    lay->addWidget(m_statusLabel);

    // ── Splitter: checks (left) | findings (right) ──
    auto* splitter = new QSplitter(Qt::Horizontal);
    splitter->setStyleSheet("QSplitter::handle { background: rgba(255,255,255,0.05); width: 1px; }");

    // Left: check list
    auto* checksPanel = new QWidget;
    auto* checksLay   = new QVBoxLayout(checksPanel);
    checksLay->setContentsMargins(0, 0, 8, 0);
    checksLay->setSpacing(6);
    auto* chkLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>DETECTION CHECKS</span>");
    chkLbl->setTextFormat(Qt::RichText);
    checksLay->addWidget(chkLbl);

    for (const auto& [key, label] : CHECKS) {
        checksLay->addWidget(makeCheckRow(key, label));
    }
    checksLay->addStretch();
    splitter->addWidget(checksPanel);

    // Right: findings + feed
    auto* rightPanel = new QWidget;
    auto* rightLay   = new QVBoxLayout(rightPanel);
    rightLay->setContentsMargins(8, 0, 0, 0);
    rightLay->setSpacing(6);

    auto* findLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>FINDINGS</span>");
    findLbl->setTextFormat(Qt::RichText);
    rightLay->addWidget(findLbl);

    m_findingsList = new QListWidget;
    m_findingsList->setStyleSheet(R"(
        QListWidget {
            background: #060810; border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px; color: #cbd5e1; font-size: 12px;
        }
        QListWidget::item { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
        QListWidget::item:selected { background: rgba(180,74,255,0.08); }
    )");
    rightLay->addWidget(m_findingsList, 1);

    auto* feedLbl = new QLabel("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>SCAN LOG</span>");
    feedLbl->setTextFormat(Qt::RichText);
    rightLay->addWidget(feedLbl);
    m_feed = new TacticalTerminal(this);
    m_feed->setMaximumHeight(130);
    rightLay->addWidget(m_feed);

    splitter->addWidget(rightPanel);
    splitter->setSizes({300, 600});
    lay->addWidget(splitter, 1);

    m_feed->log("Counter-Intelligence engine ready", "SYSTEM");
    m_feed->log("Detects: MITM/ARP · SSL interception · DNS leak · rogue DHCP · traffic anomalies · OSINT exposure", "INFO");
}

QWidget* CounterIntelPage::makeCheckRow(const QString& key, const QString& description) {
    auto* row = new QWidget;
    row->setStyleSheet(
        "QWidget { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); "
        "border-radius: 6px; }"
    );
    auto* hlay = new QHBoxLayout(row);
    hlay->setContentsMargins(10, 8, 10, 8);
    hlay->setSpacing(10);

    auto* dot = new QLabel("●");
    dot->setStyleSheet("color: #334155; font-size: 10px; min-width: 12px; background: transparent; border: none;");
    hlay->addWidget(dot);

    auto* lbl = new QLabel(description);
    lbl->setStyleSheet("color: #64748b; font-size: 12px; background: transparent; border: none;");
    hlay->addWidget(lbl, 1);

    auto* result = new QLabel("—");
    result->setStyleSheet("color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; background: transparent; border: none;");
    hlay->addWidget(result);

    m_checks.append({key, dot, result});
    return row;
}

void CounterIntelPage::setCheckStatus(const QString& name, const QString& status, const QString& detail) {
    for (auto& chk : m_checks) {
        if (chk.name != name) continue;
        QString dotColor, resultColor;
        if (status == "RUNNING") {
            dotColor = "#fbbf24"; resultColor = "#fbbf24";
        } else if (status == "CLEAN") {
            dotColor = "#10b981"; resultColor = "#10b981";
        } else if (status == "ALERT") {
            dotColor = "#f43f5e"; resultColor = "#f43f5e";
        } else if (status == "WARN") {
            dotColor = "#ffb84d"; resultColor = "#ffb84d";
        } else {
            dotColor = "#334155"; resultColor = "#334155";
        }
        chk.statusDot->setStyleSheet(QString("color: %1; font-size: 10px; min-width: 12px; background: transparent; border: none;").arg(dotColor));
        chk.resultLabel->setStyleSheet(QString("color: %1; font-family: 'JetBrains Mono'; font-size: 10px; background: transparent; border: none;").arg(resultColor));
        chk.resultLabel->setText(detail.isEmpty() ? status : detail.left(24));
        break;
    }
}

void CounterIntelPage::startFullScan() {
    if (m_scanning) return;
    if (!m_ipc || !m_ipc->isConnected()) {
        m_feed->log("Daemon not connected — cannot start scan", "WARNING");
        return;
    }
    setScanningState(true);
    for (const auto& [key, _] : CHECKS) setCheckStatus(key, "RUNNING");
    m_findingsList->clear();
    m_scanReqId = m_ipc->call("counter_intel_full_scan");
    m_pollTimer->start();
    m_feed->log("Full counter-intelligence scan initiated", "INTEL");
}

void CounterIntelPage::setScanningState(bool scanning) {
    m_scanning = scanning;
    m_scanBtn->setEnabled(!scanning);
    m_scanBtn->setText(scanning ? "⏳ SCANNING…" : "▶ RUN FULL SCAN");
    m_statusLabel->setText(scanning ? "● SCAN IN PROGRESS" : "STANDBY — no scan running");
    m_statusLabel->setStyleSheet(scanning
        ? "color: #b44aff; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;"
        : "color: #334155; font-family: 'JetBrains Mono'; font-size: 10px; letter-spacing: 2px;");
}

void CounterIntelPage::pollStatus() {
    if (!m_ipc || !m_ipc->isConnected()) return;
    m_pollReqId = m_ipc->call("counter_intel_status");
}

void CounterIntelPage::onIpcResult(int id, QJsonObject result) {
    if (id == m_scanReqId || id == m_pollReqId) {
        // Check updates per detector
        QJsonObject checks = result.value("checks").toObject();
        for (const QString& key : checks.keys()) {
            QJsonObject chk = checks.value(key).toObject();
            QString status = chk.value("status").toString("PENDING");
            QString detail = chk.value("detail").toString();
            QString st = (status == "clean") ? "CLEAN" :
                         (status == "alert") ? "ALERT" :
                         (status == "warn")  ? "WARN"  :
                         (status == "running") ? "RUNNING" : "—";
            setCheckStatus(key, st, detail);
        }

        // New findings
        QJsonArray findings = result.value("findings").toArray();
        for (const auto& f : findings) addFinding(f.toObject());

        // Scan complete?
        if (result.value("complete").toBool()) {
            m_pollTimer->stop();
            setScanningState(false);
            int alertCount = result.value("alert_count").toInt(0);
            QString severity = result.value("max_severity").toString("none");
            m_feed->log(
                QString("Scan complete — %1 finding(s), max severity: %2").arg(alertCount).arg(severity.toUpper()),
                alertCount > 0 ? (severity == "critical" ? "CRITICAL" : "WARNING") : "SUCCESS"
            );
        }
    }
}

void CounterIntelPage::addFinding(const QJsonObject& finding) {
    QString sev   = finding.value("severity").toString("info");
    QString check = finding.value("check").toString();
    QString msg   = finding.value("message").toString();

    QString color = (sev == "critical") ? "#f43f5e" : (sev == "warning") ? "#ffb84d" : "#38bdf8";
    QString icon  = (sev == "critical") ? "⚠ " : (sev == "warning") ? "⚡ " : "ℹ ";

    auto* item = new QListWidgetItem(icon + "[" + check.toUpper() + "] " + msg);
    item->setForeground(QColor(color));
    item->setData(Qt::UserRole, finding.toVariantMap());
    m_findingsList->addItem(item);

    m_feed->log(msg, sev == "critical" ? "CRITICAL" : sev == "warning" ? "WARNING" : "INTEL");
}
