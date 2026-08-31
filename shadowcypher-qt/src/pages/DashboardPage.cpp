#include "DashboardPage.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QScrollArea>
#include <QLabel>
#include <QDateTime>
#include <QFile>
#include <QDir>
#include <QProcess>
#include <QNetworkInterface>
#include <random>
#include <cmath>

DashboardPage::DashboardPage(IpcClient* ipc, QWidget* parent)
    : QWidget(parent), m_ipc(ipc)
{
    buildUi();

    m_timer = new QTimer(this);
    m_timer->setInterval(1500);
    connect(m_timer, &QTimer::timeout, this, &DashboardPage::tick);
    m_timer->start();

    if (m_ipc) {
        connect(m_ipc, &IpcClient::resultReady, this, &DashboardPage::onIpcResult);
        connect(m_ipc, &IpcClient::connected, this, [this]() {
            m_terminal->log("Shadow daemon connected", "SUCCESS");
        });
        connect(m_ipc, &IpcClient::disconnected, this, [this]() {
            m_terminal->log("Shadow daemon offline — retrying…", "WARNING");
        });
    }

    m_terminal->log("ShadowCypher Qt6 operational. All systems ready.", "SYSTEM");
    m_lastNetTime = QDateTime::currentMSecsSinceEpoch();
}

void DashboardPage::buildUi() {
    auto* scroll = new QScrollArea(this);
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    scroll->setStyleSheet("QScrollArea { border: none; background: transparent; }");

    auto* root = new QWidget;
    auto* lay  = new QVBoxLayout(root);
    lay->setContentsMargins(20, 14, 20, 20);
    lay->setSpacing(14);

    // ── Header ──
    auto* headerRow = new QHBoxLayout;
    auto* titleLbl = new QLabel;
    titleLbl->setText("<span style='font-weight:900;font-size:16px;color:#00d4ff;letter-spacing:2px;'>SHADOW_NODE_HUD</span>");
    titleLbl->setTextFormat(Qt::RichText);
    headerRow->addWidget(titleLbl);
    headerRow->addStretch();
    m_statusLabel = new QLabel;
    m_statusLabel->setText("<span style='color:#10b981;font-weight:700;'>● ALL SYSTEMS NOMINAL</span>");
    m_statusLabel->setTextFormat(Qt::RichText);
    headerRow->addWidget(m_statusLabel);
    lay->addLayout(headerRow);

    // ── Gauge + Stats Row ──
    auto* gaugeRow = new QHBoxLayout;
    gaugeRow->setSpacing(20);

    // Gauges panel
    auto* gaugesBox = new QHBoxLayout;
    gaugesBox->setSpacing(15);
    m_cpuGauge  = new ArcGauge("CPU LOAD",  "%", QColor("#00ff9d"), 125, this);
    m_ramGauge  = new ArcGauge("MEMORY",    "%", QColor("#9966ff"), 125, this);
    m_diskGauge = new ArcGauge("DISK",      "%", QColor("#ff9900"), 125, this);

    auto* gaugesContainer = new QWidget;
    gaugesContainer->setStyleSheet(
        "QWidget { background: rgba(180,74,255,0.03); border: 1px solid rgba(180,74,255,0.12); "
        "border-radius: 12px; padding: 8px; }"
    );
    auto* gaugesLayout = new QHBoxLayout(gaugesContainer);
    gaugesLayout->setSpacing(15);
    gaugesLayout->addWidget(m_cpuGauge);
    gaugesLayout->addWidget(m_ramGauge);
    gaugesLayout->addWidget(m_diskGauge);
    gaugeRow->addWidget(gaugesContainer);

    // Stats grid
    auto* statsGrid = new QGridLayout;
    statsGrid->setSpacing(8);
    m_statAi        = new MiniStat("AI_CORE",            "NOMINAL",      "#8b5cf6", this);
    m_statMissions  = new MiniStat("ACTIVE_MISSIONS",    "0",            "#f43f5e", this);
    m_statUptime    = new MiniStat("MISSION_UPTIME",     "0:00:00",      "#38bdf8", this);
    m_statStealth   = new MiniStat("STEALTH_SIGNATURE",  "CHECKING…",    "#fbbf24", this);
    m_statThreats   = new MiniStat("THREAT_INTEL",       "0 HITS",       "#f97316", this);
    m_statIntegrity = new MiniStat("CORE_INTEGRITY",     "VERIFIED",     "#10b981", this);
    m_statRelay     = new MiniStat("SHADOW_PLANE",       "CONNECTING…",  "#0ea5e9", this);
    m_statNet       = new MiniStat("GHOST_IO_SPEED",     "0 B/s",        "#64748b", this);
    m_statEntropy   = new MiniStat("ENTROPY_SIGNATURE",  "NOMINAL",      "#00ff9d", this);

    QList<MiniStat*> stats = {
        m_statAi, m_statMissions, m_statUptime,
        m_statStealth, m_statThreats, m_statIntegrity,
        m_statRelay, m_statNet, m_statEntropy
    };
    for (int i = 0; i < stats.size(); ++i)
        statsGrid->addWidget(stats[i], i / 3, i % 3);

    auto* statsContainer = new QWidget;
    statsContainer->setLayout(statsGrid);
    gaugeRow->addWidget(statsContainer);
    lay->addLayout(gaugeRow);

    // ── Mission Telemetry ──
    auto* feedLbl = new QLabel;
    feedLbl->setText("<span style='font-weight:800;color:#94a3b8;font-size:11px;letter-spacing:2px;'>MISSION TELEMETRY</span>");
    feedLbl->setTextFormat(Qt::RichText);
    lay->addWidget(feedLbl);

    m_terminal = new TacticalTerminal(this);
    m_terminal->setMinimumHeight(180);
    lay->addWidget(m_terminal);

    scroll->setWidget(root);
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->addWidget(scroll);
}

void DashboardPage::tick() {
    if (!isVisible()) return;
    refreshLocalMetrics();
    if (m_ipc && m_ipc->isConnected()) requestDaemonStats();
}

void DashboardPage::refreshLocalMetrics() {
    // CPU — read /proc/stat
    static qint64 prevIdle = 0, prevTotal = 0;
    QFile cpuFile("/proc/stat");
    if (cpuFile.open(QIODevice::ReadOnly)) {
        QByteArray line = cpuFile.readLine();
        cpuFile.close();
        QList<QByteArray> parts = line.split(' ');
        parts.removeAll("");
        if (parts.size() >= 5) {
            qint64 user = parts[1].toLongLong();
            qint64 nice = parts[2].toLongLong();
            qint64 system = parts[3].toLongLong();
            qint64 idle = parts[4].toLongLong();
            qint64 iowait = parts.size() > 5 ? parts[5].toLongLong() : 0;
            qint64 totalIdle  = idle + iowait;
            qint64 total      = user + nice + system + idle + iowait +
                               (parts.size() > 6 ? parts[6].toLongLong() : 0) +
                               (parts.size() > 7 ? parts[7].toLongLong() : 0);
            qint64 dTotal = total - prevTotal;
            qint64 dIdle  = totalIdle - prevIdle;
            double cpu = dTotal > 0 ? 100.0 * (dTotal - dIdle) / dTotal : 0.0;
            prevTotal = total;
            prevIdle  = totalIdle;
            m_cpuGauge->setValue(cpu);
        }
    }

    // RAM — /proc/meminfo
    QFile memFile("/proc/meminfo");
    if (memFile.open(QIODevice::ReadOnly)) {
        qint64 total = 0, avail = 0;
        while (!memFile.atEnd()) {
            QByteArray line = memFile.readLine().trimmed();
            if (line.startsWith("MemTotal:"))
                total = line.split(':').last().trimmed().split(' ').first().toLongLong();
            else if (line.startsWith("MemAvailable:"))
                avail = line.split(':').last().trimmed().split(' ').first().toLongLong();
        }
        memFile.close();
        if (total > 0)
            m_ramGauge->setValue(100.0 * (total - avail) / total);
    }

    // Disk — /proc
    QProcess df;
    df.start("df", {"-k", "--output=size,avail", "/"});
    df.waitForFinished(500);
    QString dfOut = df.readAllStandardOutput();
    QStringList dfLines = dfOut.split('\n', Qt::SkipEmptyParts);
    if (dfLines.size() >= 2) {
        QStringList parts = dfLines[1].trimmed().split(' ', Qt::SkipEmptyParts);
        if (parts.size() >= 2) {
            qint64 sz = parts[0].toLongLong();
            qint64 av = parts[1].toLongLong();
            if (sz > 0) m_diskGauge->setValue(100.0 * (sz - av) / sz);
        }
    }

    updateNetSpeed();
    updateEntropy();
}

void DashboardPage::updateNetSpeed() {
    qint64 now = QDateTime::currentMSecsSinceEpoch();
    qint64 dt  = now - m_lastNetTime;
    if (dt <= 0) return;

    qint64 total = 0;
    for (const auto& iface : QNetworkInterface::allInterfaces()) {
        auto stats = iface.addressEntries();
        (void)stats; // just need to list interfaces for now
    }

    // Read /proc/net/dev for byte totals
    QFile netDev("/proc/net/dev");
    if (netDev.open(QIODevice::ReadOnly)) {
        netDev.readLine(); netDev.readLine(); // skip headers
        while (!netDev.atEnd()) {
            QByteArray line = netDev.readLine().trimmed();
            if (line.startsWith("lo")) continue;
            QByteArray vals = line.split(':').last().trimmed();
            QList<QByteArray> cols = vals.split(' ');
            cols.removeAll("");
            if (cols.size() >= 9) {
                total += cols[0].toLongLong() + cols[8].toLongLong(); // rx + tx
            }
        }
        netDev.close();
    }

    double bps = (m_lastNetBytes > 0 && total > m_lastNetBytes)
                 ? (total - m_lastNetBytes) * 1000.0 / dt
                 : 0.0;
    m_lastNetBytes = total;
    m_lastNetTime  = now;

    QString spd;
    if (bps >= 1'048'576)     spd = QString::number(bps / 1'048'576, 'f', 1) + " MB/s";
    else if (bps >= 1024)     spd = QString::number(bps / 1024,      'f', 1) + " KB/s";
    else                      spd = QString::number(static_cast<int>(bps))    + " B/s";
    m_statNet->setValue(spd);
}

void DashboardPage::updateEntropy() {
    // Shannon entropy of 64 random bytes from /dev/urandom
    QFile urandom("/dev/urandom");
    if (!urandom.open(QIODevice::ReadOnly)) {
        m_statEntropy->setValue("NOMINAL");
        return;
    }
    QByteArray raw = urandom.read(64);
    urandom.close();

    int counts[256] = {};
    for (unsigned char b : raw) counts[b]++;
    double ent = 0.0;
    for (int c : counts) {
        if (c > 0) {
            double p = c / 64.0;
            ent -= p * std::log2(p);
        }
    }
    m_statEntropy->setValue(QString::number(ent, 'f', 2) + " bits");
}

void DashboardPage::requestDaemonStats() {
    m_ipc->call("get_tactical_summary");
}

void DashboardPage::onIpcResult(int /*id*/, QJsonObject result) {
    if (result.contains("active_missions"))
        m_statMissions->setValue(QString::number(result["active_missions"].toInt()));
    if (result.contains("uptime"))
        m_statUptime->setValue(result["uptime"].toString());
    if (result.contains("threat_hits"))
        m_statThreats->setValue(QString::number(result["threat_hits"].toInt()) + " HITS");
    if (result.contains("integrity"))
        m_statIntegrity->setValue(result["integrity"].toBool() ? "VERIFIED" : "TAMPERED");
    if (result.contains("stealth_active"))
        m_statStealth->setValue(result["stealth_active"].toBool() ? "ACTIVE" : "EXPOSED");
    if (result.contains("relay_connected"))
        m_statRelay->setValue(result["relay_connected"].toBool() ? "SECURE" : "OFFLINE");
}
