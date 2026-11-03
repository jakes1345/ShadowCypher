#include "NetworkScanner.h"
#include <QProcess>
#include <QFile>
#include <QTextStream>
#include <QJsonObject>
#include <QHostInfo>
#include <QNetworkInterface>
#include <QDateTime>

NetworkScanner::NetworkScanner(QObject* parent) : QObject(parent)
{
    m_timer.setInterval(600'000); // 10 min default
    connect(&m_timer, &QTimer::timeout, this, &NetworkScanner::onTimer);
}

NetworkScanner::~NetworkScanner()
{
    stop();
}

void NetworkScanner::start()
{
    m_running = true;
    emit runningChanged();
    m_timer.start();
    scanNow();
}

void NetworkScanner::stop()
{
    m_timer.stop();
    m_running = false;
    emit runningChanged();
}

void NetworkScanner::onTimer() { scanNow(); }

void NetworkScanner::scanNow()
{
    QList<Device> found = parseArpTable();

    for (auto& d : found) {
        // 1. Check confirmed baseline first.
        auto base = std::find_if(m_baseline.begin(), m_baseline.end(),
            [&](const Device& k) { return k.ip == d.ip; });
        if (base != m_baseline.end()) {
            if (base->mac != d.mac) {
                d.isSuspect = true;
                emit arpSpoofDetected(d.ip, base->mac, d.mac);
            }
            continue;
        }

        // 2. Check pending (first-seen but not yet confirmed) list.
        auto pend = std::find_if(m_pending.begin(), m_pending.end(),
            [&](const Device& k) { return k.ip == d.ip; });
        if (pend != m_pending.end()) {
            // Still unconfirmed — detect MAC changes against the first-seen MAC.
            if (pend->mac != d.mac) {
                d.isSuspect = true;
                emit arpSpoofDetected(d.ip, pend->mac, d.mac);
            }
            // isNew stays false on repeat scans of a pending device.
            continue;
        }

        // 3. Genuinely new IP — add to pending, NOT to baseline.
        //    The user must call confirmDevice(ip) to promote it to baseline.
        d.isNew = true;
        m_pending.append(d);
        emit newDeviceFound(d.ip, d.mac);
    }

    m_devices = found;
    emit devicesChanged();
    emit scanComplete(found.size());
}

QList<Device> NetworkScanner::parseArpTable()
{
    QList<Device> devices;

#ifdef SC_LINUX
    QFile arp("/proc/net/arp");
    if (arp.open(QIODevice::ReadOnly)) {
        QTextStream ts(&arp);
        ts.readLine(); // skip header
        while (!ts.atEnd()) {
            const QStringList cols = ts.readLine().split(' ', Qt::SkipEmptyParts);
            if (cols.size() < 4) continue;
            Device d;
            d.ip  = cols[0];
            d.mac = cols[3];
            if (d.mac == "00:00:00:00:00:00") continue;
            d.hostname = QHostInfo::localHostName();
            devices.append(d);
        }
    }
#elif defined(SC_WINDOWS)
    // Use GetIpNetTable via QProcess arp -a
    QProcess p;
    p.start("arp", {"-a"});
    p.waitForFinished(5000);
    const QString out = p.readAllStandardOutput();
    for (const QString& line : out.split('\n')) {
        const QStringList cols = line.simplified().split(' ');
        if (cols.size() >= 2 && cols[0].contains('.')) {
            Device d;
            d.ip  = cols[0];
            d.mac = cols.size() > 1 ? cols[1] : "";
            devices.append(d);
        }
    }
#endif

    return devices;
}

void NetworkScanner::confirmDevice(const QString& ip)
{
    // Find the device in the last scan result.
    auto cur = std::find_if(m_devices.begin(), m_devices.end(),
        [&](const Device& d) { return d.ip == ip; });
    if (cur == m_devices.end()) return;

    // Remove from pending (if present).
    m_pending.removeIf([&](const Device& d) { return d.ip == ip; });

    // Add/update in confirmed baseline with the current (user-approved) MAC.
    auto base = std::find_if(m_baseline.begin(), m_baseline.end(),
        [&](const Device& d) { return d.ip == ip; });
    if (base != m_baseline.end())
        base->mac = cur->mac;
    else
        m_baseline.append(*cur);

    cur->isSuspect = false;
    cur->isNew     = false;
    emit devicesChanged();
}

int NetworkScanner::newCount() const
{
    int n = 0;
    for (const auto& d : m_devices) if (d.isNew) ++n;
    return n;
}

int NetworkScanner::alertCount() const
{
    int n = 0;
    for (const auto& d : m_devices) if (d.isSuspect) ++n;
    return n;
}

QJsonArray NetworkScanner::devicesJson() const
{
    QJsonArray arr;
    for (const auto& d : m_devices) {
        QJsonObject obj;
        obj["ip"]       = d.ip;
        obj["mac"]      = d.mac;
        obj["hostname"] = d.hostname;
        obj["vendor"]   = d.vendor;
        obj["isNew"]    = d.isNew;
        obj["suspect"]  = d.isSuspect;
        obj["lastSeen"] = QDateTime::currentDateTime().toString("hh:mm:ss");
        arr.append(obj);
    }
    return arr;
}
