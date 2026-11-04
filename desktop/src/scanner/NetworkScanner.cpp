#include "NetworkScanner.h"
#include <QProcess>
#include <QFile>
#include <QDir>
#include <QStandardPaths>
#include <QTextStream>
#include <QJsonObject>
#include <QJsonDocument>
#include <QHostInfo>
#include <QHostAddress>
#include <QNetworkInterface>
#include <QDateTime>

// Hosts probed per interface; a /22 is the largest subnet swept.
static constexpr int kMaxProbeHosts = 1024;
static constexpr int kProbesPerSocket = 128;
// Time for the kernel to finish ARP resolution after the probes go out.
static constexpr int kArpSettleMs   = 2500;

NetworkScanner::NetworkScanner(QObject* parent) : QObject(parent)
{
    m_timer.setInterval(600'000); // 10 min default
    connect(&m_timer, &QTimer::timeout, this, &NetworkScanner::scanNow);

    const QString dir = QStandardPaths::writableLocation(QStandardPaths::HomeLocation) + "/.shadowcypher";
    QDir().mkpath(dir);
    m_baselinePath = dir + "/desktop_baseline.json";
    loadBaseline();
}

NetworkScanner::~NetworkScanner()
{
    stop();
}

void NetworkScanner::setIntervalSeconds(int seconds)
{
    m_timer.setInterval(qMax(30, seconds) * 1000);
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
    if (!m_running) return;
    m_running = false;
    emit runningChanged();
}

void NetworkScanner::scanNow()
{
    if (m_scanning) return;
    m_scanning = true;
    emit scanningChanged();
    m_scanClock.start();

    probeLocalSubnets();
    QTimer::singleShot(kArpSettleMs, this, &NetworkScanner::collectResults);
}

// /proc/net/arp only lists hosts we've already talked to. Sending one UDP
// datagram to every address on the local subnet makes the kernel ARP-resolve
// each of them, without needing raw sockets or root.
void NetworkScanner::probeLocalSubnets()
{
    const QByteArray payload(1, '\0');
    QUdpSocket* sock = nullptr;
    int onSocket = kProbesPerSocket;
    auto send = [&](const QHostAddress& addr) {
        if (onSocket == kProbesPerSocket) {
            sock = new QUdpSocket(this);
            m_probeSockets.append(sock);
            onSocket = 0;
        }
        // Port 9 is "discard"; nothing needs to answer, only ARP matters.
        sock->writeDatagram(payload, addr, 9);
        ++onSocket;
    };

    for (const QNetworkInterface& iface : QNetworkInterface::allInterfaces()) {
        const auto flags = iface.flags();
        if (!(flags & QNetworkInterface::IsUp) || !(flags & QNetworkInterface::IsRunning)
            || (flags & QNetworkInterface::IsLoopBack))
            continue;

        for (const QNetworkAddressEntry& entry : iface.addressEntries()) {
            const QHostAddress self = entry.ip();
            if (self.protocol() != QAbstractSocket::IPv4Protocol) continue;
            const int prefix = entry.prefixLength();
            if (prefix < 22 || prefix > 30) continue;

            const quint32 mask    = prefix == 0 ? 0 : (0xFFFFFFFFu << (32 - prefix));
            const quint32 network = self.toIPv4Address() & mask;
            const quint32 bcast   = network | ~mask;
            int sent = 0;
            for (quint32 a = network + 1; a < bcast && sent < kMaxProbeHosts; ++a) {
                if (a == self.toIPv4Address()) continue;
                send(QHostAddress(a));
                ++sent;
            }
        }
    }
}

void NetworkScanner::collectResults()
{
    qDeleteAll(m_probeSockets);
    m_probeSockets.clear();

    QList<Device> found = parseArpTable();

    for (auto& d : found) {
        // 1. Check confirmed baseline first.
        auto base = std::find_if(m_baseline.begin(), m_baseline.end(),
            [&](const Device& k) { return k.ip == d.ip; });
        if (base != m_baseline.end()) {
            if (base->mac != d.mac) {
                d.isSuspect = true;
                emit arpSpoofDetected(d.ip, base->mac, d.mac);
            } else {
                d.isTrusted = true;
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
    m_lastDurationMs = m_scanClock.elapsed();
    m_scanning = false;
    emit scanningChanged();
    emit devicesChanged();
    emit scanComplete(found.size());
    resolveHostnames();
}

void NetworkScanner::resolveHostnames()
{
    for (const Device& d : std::as_const(m_devices)) {
        if (m_hostnames.contains(d.ip)) continue;
        m_hostnames.insert(d.ip, QString());   // mark in-flight; no repeat lookups
        const QString ip = d.ip;
        QHostInfo::lookupHost(ip, this, [this, ip](const QHostInfo& info) {
            const QString name = info.error() == QHostInfo::NoError ? info.hostName() : QString();
            if (name.isEmpty() || name == ip) return;
            m_hostnames.insert(ip, name);
            for (auto& dev : m_devices)
                if (dev.ip == ip) dev.hostname = name;
            emit devicesChanged();
        });
    }
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
            // IP address, HW type, Flags, HW address, Mask, Device
            const QStringList cols = ts.readLine().split(' ', Qt::SkipEmptyParts);
            if (cols.size() < 4) continue;
            if (cols[2] == "0x0") continue;            // incomplete: nobody answered
            Device d;
            d.ip  = cols[0];
            d.mac = cols[3].toLower();
            if (d.mac == "00:00:00:00:00:00") continue;
            d.hostname = m_hostnames.value(d.ip);
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
            d.hostname = m_hostnames.value(d.ip);
            devices.append(d);
        }
    }
#endif

    std::sort(devices.begin(), devices.end(), [](const Device& a, const Device& b) {
        return QHostAddress(a.ip).toIPv4Address() < QHostAddress(b.ip).toIPv4Address();
    });
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
    cur->isTrusted = true;
    saveBaseline();
    emit devicesChanged();
}

void NetworkScanner::loadBaseline()
{
    QFile f(m_baselinePath);
    if (!f.open(QIODevice::ReadOnly)) return;
    const QJsonArray arr = QJsonDocument::fromJson(f.readAll()).array();
    for (const auto& v : arr) {
        const QJsonObject o = v.toObject();
        Device d;
        d.ip  = o["ip"].toString();
        d.mac = o["mac"].toString().toLower();
        if (!d.ip.isEmpty() && !d.mac.isEmpty()) m_baseline.append(d);
    }
}

void NetworkScanner::saveBaseline() const
{
    QJsonArray arr;
    for (const auto& d : m_baseline)
        arr.append(QJsonObject{{"ip", d.ip}, {"mac", d.mac}});
    QFile f(m_baselinePath);
    if (f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        f.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
        f.write(QJsonDocument(arr).toJson());
    }
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
        obj["trusted"]  = d.isTrusted;
        obj["lastSeen"] = QDateTime::currentDateTime().toString("hh:mm:ss");
        arr.append(obj);
    }
    return arr;
}
