#pragma once
#include <QObject>
#include <QString>
#include <QMap>

// Tracks IP→MAC mappings and fires spoofDetected when a known IP
// starts advertising a different MAC address.
class ArpMonitor : public QObject
{
    Q_OBJECT

public:
    explicit ArpMonitor(QObject* parent = nullptr);

    void update(const QString& ip, const QString& mac);
    void clear() { m_table.clear(); }

signals:
    void spoofDetected(const QString& ip, const QString& knownMac, const QString& newMac);

private:
    QMap<QString, QString> m_table; // ip → mac
};
