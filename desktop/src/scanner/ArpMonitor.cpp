#include "ArpMonitor.h"

ArpMonitor::ArpMonitor(QObject* parent) : QObject(parent) {}

void ArpMonitor::update(const QString& ip, const QString& mac)
{
    auto it = m_table.find(ip);
    if (it == m_table.end()) {
        m_table.insert(ip, mac);
    } else if (it.value() != mac) {
        emit spoofDetected(ip, it.value(), mac);
        it.value() = mac;
    }
}
