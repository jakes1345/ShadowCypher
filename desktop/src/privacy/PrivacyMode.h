#pragma once
#include <QObject>
#include <QString>

// Privacy mode: routes all traffic through Tor with an iptables kill-switch.
// Linux: firewall changes go through shadowcypher-privacy-helper via pkexec.
// Windows: not implemented.
class PrivacyMode : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool active READ active NOTIFY activeChanged)
    Q_PROPERTY(bool busy   READ busy   NOTIFY busyChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)

public:
    explicit PrivacyMode(QObject* parent = nullptr);

    bool    active() const { return m_active; }
    bool    busy()   const { return m_busy; }
    QString status() const { return m_status; }

    Q_INVOKABLE void engage();
    Q_INVOKABLE void disengage();
    Q_INVOKABLE void verify();

signals:
    void activeChanged();
    void busyChanged();
    void statusChanged();
    void verifyResult(bool ok, const QString& report);

private:
    void setStatus(const QString& s) { m_status = s; emit statusChanged(); }
    void setActive(bool a) { if (a == m_active) return; m_active = a; emit activeChanged(); }
    void setBusy(bool b)   { if (b == m_busy) return; m_busy = b; emit busyChanged(); }
    void runHelper(const QString& verb);
    void onHelperFinished(const QString& verb, int exitCode, const QString& output);

    bool       m_active = false;
    bool       m_busy   = false;
    QString    m_status = "off";
};
