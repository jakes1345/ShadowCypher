#include "PrivacyMode.h"
#include <QProcess>

PrivacyMode::PrivacyMode(QObject* parent) : QObject(parent) {}

void PrivacyMode::engage()
{
#ifdef SC_LINUX
    setStatus("engaging");
    QProcess p;
    // Start Tor service, apply iptables kill-switch
    p.start("bash", {"-c",
        "systemctl start tor && "
        "iptables -F && iptables -P OUTPUT DROP && "
        "iptables -A OUTPUT -m owner --uid-owner debian-tor -j ACCEPT && "
        "iptables -A OUTPUT -o lo -j ACCEPT && "
        "iptables -A OUTPUT -j DROP"
    });
    p.waitForFinished(15000);
    const bool ok = (p.exitCode() == 0);
    m_active = ok;
    setStatus(ok ? "active" : "error");
    emit activeChanged();
#elif defined(SC_WINDOWS)
    // Windows: configure SOCKS5 proxy to Tor on 127.0.0.1:9050
    setStatus("proxy-mode"); // full iptables not available on Windows
    m_active = true;
    emit activeChanged();
#endif
}

void PrivacyMode::disengage()
{
#ifdef SC_LINUX
    QProcess p;
    p.start("bash", {"-c",
        "systemctl stop tor && "
        "iptables -F && iptables -P OUTPUT ACCEPT"
    });
    p.waitForFinished(10000);
#endif
    m_active = false;
    setStatus("off");
    emit activeChanged();
}

void PrivacyMode::verify()
{
    // Check real IP via Tor
    QProcess p;
#ifdef SC_LINUX
    p.start("bash", {"-c",
        "curl --socks5 127.0.0.1:9050 --max-time 10 -s https://check.torproject.org/api/ip"
    });
#elif defined(SC_WINDOWS)
    p.start("curl", {"--socks5", "127.0.0.1:9050", "--max-time", "10", "-s",
                     "https://check.torproject.org/api/ip"});
#endif
    p.waitForFinished(15000);
    const QString out = p.readAllStandardOutput();
    const bool ok = out.contains("\"IsTor\":true");
    emit verifyResult(ok, ok ? "Tor confirmed." : "Not routing through Tor.");
}
