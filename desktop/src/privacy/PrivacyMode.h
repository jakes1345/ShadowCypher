#pragma once
#include <QObject>
#include <QString>

// Privacy mode: routes all traffic through Tor with an iptables kill-switch.
// Linux: uses systemd + iptables. Windows: stub (routes via SOCKS proxy).
class PrivacyMode : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool active READ active NOTIFY activeChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)

public:
    explicit PrivacyMode(QObject* parent = nullptr);

    bool    active() const { return m_active; }
    QString status() const { return m_status; }

    Q_INVOKABLE void engage();
    Q_INVOKABLE void disengage();
    Q_INVOKABLE void verify();

signals:
    void activeChanged();
    void statusChanged();
    void verifyResult(bool ok, const QString& report);

private:
    void setStatus(const QString& s) { m_status = s; emit statusChanged(); }
    void rollback();

    bool       m_active     = false;
    QString    m_status     = "off";
};
