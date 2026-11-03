#pragma once
#include <QObject>
#include <QString>
#include <QJsonArray>
#include <QTimer>
#include <QThread>

struct Device {
    QString ip;
    QString mac;
    QString hostname;
    QStringList openPorts;
    QString vendor;
    bool    isNew      = false;
    bool    isSuspect  = false;
};

class NetworkScanner : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool       running    READ running    NOTIFY runningChanged)
    Q_PROPERTY(QJsonArray devices    READ devicesJson NOTIFY devicesChanged)
    Q_PROPERTY(int        newCount   READ newCount   NOTIFY devicesChanged)
    Q_PROPERTY(int        alertCount READ alertCount NOTIFY devicesChanged)

public:
    explicit NetworkScanner(QObject* parent = nullptr);
    ~NetworkScanner() override;

    bool       running()    const { return m_running; }
    int        newCount()   const;
    int        alertCount() const;
    QJsonArray devicesJson() const;

public slots:
    void start();
    void stop();
    Q_INVOKABLE void scanNow();
    // Confirm that a device's current MAC is legitimate, updating the baseline.
    Q_INVOKABLE void confirmDevice(const QString& ip);

signals:
    void runningChanged();
    void devicesChanged();
    void newDeviceFound(const QString& ip, const QString& mac);
    void arpSpoofDetected(const QString& ip, const QString& knownMac, const QString& currentMac);
    void scanComplete(int deviceCount);

private slots:
    void onTimer();

private:
    QList<Device> scan();
    QList<Device> parseArpTable();
    bool          detectArpSpoof(const Device&);

    QTimer        m_timer;
    QThread       m_thread;
    QList<Device> m_devices;
    // m_baseline: user-confirmed IP→MAC mappings. Only updated via confirmDevice().
    QList<Device> m_baseline;
    // m_pending: first-seen but not yet confirmed. MAC changes here still fire
    // arpSpoofDetected. Promoted to m_baseline via confirmDevice().
    QList<Device> m_pending;
    bool          m_running = false;
};
