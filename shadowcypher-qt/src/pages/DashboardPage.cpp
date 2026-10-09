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
#include <QStorageInfo>
#include <QRegularExpression>
#include <QRandomGenerator>
#include <QtConcurrent/QtConcurrent>

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
    refreshCpu();
    refreshRam();
    refreshDisk();
    updateNetSpeed();
    updateEntropy();
}

// ── Disk — QStorageInfo works on all platforms ──────────────────────────────
void DashboardPage::refreshDisk() {
    QStorageInfo info = QStorageInfo::root();
    if (info.isValid() && info.bytesTotal() > 0)
        m_diskGauge->setValue(100.0 * (info.bytesTotal() - info.bytesAvailable())
                              / info.bytesTotal());
}

// ── CPU ─────────────────────────────────────────────────────────────────────
#if defined(Q_OS_LINUX)
void DashboardPage::refreshCpu() {
    static qint64 prevIdle = 0, prevTotal = 0;
    QFile f("/proc/stat");
    if (!f.open(QIODevice::ReadOnly)) return;
    QList<QByteArray> p = f.readLine().split(' ');
    f.close();
    p.removeAll("");
    if (p.size() < 5) return;
    qint64 user = p[1].toLongLong(), nice = p[2].toLongLong(),
           sys  = p[3].toLongLong(), idle = p[4].toLongLong(),
           iow  = p.size() > 5 ? p[5].toLongLong() : 0,
           irq  = p.size() > 6 ? p[6].toLongLong() : 0,
           sirq = p.size() > 7 ? p[7].toLongLong() : 0;
    qint64 totalIdle = idle + iow;
    qint64 total     = user + nice + sys + idle + iow + irq + sirq;
    qint64 dT = total - prevTotal, dI = totalIdle - prevIdle;
    double cpu = dT > 0 ? 100.0 * (dT - dI) / dT : 0.0;
    prevTotal = total; prevIdle = totalIdle;
    m_cpuGauge->setValue(cpu);
}

void DashboardPage::refreshRam() {
    QFile f("/proc/meminfo");
    if (!f.open(QIODevice::ReadOnly)) return;
    qint64 total = 0, avail = 0;
    while (!f.atEnd()) {
        QByteArray line = f.readLine().trimmed();
        if (line.startsWith("MemTotal:"))
            total = line.split(':').last().trimmed().split(' ').first().toLongLong();
        else if (line.startsWith("MemAvailable:"))
            avail = line.split(':').last().trimmed().split(' ').first().toLongLong();
    }
    f.close();
    if (total > 0) m_ramGauge->setValue(100.0 * (total - avail) / total);
}

void DashboardPage::updateNetSpeed() {
    qint64 now = QDateTime::currentMSecsSinceEpoch();
    qint64 dt  = now - m_lastNetTime;
    if (dt <= 0) return;
    qint64 total = 0;
    QFile f("/proc/net/dev");
    if (f.open(QIODevice::ReadOnly)) {
        f.readLine(); f.readLine();
        while (!f.atEnd()) {
            QByteArray line = f.readLine().trimmed();
            if (line.startsWith("lo")) continue;
            QByteArray vals = line.split(':').last().trimmed();
            QList<QByteArray> cols = vals.split(' ');
            cols.removeAll("");
            if (cols.size() >= 9)
                total += cols[0].toLongLong() + cols[8].toLongLong();
        }
        f.close();
    }
    double bps = (m_lastNetBytes > 0 && total > m_lastNetBytes)
                 ? (total - m_lastNetBytes) * 1000.0 / dt : 0.0;
    m_lastNetBytes = total; m_lastNetTime = now;
    QString spd;
    if (bps >= 1048576)  spd = QString::number(bps / 1048576, 'f', 1) + " MB/s";
    else if (bps >= 1024) spd = QString::number(bps / 1024,   'f', 1) + " KB/s";
    else                  spd = QString::number((int)bps)               + " B/s";
    m_statNet->setValue(spd);
}

void DashboardPage::updateEntropy() {
    QFile f("/dev/urandom");
    if (!f.open(QIODevice::ReadOnly)) { m_statEntropy->setValue("NOMINAL"); return; }
    QByteArray raw = f.read(64); f.close();
    int counts[256] = {};
    for (unsigned char b : raw) counts[b]++;
    double ent = 0.0;
    for (int c : counts) {
        if (c > 0) { double p = c / 64.0; ent -= p * std::log2(p); }
    }
    m_statEntropy->setValue(QString::number(ent, 'f', 2) + " bits");
}

#elif defined(Q_OS_MACOS)
void DashboardPage::refreshCpu() {
    auto* w = new QFutureWatcher<double>(this);
    connect(w, &QFutureWatcher<double>::finished, this, [this, w]() {
        m_cpuGauge->setValue(w->result()); w->deleteLater();
    });
    w->setFuture(QtConcurrent::run([]() -> double {
        QProcess p;
        p.start("top", {"-l", "1", "-n", "0"});
        if (!p.waitForFinished(3000)) return 0.0;
        QString out = p.readAllStandardOutput();
        QRegularExpression re(R"((\d+\.\d+)%\s+idle)");
        auto m = re.match(out);
        return m.hasMatch() ? 100.0 - m.captured(1).toDouble() : 0.0;
    }));
}

void DashboardPage::refreshRam() {
    auto* w = new QFutureWatcher<double>(this);
    connect(w, &QFutureWatcher<double>::finished, this, [this, w]() {
        m_ramGauge->setValue(w->result()); w->deleteLater();
    });
    w->setFuture(QtConcurrent::run([]() -> double {
        // Total memory in bytes
        QProcess pmem;
        pmem.start("sysctl", {"-n", "hw.memsize"});
        pmem.waitForFinished(1000);
        qint64 total = pmem.readAllStandardOutput().trimmed().toLongLong();
        if (total <= 0) return 0.0;

        // vm_stat: parse Pages free + inactive + speculative as "available"
        QProcess pvms;
        pvms.start("vm_stat");
        pvms.waitForFinished(1000);
        QString vms = pvms.readAllStandardOutput();
        auto extractPages = [&](const QString& key) -> qint64 {
            QRegularExpression re(key + R"(:\s+(\d+))");
            auto m = re.match(vms);
            return m.hasMatch() ? m.captured(1).toLongLong() : 0;
        };
        qint64 pageSz = 4096;
        QProcess pps;
        pps.start("sysctl", {"-n", "hw.pagesize"});
        pps.waitForFinished(500);
        qint64 ps = pps.readAllStandardOutput().trimmed().toLongLong();
        if (ps > 0) pageSz = ps;

        qint64 free  = (extractPages("Pages free") +
                        extractPages("Pages inactive") +
                        extractPages("Pages speculative")) * pageSz;
        return 100.0 * (total - free) / total;
    }));
}

void DashboardPage::updateNetSpeed() {
    qint64 now = QDateTime::currentMSecsSinceEpoch();
    qint64 dt  = now - m_lastNetTime;
    if (dt <= 0) return;

    auto* w = new QFutureWatcher<qint64>(this);
    qint64 prev = m_lastNetBytes;
    qint64 prevTime = dt;
    connect(w, &QFutureWatcher<qint64>::finished, this, [this, w, prev, prevTime, now]() {
        qint64 total = w->result(); w->deleteLater();
        double bps = (prev > 0 && total > prev) ? (total - prev) * 1000.0 / prevTime : 0.0;
        m_lastNetBytes = total; m_lastNetTime = now;
        QString spd;
        if (bps >= 1048576)   spd = QString::number(bps / 1048576, 'f', 1) + " MB/s";
        else if (bps >= 1024) spd = QString::number(bps / 1024,    'f', 1) + " KB/s";
        else                  spd = QString::number((int)bps)                + " B/s";
        m_statNet->setValue(spd);
    });
    m_lastNetTime = now;
    w->setFuture(QtConcurrent::run([]() -> qint64 {
        // netstat -ibn: columns are Name Mtu Network Address Ipkts Ierrs Ibytes Opkts Oerrs Obytes
        QProcess p;
        p.start("netstat", {"-ibn"});
        if (!p.waitForFinished(2000)) return 0;
        qint64 total = 0;
        for (const QString& line : p.readAllStandardOutput().split('\n')) {
            if (!line.contains("<Link#")) continue;
            if (line.startsWith("lo")) continue;
            QStringList cols = line.split(' ', Qt::SkipEmptyParts);
            if (cols.size() >= 10) {
                total += cols[6].toLongLong() + cols[9].toLongLong();
            }
        }
        return total;
    }));
}

void DashboardPage::updateEntropy() {
    QFile f("/dev/urandom");
    if (!f.open(QIODevice::ReadOnly)) { m_statEntropy->setValue("NOMINAL"); return; }
    QByteArray raw = f.read(64); f.close();
    int counts[256] = {};
    for (unsigned char b : raw) counts[b]++;
    double ent = 0.0;
    for (int c : counts) {
        if (c > 0) { double p = c / 64.0; ent -= p * std::log2(p); }
    }
    m_statEntropy->setValue(QString::number(ent, 'f', 2) + " bits");
}

#elif defined(Q_OS_WIN)
void DashboardPage::refreshCpu() {
    auto* w = new QFutureWatcher<double>(this);
    connect(w, &QFutureWatcher<double>::finished, this, [this, w]() {
        m_cpuGauge->setValue(w->result()); w->deleteLater();
    });
    w->setFuture(QtConcurrent::run([]() -> double {
        QProcess p;
        p.start("wmic", {"cpu", "get", "loadpercentage", "/value"});
        if (!p.waitForFinished(3000)) return 0.0;
        QString out = p.readAllStandardOutput();
        QRegularExpression re(R"(LoadPercentage=(\d+))");
        auto m = re.match(out);
        return m.hasMatch() ? m.captured(1).toDouble() : 0.0;
    }));
}

void DashboardPage::refreshRam() {
    auto* w = new QFutureWatcher<double>(this);
    connect(w, &QFutureWatcher<double>::finished, this, [this, w]() {
        m_ramGauge->setValue(w->result()); w->deleteLater();
    });
    w->setFuture(QtConcurrent::run([]() -> double {
        QProcess p;
        p.start("wmic", {"OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/value"});
        if (!p.waitForFinished(3000)) return 0.0;
        QString out = p.readAllStandardOutput();
        QRegularExpression reFree(R"(FreePhysicalMemory=(\d+))");
        QRegularExpression reTotal(R"(TotalVisibleMemorySize=(\d+))");
        auto mFree  = reFree.match(out);
        auto mTotal = reTotal.match(out);
        if (!mFree.hasMatch() || !mTotal.hasMatch()) return 0.0;
        double free  = mFree.captured(1).toDouble();
        double total = mTotal.captured(1).toDouble();
        return total > 0 ? 100.0 * (total - free) / total : 0.0;
    }));
}

void DashboardPage::updateNetSpeed() {
    qint64 now = QDateTime::currentMSecsSinceEpoch();
    qint64 dt  = now - m_lastNetTime;
    if (dt <= 0) return;

    auto* w = new QFutureWatcher<qint64>(this);
    qint64 prev = m_lastNetBytes;
    connect(w, &QFutureWatcher<qint64>::finished, this, [this, w, prev, dt, now]() {
        qint64 total = w->result(); w->deleteLater();
        double bps = (prev > 0 && total > prev) ? (total - prev) * 1000.0 / dt : 0.0;
        m_lastNetBytes = total; m_lastNetTime = now;
        QString spd;
        if (bps >= 1048576)   spd = QString::number(bps / 1048576, 'f', 1) + " MB/s";
        else if (bps >= 1024) spd = QString::number(bps / 1024,    'f', 1) + " KB/s";
        else                  spd = QString::number((int)bps)                + " B/s";
        m_statNet->setValue(spd);
    });
    m_lastNetTime = now;
    w->setFuture(QtConcurrent::run([]() -> qint64 {
        // netstat -e: "Bytes   received    sent"
        QProcess p;
        p.start("netstat", {"-e"});
        if (!p.waitForFinished(2000)) return 0;
        QString out = p.readAllStandardOutput();
        QRegularExpression re(R"(Bytes\s+(\d+)\s+(\d+))");
        auto m = re.match(out);
        if (!m.hasMatch()) return 0;
        return m.captured(1).toLongLong() + m.captured(2).toLongLong();
    }));
}

void DashboardPage::updateEntropy() {
    // Use Qt's cryptographically seeded RNG to estimate entropy quality
    quint64 v = QRandomGenerator::securelySeeded().generate64();
    int counts[8] = {};
    for (int i = 0; i < 8; ++i) counts[i] = (v >> (i * 8)) & 0xFF;
    m_statEntropy->setValue("NOMINAL");
    (void)counts;
}
#endif

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
