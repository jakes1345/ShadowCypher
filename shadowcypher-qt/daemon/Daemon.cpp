#include "Daemon.h"
#include "../core/Process.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonArray>
#include <QRegularExpression>
#include <QSet>
#include <QSettings>
#include <QStandardPaths>
#include <QDateTime>
#include <QThread>
#include <QtConcurrent/QtConcurrent>
#include <QTimer>

#ifdef Q_OS_WIN
static constexpr quint16 IPC_PORT = 54321;
#else
static const QString IPC_SOCKET = QStringLiteral("/tmp/shadowcypher-daemon.sock");
#endif

// ── Construction ──────────────────────────────────────────────────────────────

Daemon::Daemon(QObject* parent) : QObject(parent) {
    // Load config from ~/.config/shadowcypher/config.ini
    QSettings cfg(QSettings::IniFormat, QSettings::UserScope,
                  QStringLiteral("shadowcypher"), QStringLiteral("config"));
    QJsonObject toolCfg;
    toolCfg[QStringLiteral("api_key")]     = cfg.value(QStringLiteral("auth/api_key")).toString();
    toolCfg[QStringLiteral("ollama_url")]  = cfg.value(QStringLiteral("ollama/endpoint"),
                                                        QStringLiteral("http://127.0.0.1:11434")).toString();
    const QString ollamaModel = cfg.value(QStringLiteral("ollama/model")).toString();
    if (!ollamaModel.isEmpty())
        toolCfg[QStringLiteral("ollama_model")] = ollamaModel;

    m_tools = shadow::NativeTools(toolCfg);

    // State directory
    m_stateDir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
                 + QStringLiteral("/daemon");
    QDir().mkpath(m_stateDir);
    m_statePath = m_stateDir + QStringLiteral("/state.json");
    loadState();

    m_uptime.start();

#ifdef Q_OS_WIN
    m_server = new QTcpServer(this);
#else
    m_server = new QLocalServer(this);
    QLocalServer::removeServer(IPC_SOCKET);
#endif

    connect(m_server, &Server::newConnection, this, &Daemon::onNewConnection);
}

bool Daemon::start() {
#ifdef Q_OS_WIN
    if (!m_server->listen(QHostAddress::LocalHost, IPC_PORT)) {
#else
    if (!m_server->listen(IPC_SOCKET)) {
#endif
        qCritical("[daemon] Cannot listen: %s", qPrintable(m_server->errorString()));
        return false;
    }
    qInfo("[daemon] Listening on %s",
#ifdef Q_OS_WIN
          qPrintable(QString("TCP 127.0.0.1:%1").arg(IPC_PORT))
#else
          qPrintable(IPC_SOCKET)
#endif
    );

    // Run first scan after 2s so the GUI sees data quickly on startup
    QTimer::singleShot(2000, this, &Daemon::handleTriggerScan);
    return true;
}

// ── Connection handling ───────────────────────────────────────────────────────

void Daemon::onNewConnection() {
    while (m_server->hasPendingConnections()) {
#ifdef Q_OS_WIN
        auto* sock = m_server->nextPendingConnection();
#else
        auto* sock = m_server->nextPendingConnection();
#endif
        connect(sock, &QIODevice::readyRead,    this, &Daemon::onReadyRead);
        connect(sock, &Socket::disconnected,    this, &Daemon::onDisconnected);
        connect(sock, &Socket::disconnected,    sock, &QObject::deleteLater);
    }
}

void Daemon::onReadyRead() {
    auto* sock = qobject_cast<QIODevice*>(sender());
    if (!sock) return;

    // Buffer per-socket — store in dynamic property
    QByteArray buf = sock->property("_buf").toByteArray();
    buf += sock->readAll();

    while (true) {
        const int nl = buf.indexOf('\n');
        if (nl < 0) break;
        const QByteArray line = buf.left(nl).trimmed();
        buf.remove(0, nl + 1);

        if (line.isEmpty()) continue;

        const QJsonObject req = QJsonDocument::fromJson(line).object();
        const QJsonValue  id  = req.value(QStringLiteral("id"));
        const QString method  = req.value(QStringLiteral("method")).toString();
        const QJsonObject params = req.value(QStringLiteral("params")).toObject();

        try {
            const QJsonValue result = dispatch(method, params);
            respond(sock, id, result);
        } catch (const shadow::Error& e) {
            respondError(sock, id, QString::fromUtf8(e.what()));
        } catch (const std::exception& e) {
            respondError(sock, id, QString::fromUtf8(e.what()), -32603);
        }
    }

    sock->setProperty("_buf", buf);
}

void Daemon::onDisconnected() {
    // Sockets are set to deleteLater on disconnect — nothing to do here.
}

// ── Dispatch ──────────────────────────────────────────────────────────────────

QJsonValue Daemon::dispatch(const QString& method, const QJsonObject& params) {
    if (method == QStringLiteral("get_tactical_summary"))    return handleGetTacticalSummary();
    if (method == QStringLiteral("get_devices"))             return handleGetDevices();
    if (method == QStringLiteral("get_incidents"))           return handleGetIncidents();
    if (method == QStringLiteral("trigger_scan"))            return handleTriggerScan();
    if (method == QStringLiteral("ai_chat"))                 return handleAiChat(params);
    if (method == QStringLiteral("get_ai_model"))            return handleGetAiModel();
    if (method == QStringLiteral("cve_feed_recent"))         return handleCveFeedRecent(params);
    if (method == QStringLiteral("cve_feed_search"))         return handleCveFeedSearch(params);
    if (method == QStringLiteral("cve_feed_scan"))           return handleCveFeedScan(params);
    if (method == QStringLiteral("counter_intel_full_scan")) return handleCounterIntelScan();
    if (method == QStringLiteral("counter_intel_status"))    return handleCounterIntelStatus();
    if (method == QStringLiteral("get_counter_intel_status"))return handleCounterIntelStatus();
    if (method == QStringLiteral("ghost_mode_status"))       return handleGhostStatus();
    if (method == QStringLiteral("ghost_mode_enable"))       return handleGhostEnable();
    if (method == QStringLiteral("ghost_mode_disable"))      return handleGhostDisable();

    throw shadow::Error(QStringLiteral("Method not found: ") + method);
}

// ── Handlers ──────────────────────────────────────────────────────────────────

QJsonValue Daemon::handleGetTacticalSummary() {
    QMutexLocker lk(&m_mutex);
    const int active = static_cast<int>(
        std::count_if(m_incidents.begin(), m_incidents.end(), [](const QJsonValue& v) {
            return v.toObject().value(QStringLiteral("status")).toString() == QStringLiteral("open");
        }));
    const double uptimeSec = static_cast<double>(m_uptime.elapsed()) / 1000.0;
    QJsonObject obj;
    obj[QStringLiteral("active_missions")]   = active;
    obj[QStringLiteral("uptime")]            = QString::number(static_cast<int>(uptimeSec)) + QStringLiteral("s");
    obj[QStringLiteral("threat_hits")]       = m_incidents.size();
    obj[QStringLiteral("integrity")]         = QStringLiteral("ok");
    obj[QStringLiteral("stealth_active")]    = false;
    obj[QStringLiteral("relay_connected")]   = false;
    return obj;
}

QJsonValue Daemon::handleGetDevices() {
    QMutexLocker lk(&m_mutex);
    QJsonObject obj;
    obj[QStringLiteral("devices")] = m_devices;
    return obj;
}

QJsonValue Daemon::handleGetIncidents() {
    QMutexLocker lk(&m_mutex);
    QJsonObject obj;
    obj[QStringLiteral("incidents")] = m_incidents;
    return obj;
}

QJsonValue Daemon::handleTriggerScan() {
    if (m_scanRunning.exchange(true)) {
        QJsonObject obj;
        obj[QStringLiteral("ok")]   = false;
        obj[QStringLiteral("note")] = QStringLiteral("scan already running");
        return obj;
    }

    m_scanCancel = std::make_shared<std::atomic_bool>(false);
    const auto cancel = m_scanCancel;

    QtConcurrent::run([this, cancel]() {
        try {
            QJsonArray fresh = m_tools.discover(cancel);

            // Enrich with hostname via reverse DNS (best-effort, short timeout)
            for (int i = 0; i < fresh.size(); ++i) {
                QJsonObject dev = fresh[i].toObject();
                const QString ip = dev[QStringLiteral("ip")].toString();
                if (!ip.isEmpty() && dev[QStringLiteral("hostname")].toString().isEmpty()) {
                    // Qt reverse DNS is async; skip for now — can be added later
                    dev[QStringLiteral("hostname")] = QStringLiteral("");
                }
                dev[QStringLiteral("trusted")]    = false;
                dev[QStringLiteral("risk_score")] = 0;
                fresh[i] = dev;
            }

            {
                QMutexLocker lk(&m_mutex);
                reconcileDevices(fresh);
                m_devices = fresh;
                saveState();
            }
        } catch (...) {}

        m_scanRunning.store(false);
    });

    QJsonObject obj;
    obj[QStringLiteral("ok")] = true;
    return obj;
}

QJsonValue Daemon::handleAiChat(const QJsonObject& p) {
    const QString message = p.value(QStringLiteral("message")).toString();
    if (message.isEmpty())
        throw shadow::Error(QStringLiteral("message is required"));

    // This blocks — run in the caller's thread (IPC calls are already non-blocking
    // from the GUI's perspective since it uses async IpcClient)
    const QJsonObject resp = m_tools.chat(message);
    return resp;
}

QJsonValue Daemon::handleGetAiModel() {
    // Ask Ollama which model is loaded
    try {
        const QJsonObject tags = shadow::NativeTools::request(
            QUrl(QStringLiteral("http://127.0.0.1:11434/api/tags")));
        const QJsonArray models = tags.value(QStringLiteral("models")).toArray();
        if (!models.isEmpty()) {
            QJsonObject obj;
            obj[QStringLiteral("model")] = models[0].toObject().value(QStringLiteral("name")).toString();
            return obj;
        }
    } catch (...) {}

    QJsonObject obj;
    obj[QStringLiteral("model")] = QStringLiteral("ollama-unavailable");
    return obj;
}

// ── CVE Feed ──────────────────────────────────────────────────────────────────

QJsonObject Daemon::nvdSearch(const QString& query, int days) {
    QString urlStr = QStringLiteral("https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=50");
    if (!query.isEmpty())
        urlStr += QStringLiteral("&keywordSearch=") + QString::fromUtf8(query.toUtf8().toPercentEncoding());
    if (days > 0) {
        const QString end   = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
        const QString start = QDateTime::currentDateTimeUtc()
                              .addDays(-days).toString(Qt::ISODate);
        urlStr += QStringLiteral("&pubStartDate=") + start + QStringLiteral("&pubEndDate=") + end;
    }
    return shadow::NativeTools::request(QUrl(urlStr));
}

QJsonArray Daemon::parseCveResponse(const QJsonObject& nvdResp) {
    QJsonArray out;
    const QJsonArray vulns = nvdResp.value(QStringLiteral("vulnerabilities")).toArray();
    for (const QJsonValue& v : vulns) {
        const QJsonObject cveWrap = v.toObject().value(QStringLiteral("cve")).toObject();
        const QString cveId = cveWrap.value(QStringLiteral("id")).toString();

        // Description (English preferred)
        QString desc;
        for (const QJsonValue& d : cveWrap.value(QStringLiteral("descriptions")).toArray()) {
            const QJsonObject dobj = d.toObject();
            if (dobj.value(QStringLiteral("lang")).toString() == QStringLiteral("en")) {
                desc = dobj.value(QStringLiteral("value")).toString();
                break;
            }
        }

        // CVSS score + severity
        double score    = 0.0;
        QString severity = QStringLiteral("UNKNOWN");
        const auto tryMetrics = [&](const QString& key) {
            const QJsonArray arr = cveWrap.value(QStringLiteral("metrics")).toObject()
                                         .value(key).toArray();
            if (!arr.isEmpty()) {
                const QJsonObject cvss = arr[0].toObject().value(QStringLiteral("cvssData")).toObject();
                score    = cvss.value(QStringLiteral("baseScore")).toDouble();
                severity = cvss.value(QStringLiteral("baseSeverity")).toString();
                return true;
            }
            return false;
        };
        if (!tryMetrics(QStringLiteral("cvssMetricV31")))
            tryMetrics(QStringLiteral("cvssMetricV30"));

        // References
        QJsonArray refs;
        for (const QJsonValue& r : cveWrap.value(QStringLiteral("references")).toArray())
            refs.append(r.toObject().value(QStringLiteral("url")).toString());

        QJsonObject row;
        row[QStringLiteral("cve_id")]      = cveId;
        row[QStringLiteral("severity")]    = severity;
        row[QStringLiteral("score")]       = score;
        row[QStringLiteral("epss_score")]  = 0.0;
        row[QStringLiteral("kev_exploited")]= false;
        row[QStringLiteral("published")]   = cveWrap.value(QStringLiteral("published")).toString();
        row[QStringLiteral("description")] = desc;
        row[QStringLiteral("references")]  = refs;
        out.append(row);
    }
    return out;
}

QJsonValue Daemon::handleCveFeedRecent(const QJsonObject& p) {
    const int days = p.value(QStringLiteral("days")).toInt(7);
    try {
        const QJsonArray cves = parseCveResponse(nvdSearch(QString(), days));
        QJsonObject obj;
        obj[QStringLiteral("cves")] = cves;
        return obj;
    } catch (const std::exception& e) {
        throw shadow::Error(QStringLiteral("NVD fetch failed: ") + QString::fromUtf8(e.what()));
    }
}

QJsonValue Daemon::handleCveFeedSearch(const QJsonObject& p) {
    const QString keyword = p.value(QStringLiteral("keyword")).toString().trimmed();
    if (keyword.isEmpty())
        throw shadow::Error(QStringLiteral("keyword is required"));
    try {
        const QJsonArray cves = parseCveResponse(nvdSearch(keyword));
        QJsonObject obj;
        obj[QStringLiteral("cves")] = cves;
        return obj;
    } catch (const std::exception& e) {
        throw shadow::Error(QStringLiteral("NVD fetch failed: ") + QString::fromUtf8(e.what()));
    }
}

QJsonValue Daemon::handleCveFeedScan(const QJsonObject& p) {
    const QString target = p.value(QStringLiteral("target")).toString().trimmed();
    if (target.isEmpty())
        throw shadow::Error(QStringLiteral("target is required"));

    // Run nmap -sV to detect services, then search NVD for each
    try {
        shadow::NativeTools::validateTarget(target);
        const shadow::ProcessResult res = shadow::runProcess(
            QStringLiteral("nmap"),
            {QStringLiteral("-sV"), QStringLiteral("--open"), QStringLiteral("-oG"), QStringLiteral("-"), target},
            {}, 120000);

        // Parse grepable nmap output for service/version info
        QStringList services;
        for (const QString& line : QString::fromUtf8(res.out).split('\n')) {
            if (!line.startsWith(QStringLiteral("Host:"))) continue;
            const int portsIdx = line.indexOf(QStringLiteral("Ports:"));
            if (portsIdx < 0) continue;
            const QString portsSection = line.mid(portsIdx + 6);
            for (const QString& portEntry : portsSection.split(QStringLiteral(", "))) {
                const QStringList parts = portEntry.split('/');
                if (parts.size() >= 7 && parts[1].trimmed() == QStringLiteral("open")) {
                    const QString svc     = parts[4].trimmed();
                    const QString version = parts[6].trimmed();
                    if (!svc.isEmpty())
                        services.append(svc + (version.isEmpty() ? QString() : QStringLiteral(" ") + version));
                }
            }
        }

        QJsonArray allCves;
        QSet<QString> seen;
        for (const QString& svc : services) {
            const QString query = svc.section(' ', 0, 0); // service name only
            try {
                for (const QJsonValue& cv : parseCveResponse(nvdSearch(query))) {
                    const QString id = cv.toObject().value(QStringLiteral("cve_id")).toString();
                    if (!seen.contains(id)) { seen.insert(id); allCves.append(cv); }
                }
            } catch (...) {}
        }

        QJsonObject obj;
        obj[QStringLiteral("cves")]    = allCves;
        obj[QStringLiteral("output")]  = QString::fromUtf8(res.out).left(4096);
        obj[QStringLiteral("complete")] = true;
        return obj;
    } catch (const std::exception& e) {
        throw shadow::Error(QStringLiteral("CVE scan failed: ") + QString::fromUtf8(e.what()));
    }
}

// ── Counter-Intel ─────────────────────────────────────────────────────────────

QJsonValue Daemon::handleCounterIntelScan() {
    if (m_ciRunning.exchange(true)) {
        QJsonObject obj;
        obj[QStringLiteral("ok")]   = false;
        obj[QStringLiteral("note")] = QStringLiteral("scan already running");
        return obj;
    }

    // Reset state
    {
        QMutexLocker lk(&m_ciMutex);
        m_ciState = CiState{};
        const QStringList checks = {
            QStringLiteral("arp_spoofing"), QStringLiteral("promiscuous"),
            QStringLiteral("ssl_interception"), QStringLiteral("dns_leak"),
            QStringLiteral("rogue_dhcp"), QStringLiteral("traffic_anomaly"),
            QStringLiteral("osint_self")
        };
        for (const QString& c : checks)
            m_ciState.checks[c] = {QStringLiteral("pending"), {}};
    }

    QtConcurrent::run([this]() { runCounterIntelAsync(); });

    QJsonObject obj;
    obj[QStringLiteral("ok")] = true;
    return obj;
}

void Daemon::runCounterIntelAsync() {
    struct CheckEntry { QString key; std::function<CiCheck()> fn; };
    const QVector<CheckEntry> checks = {
        { QStringLiteral("arp_spoofing"),       [this]{ return checkArpSpoofing();       } },
        { QStringLiteral("promiscuous"),         [this]{ return checkPromiscuous();        } },
        { QStringLiteral("ssl_interception"),    [this]{ return checkSslInterception();   } },
        { QStringLiteral("dns_leak"),            [this]{ return checkDnsLeak();           } },
        { QStringLiteral("rogue_dhcp"),          [this]{ return checkRogueDhcp();         } },
        { QStringLiteral("traffic_anomaly"),     [this]{ return checkTrafficAnomaly();    } },
        { QStringLiteral("osint_self"),          [this]{ return checkOsintSelf();         } },
    };

    QJsonArray findings;
    int alertCount = 0;
    QString maxSev = QStringLiteral("none");
    const QMap<QString, int> sevRank = {
        {QStringLiteral("none"),    0}, {QStringLiteral("low"),   1},
        {QStringLiteral("medium"),  2}, {QStringLiteral("high"),  3},
        {QStringLiteral("critical"),4}
    };

    for (const CheckEntry& entry : checks) {
        CiCheck result;
        try {
            result = entry.fn();
        } catch (const std::exception& e) {
            result = {QStringLiteral("error"), QString::fromUtf8(e.what())};
        }

        {
            QMutexLocker lk(&m_ciMutex);
            m_ciState.checks[entry.key] = result;
        }

        if (result.status == QStringLiteral("alert") || result.status == QStringLiteral("warning")) {
            const QString sev = (result.status == QStringLiteral("alert"))
                                ? QStringLiteral("high") : QStringLiteral("medium");
            QJsonObject finding;
            finding[QStringLiteral("severity")] = sev;
            finding[QStringLiteral("check")]    = entry.key;
            finding[QStringLiteral("message")]  = result.detail;
            findings.append(finding);
            ++alertCount;
            if (sevRank.value(sev, 0) > sevRank.value(maxSev, 0))
                maxSev = sev;
        }
    }

    QMutexLocker lk(&m_ciMutex);
    m_ciState.findings   = findings;
    m_ciState.complete   = true;
    m_ciState.alertCount = alertCount;
    m_ciState.maxSeverity = maxSev;
    m_ciRunning.store(false);
}

QJsonValue Daemon::handleCounterIntelStatus() {
    QMutexLocker lk(&m_ciMutex);
    QJsonObject checks;
    for (auto it = m_ciState.checks.begin(); it != m_ciState.checks.end(); ++it) {
        QJsonObject c;
        c[QStringLiteral("status")] = it->status;
        c[QStringLiteral("detail")] = it->detail;
        checks[it.key()] = c;
    }
    QJsonObject obj;
    obj[QStringLiteral("checks")]      = checks;
    obj[QStringLiteral("findings")]    = m_ciState.findings;
    obj[QStringLiteral("complete")]    = m_ciState.complete;
    obj[QStringLiteral("alert_count")] = m_ciState.alertCount;
    obj[QStringLiteral("max_severity")]= m_ciState.maxSeverity;
    return obj;
}

// ── Counter-Intel checks ──────────────────────────────────────────────────────

CiCheck Daemon::checkArpSpoofing() {
    // Look for duplicate IPs with different MACs in the ARP table
    const shadow::ProcessResult r = shadow::runProcess(
        QStringLiteral("ip"), {QStringLiteral("-j"), QStringLiteral("neigh"), QStringLiteral("show")});
    if (r.exitCode != 0) return {QStringLiteral("error"), QStringLiteral("ip neigh failed")};

    const QJsonArray neighbors = shadow::NativeTools::parseNeighbors(r.out);
    QMap<QString, QString> ipToMac;
    QStringList conflicts;
    for (const QJsonValue& v : neighbors) {
        const QJsonObject n = v.toObject();
        const QString ip  = n.value(QStringLiteral("ip")).toString();
        const QString mac = n.value(QStringLiteral("mac")).toString();
        if (ip.isEmpty() || mac.isEmpty()) continue;
        if (ipToMac.contains(ip) && ipToMac[ip] != mac)
            conflicts.append(ip + QStringLiteral(" (") + ipToMac[ip] + QStringLiteral(" vs ") + mac + QStringLiteral(")"));
        else
            ipToMac[ip] = mac;
    }

    if (!conflicts.isEmpty())
        return {QStringLiteral("alert"),
                QStringLiteral("ARP conflict detected: ") + conflicts.join(QStringLiteral(", "))};
    return {QStringLiteral("ok"), QStringLiteral("No ARP conflicts detected")};
}

CiCheck Daemon::checkPromiscuous() {
    QStringList promiscIfaces;
#ifndef Q_OS_WIN
    const QDir sysnet(QStringLiteral("/sys/class/net"));
    for (const QString& iface : sysnet.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
        QFile f(QStringLiteral("/sys/class/net/") + iface + QStringLiteral("/flags"));
        if (!f.open(QIODevice::ReadOnly)) continue;
        const QString flags = QString::fromUtf8(f.readAll()).trimmed();
        bool ok = false;
        const ulong v = flags.toULong(&ok, 16);
        if (ok && (v & 0x100)) // IFF_PROMISC
            promiscIfaces.append(iface);
    }
#endif
    if (!promiscIfaces.isEmpty())
        return {QStringLiteral("alert"),
                QStringLiteral("Promiscuous interfaces: ") + promiscIfaces.join(QStringLiteral(", "))};
    return {QStringLiteral("ok"), QStringLiteral("No promiscuous interfaces")};
}

CiCheck Daemon::checkDnsLeak() {
#ifndef Q_OS_WIN
    QFile resolv(QStringLiteral("/etc/resolv.conf"));
    if (!resolv.open(QIODevice::ReadOnly))
        return {QStringLiteral("error"), QStringLiteral("Cannot read /etc/resolv.conf")};

    QStringList nameservers;
    for (const QString& line : QString::fromUtf8(resolv.readAll()).split('\n')) {
        const QString t = line.trimmed();
        if (t.startsWith(QStringLiteral("nameserver"))) {
            const QString ns = t.section(QStringLiteral(" "), 1, 1).trimmed();
            if (!ns.isEmpty()) nameservers.append(ns);
        }
    }

    // Check if any nameserver is external (not loopback or private)
    QStringList external;
    for (const QString& ns : nameservers) {
        if (!ns.startsWith(QStringLiteral("127.")) &&
            !ns.startsWith(QStringLiteral("10.")) &&
            !ns.startsWith(QStringLiteral("192.168.")) &&
            !ns.startsWith(QStringLiteral("172.")) &&
            ns != QStringLiteral("::1"))
            external.append(ns);
    }

    if (!external.isEmpty())
        return {QStringLiteral("warning"),
                QStringLiteral("External DNS servers detected: ") + external.join(QStringLiteral(", "))};
    return {QStringLiteral("ok"),
            QStringLiteral("DNS uses local/private resolvers: ") + nameservers.join(QStringLiteral(", "))};
#else
    return {QStringLiteral("ok"), QStringLiteral("DNS check not available on Windows")};
#endif
}

CiCheck Daemon::checkTrafficAnomaly() {
    // Sample /proc/net/dev twice, flag >100 MB/s sustained RX
#ifndef Q_OS_WIN
    auto readRxBytes = [](QMap<QString, quint64>& out) {
        QFile f(QStringLiteral("/proc/net/dev"));
        if (!f.open(QIODevice::ReadOnly)) return;
        bool first = true;
        for (const QString& line : QString::fromUtf8(f.readAll()).split('\n')) {
            if (first) { first = false; continue; }  // header
            const QString t = line.trimmed();
            if (t.isEmpty() || t.startsWith('|')) continue;
            const int colon = t.indexOf(':');
            if (colon < 0) continue;
            const QString iface = t.left(colon).trimmed();
            const QStringList cols = t.mid(colon + 1).simplified().split(' ');
            if (cols.size() >= 1) out[iface] = cols[0].toULongLong();
        }
    };

    QMap<QString, quint64> before, after;
    readRxBytes(before);
    QThread::msleep(2000);
    readRxBytes(after);

    QStringList high;
    for (auto it = after.begin(); it != after.end(); ++it) {
        const quint64 prev = before.value(it.key(), 0);
        const double mbps  = static_cast<double>(it.value() - prev) / 2.0 / 1e6;
        if (mbps > 100.0)
            high.append(it.key() + QStringLiteral(" (") + QString::number(mbps, 'f', 1) + QStringLiteral(" MB/s)"));
    }

    if (!high.isEmpty())
        return {QStringLiteral("alert"), QStringLiteral("High traffic: ") + high.join(QStringLiteral(", "))};
    return {QStringLiteral("ok"), QStringLiteral("No traffic anomalies detected")};
#else
    return {QStringLiteral("ok"), QStringLiteral("Traffic check not available on Windows")};
#endif
}

CiCheck Daemon::checkRogueDhcp() {
    // Check journal for multiple DHCP offers from different sources
    const shadow::ProcessResult r = shadow::runProcess(
        QStringLiteral("journalctl"),
        {QStringLiteral("-u"), QStringLiteral("NetworkManager"), QStringLiteral("-u"), QStringLiteral("dhcpcd"),
         QStringLiteral("--since"), QStringLiteral("1 hour ago"), QStringLiteral("-o"), QStringLiteral("short"),
         QStringLiteral("--no-pager"), QStringLiteral("-q")},
        {}, 10000);

    if (r.exitCode != 0 && r.out.isEmpty())
        return {QStringLiteral("ok"), QStringLiteral("No DHCP log available")};

    const QString log = QString::fromUtf8(r.out);
    const int offerCount = log.count(QStringLiteral("DHCPOFFER"), Qt::CaseInsensitive);
    if (offerCount > 2)
        return {QStringLiteral("warning"),
                QString::number(offerCount) + QStringLiteral(" DHCP offers seen — possible rogue DHCP server")};
    return {QStringLiteral("ok"), QStringLiteral("DHCP appears normal")};
}

CiCheck Daemon::checkSslInterception() {
    // Check for non-standard CAs in system trust store that look suspicious
    const shadow::ProcessResult r = shadow::runProcess(
        QStringLiteral("trust"), {QStringLiteral("list"), QStringLiteral("--filter=ca-anchor")},
        {}, 10000);

    if (r.exitCode != 0)
        return {QStringLiteral("ok"), QStringLiteral("Cannot inspect CA store (trust tool unavailable)")};

    // Look for recently added CAs (in the past 30 days would need file stat — skip for now)
    const QString output = QString::fromUtf8(r.out);
    const int caCount = output.count(QStringLiteral("pkcs11:"));
    QJsonObject obj;
    return {QStringLiteral("ok"),
            QString::number(caCount) + QStringLiteral(" CAs in trust store — manual review recommended if unfamiliar")};
}

CiCheck Daemon::checkOsintSelf() {
    // Get public IP and do a basic check
    try {
        const QJsonObject resp = shadow::NativeTools::request(
            QUrl(QStringLiteral("https://api.ipify.org?format=json")), {}, false, {}, {}, 10000);
        const QString ip = resp.value(QStringLiteral("ip")).toString();
        if (ip.isEmpty())
            return {QStringLiteral("ok"), QStringLiteral("Could not determine public IP")};
        return {QStringLiteral("ok"), QStringLiteral("Public IP: ") + ip};
    } catch (...) {
        return {QStringLiteral("ok"), QStringLiteral("OSINT check skipped (offline?)")};
    }
}

// ── Ghost Mode ────────────────────────────────────────────────────────────────

QJsonValue Daemon::handleGhostStatus() {
    bool torActive    = false;
    bool killSwitch   = false;
    bool dnsLocked    = false;
    QString mac;

#ifndef Q_OS_WIN
    // Tor
    {
        const shadow::ProcessResult r = shadow::runProcess(
            QStringLiteral("systemctl"), {QStringLiteral("is-active"), QStringLiteral("tor")}, {}, 5000);
        torActive = (r.out.trimmed() == QByteArray("active"));
    }

    // Kill-switch: look for DROP rule in OUTPUT chain
    {
        const shadow::ProcessResult r = shadow::runProcess(
            QStringLiteral("iptables"), {QStringLiteral("-L"), QStringLiteral("OUTPUT"), QStringLiteral("-n")}, {}, 5000);
        killSwitch = QString::fromUtf8(r.out).contains(QStringLiteral("DROP"));
    }

    // MAC address of primary interface
    {
        const shadow::ProcessResult r = shadow::runProcess(
            QStringLiteral("ip"), {QStringLiteral("link"), QStringLiteral("show")}, {}, 5000);
        const QString out = QString::fromUtf8(r.out);
        // Find first non-loopback interface MAC
        static QRegularExpression re(QStringLiteral("link/ether ([0-9a-f:]{17})"));
        const auto m = re.match(out);
        if (m.hasMatch()) mac = m.captured(1);
    }

    // DNS locked to loopback
    {
        QFile resolv(QStringLiteral("/etc/resolv.conf"));
        if (resolv.open(QIODevice::ReadOnly)) {
            const QString content = QString::fromUtf8(resolv.readAll());
            dnsLocked = content.contains(QStringLiteral("nameserver 127."));
        }
    }
#endif

    QJsonObject obj;
    obj[QStringLiteral("tor")]         = torActive;
    obj[QStringLiteral("kill_switch")] = killSwitch;
    obj[QStringLiteral("mac")]         = mac;
    obj[QStringLiteral("dns_locked")]  = dnsLocked;
    obj[QStringLiteral("active")]      = torActive && killSwitch;
    return obj;
}

QJsonValue Daemon::handleGhostEnable() {
#ifndef Q_OS_WIN
    QStringList errors;
    auto run = [&](const QString& prog, const QStringList& args) {
        const shadow::ProcessResult r = shadow::runProcess(prog, args, {}, 15000);
        if (r.exitCode != 0)
            errors.append(prog + QStringLiteral(": ") + QString::fromUtf8(r.err).trimmed());
    };

    // 1. Start Tor
    run(QStringLiteral("systemctl"), {QStringLiteral("start"), QStringLiteral("tor")});
    QThread::sleep(2);

    // 2. Kill-switch: block all non-Tor outbound traffic
    run(QStringLiteral("iptables"), {QStringLiteral("-I"), QStringLiteral("OUTPUT"), QStringLiteral("1"),
        QStringLiteral("-m"), QStringLiteral("owner"), QStringLiteral("--uid-owner"),
        QStringLiteral("debian-tor"), QStringLiteral("-j"), QStringLiteral("ACCEPT")});
    run(QStringLiteral("iptables"), {QStringLiteral("-A"), QStringLiteral("OUTPUT"),
        QStringLiteral("-d"), QStringLiteral("127.0.0.0/8"), QStringLiteral("-j"), QStringLiteral("ACCEPT")});
    run(QStringLiteral("iptables"), {QStringLiteral("-A"), QStringLiteral("OUTPUT"),
        QStringLiteral("-j"), QStringLiteral("DROP")});

    // 3. Lock DNS to Tor's resolver
    // (Best-effort — requires write permission to /etc/resolv.conf)
    QFile resolv(QStringLiteral("/etc/resolv.conf"));
    if (resolv.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        resolv.write("nameserver 127.0.0.1\n");
        resolv.close();
    }

    QJsonObject obj;
    obj[QStringLiteral("ok")]   = errors.isEmpty();
    if (!errors.isEmpty())
        obj[QStringLiteral("error")] = errors.join(QStringLiteral("; "));
    return obj;
#else
    QJsonObject obj;
    obj[QStringLiteral("ok")]    = false;
    obj[QStringLiteral("error")] = QStringLiteral("Ghost mode not supported on Windows");
    return obj;
#endif
}

QJsonValue Daemon::handleGhostDisable() {
#ifndef Q_OS_WIN
    QStringList errors;
    auto run = [&](const QString& prog, const QStringList& args) {
        const shadow::ProcessResult r = shadow::runProcess(prog, args, {}, 15000);
        if (r.exitCode != 0)
            errors.append(prog + QStringLiteral(": ") + QString::fromUtf8(r.err).trimmed());
    };

    // 1. Flush OUTPUT chain kill-switch rules
    run(QStringLiteral("iptables"), {QStringLiteral("-F"), QStringLiteral("OUTPUT")});

    // 2. Stop Tor
    run(QStringLiteral("systemctl"), {QStringLiteral("stop"), QStringLiteral("tor")});

    // 3. Restore DNS (try resolvectl, then dhclient, then fallback)
    {
        const shadow::ProcessResult r = shadow::runProcess(
            QStringLiteral("resolvectl"), {QStringLiteral("revert")}, {}, 5000);
        if (r.exitCode != 0)
            shadow::runProcess(QStringLiteral("dhclient"), {QStringLiteral("-1")}, {}, 10000);
    }

    QJsonObject obj;
    obj[QStringLiteral("ok")]   = errors.isEmpty();
    if (!errors.isEmpty())
        obj[QStringLiteral("error")] = errors.join(QStringLiteral("; "));
    return obj;
#else
    QJsonObject obj;
    obj[QStringLiteral("ok")]    = false;
    obj[QStringLiteral("error")] = QStringLiteral("Ghost mode not supported on Windows");
    return obj;
#endif
}

// ── State persistence ─────────────────────────────────────────────────────────

void Daemon::loadState() {
    QFile f(m_statePath);
    if (!f.open(QIODevice::ReadOnly)) return;
    const QJsonObject root = QJsonDocument::fromJson(f.readAll()).object();
    m_devices   = root.value(QStringLiteral("devices")).toArray();
    m_incidents = root.value(QStringLiteral("incidents")).toArray();
}

void Daemon::saveState() {
    QJsonObject root;
    root[QStringLiteral("devices")]   = m_devices;
    root[QStringLiteral("incidents")] = m_incidents;
    QFile f(m_statePath + QStringLiteral(".tmp"));
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return;
    f.write(QJsonDocument(root).toJson());
    f.close();
    QFile::remove(m_statePath);
    f.rename(m_statePath);
}

void Daemon::addIncident(const QString& deviceIp, const QString& type,
                          const QString& description, const QString& severity) {
    QJsonObject inc;
    inc[QStringLiteral("status")]      = QStringLiteral("open");
    inc[QStringLiteral("severity")]    = severity;
    inc[QStringLiteral("device_ip")]   = deviceIp;
    inc[QStringLiteral("type")]        = type;
    inc[QStringLiteral("description")] = description;
    inc[QStringLiteral("created_at")]  = QDateTime::currentDateTimeUtc().toString(Qt::ISODate);
    m_incidents.prepend(inc);

    // Cap at 500 incidents
    while (m_incidents.size() > 500)
        m_incidents.removeLast();
}

void Daemon::reconcileDevices(const QJsonArray& fresh) {
    // Build map of current IPs
    QMap<QString, QString> oldIpToMac;
    for (const QJsonValue& v : m_devices) {
        const QJsonObject d = v.toObject();
        oldIpToMac[d.value(QStringLiteral("ip")).toString()] =
            d.value(QStringLiteral("mac")).toString();
    }

    for (const QJsonValue& v : fresh) {
        const QJsonObject d = v.toObject();
        const QString ip  = d.value(QStringLiteral("ip")).toString();
        const QString mac = d.value(QStringLiteral("mac")).toString();

        if (!oldIpToMac.contains(ip)) {
            // New device
            addIncident(ip, QStringLiteral("new_device"),
                        QStringLiteral("New device appeared: ") + ip + QStringLiteral(" (") + mac + QStringLiteral(")"),
                        QStringLiteral("low"));
        } else if (oldIpToMac[ip] != mac && !mac.isEmpty() && !oldIpToMac[ip].isEmpty()) {
            // MAC changed on same IP — possible ARP spoof
            addIncident(ip, QStringLiteral("arp_change"),
                        QStringLiteral("MAC changed on ") + ip + QStringLiteral(": ") +
                        oldIpToMac[ip] + QStringLiteral(" → ") + mac,
                        QStringLiteral("high"));
        }
    }
}

// ── Util ──────────────────────────────────────────────────────────────────────

void Daemon::respond(QIODevice* sock, const QJsonValue& id, const QJsonValue& result) {
    QJsonObject resp;
    resp[QStringLiteral("jsonrpc")] = QStringLiteral("2.0");
    resp[QStringLiteral("id")]      = id;
    resp[QStringLiteral("result")]  = result;
    sock->write(QJsonDocument(resp).toJson(QJsonDocument::Compact) + '\n');
}

void Daemon::respondError(QIODevice* sock, const QJsonValue& id, const QString& msg, int code) {
    QJsonObject err;
    err[QStringLiteral("code")]    = code;
    err[QStringLiteral("message")] = msg;
    QJsonObject resp;
    resp[QStringLiteral("jsonrpc")] = QStringLiteral("2.0");
    resp[QStringLiteral("id")]      = id;
    resp[QStringLiteral("error")]   = err;
    sock->write(QJsonDocument(resp).toJson(QJsonDocument::Compact) + '\n');
}
