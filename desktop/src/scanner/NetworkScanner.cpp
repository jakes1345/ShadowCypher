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
    // Run in Qt concurrent to avoid blocking UI
    QList<Device> found = parseArpTable();
    for (auto& d : found) {
        auto it = std::find_if(m_knownDevices.begin(), m_knownDevices.end(),
            [&](const Device& k) { return k.ip == d.ip; });
        if (it == m_knownDevices.end()) {
            d.isNew = true;
            emit newDeviceFound(d.ip, d.mac);
        } else if (it->mac != d.mac) {
            d.isSuspect = true;
            emit arpSpoofDetected(d.ip, it->mac, d.mac);
        }
    }
    m_knownDevices = found;
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
