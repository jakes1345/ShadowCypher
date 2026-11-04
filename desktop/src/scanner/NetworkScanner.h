#pragma once
#include <QObject>
#include <QString>
#include <QJsonArray>
#include <QTimer>
#include <QHash>
#include <QUdpSocket>
#include <QElapsedTimer>

struct Device {
    QString ip;
    QString mac;
    QString hostname;
    QStringList openPorts;
    QString vendor;
    bool    isNew      = false;
    bool    isSuspect  = false;
    bool    isTrusted  = false;
};

class NetworkScanner : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool       running    READ running    NOTIFY runningChanged)
    Q_PROPERTY(bool       scanning   READ scanning   NOTIFY scanningChanged)
    Q_PROPERTY(QJsonArray devices    READ devicesJson NOTIFY devicesChanged)
    Q_PROPERTY(int        newCount   READ newCount   NOTIFY devicesChanged)
    Q_PROPERTY(int        alertCount READ alertCount NOTIFY devicesChanged)

public:
    explicit NetworkScanner(QObject* parent = nullptr);
    ~NetworkScanner() override;

    bool       running()    const { return m_running; }
    bool       scanning()   const { return m_scanning; }
    int        newCount()   const;
    int        alertCount() const;
    QJsonArray devicesJson() const;

    void setIntervalSeconds(int seconds);
    qint64 lastScanDurationMs() const { return m_lastDurationMs; }

public slots:
    void start();
    void stop();
    Q_INVOKABLE void scanNow();
    // Confirm that a device's current MAC is legitimate, updating the baseline.
    Q_INVOKABLE void confirmDevice(const QString& ip);

signals:
    void runningChanged();
    void scanningChanged();
    void devicesChanged();
    void newDeviceFound(const QString& ip, const QString& mac);
    void arpSpoofDetected(const QString& ip, const QString& knownMac, const QString& currentMac);
    void scanComplete(int deviceCount);

private:
    void          probeLocalSubnets();
    void          collectResults();
    void          resolveHostnames();
    QList<Device> parseArpTable();
    void          loadBaseline();
    void          saveBaseline() const;

    QTimer        m_timer;
    // Probes sit in the kernel's ARP queue (charged to the sending socket) until
    // resolution finishes, so one socket's send buffer caps a sweep at ~200 hosts.
    QList<QUdpSocket*> m_probeSockets;
    QList<Device> m_devices;
    // m_baseline: user-confirmed IP→MAC mappings. Only updated via confirmDevice().
    QList<Device> m_baseline;
    // m_pending: first-seen but not yet confirmed. MAC changes here still fire
    // arpSpoofDetected. Promoted to m_baseline via confirmDevice().
    QList<Device> m_pending;
    QHash<QString, QString> m_hostnames;   // ip → reverse-DNS name ("" = no PTR record)
    QString       m_baselinePath;
    QElapsedTimer m_scanClock;
    qint64        m_lastDurationMs = 0;
    bool          m_running  = false;
    bool          m_scanning = false;
};
