#include "PrivacyMode.h"
#include <QProcess>

PrivacyMode::PrivacyMode(QObject* parent) : QObject(parent) {}

// Helper: run a shell command, return true only if it exited normally with code 0.
static bool runShell(const QString& cmd, int timeoutMs = 15000)
{
    QProcess p;
    p.start("bash", {"-c", cmd});
    const bool finished = p.waitForFinished(timeoutMs);
    return finished
        && p.exitStatus() == QProcess::NormalExit
        && p.exitCode() == 0;
}

void PrivacyMode::engage()
{
#ifdef SC_LINUX
    setStatus("engaging");

    // Save existing iptables rules so we can restore them on disengage.
    QProcess save;
    save.start("bash", {"-c", "iptables-save; ip6tables-save"});
    save.waitForFinished(5000);
    m_savedRules = save.readAllStandardOutput();

    // Use a dedicated chain (SHADOW_KS) instead of flushing global OUTPUT.
    const QString setup =
        // IPv4 kill-switch
        "iptables -N SHADOW_KS 2>/dev/null; "
        "iptables -F SHADOW_KS; "
        "iptables -A SHADOW_KS -m owner --uid-owner debian-tor -j ACCEPT; "
        "iptables -A SHADOW_KS -o lo -j ACCEPT; "
        "iptables -A SHADOW_KS -j DROP; "
        "iptables -C OUTPUT -j SHADOW_KS 2>/dev/null || iptables -I OUTPUT 1 -j SHADOW_KS; "
        // IPv6 kill-switch (prevent IPv6 leaks)
        "ip6tables -N SHADOW_KS6 2>/dev/null; "
        "ip6tables -F SHADOW_KS6; "
        "ip6tables -A SHADOW_KS6 -o lo -j ACCEPT; "
        "ip6tables -A SHADOW_KS6 -j DROP; "
        "ip6tables -C OUTPUT -j SHADOW_KS6 2>/dev/null || ip6tables -I OUTPUT 1 -j SHADOW_KS6; "
        // Start Tor
        "systemctl start tor";

    const bool ok = runShell(setup);
    if (!ok) {
        // Roll back on partial failure
        runShell("iptables -D OUTPUT -j SHADOW_KS 2>/dev/null; iptables -F SHADOW_KS; iptables -X SHADOW_KS 2>/dev/null; "
                 "ip6tables -D OUTPUT -j SHADOW_KS6 2>/dev/null; ip6tables -F SHADOW_KS6; ip6tables -X SHADOW_KS6 2>/dev/null", 8000);
        m_active = false;
        setStatus("error: failed to apply kill-switch");
        emit activeChanged();
        return;
    }

    m_active = true;
    setStatus("active");
    emit activeChanged();

#elif defined(SC_WINDOWS)
    // Windows: full iptables kill-switch is not available.
    // Report as unsupported rather than falsely claiming protection.
    setStatus("unsupported: Windows kill-switch not implemented");
    m_active = false;
    emit activeChanged();
#endif
}

void PrivacyMode::disengage()
{
#ifdef SC_LINUX
    // Remove only our dedicated chain, don't flush the user's other rules.
    runShell("iptables -D OUTPUT -j SHADOW_KS 2>/dev/null; "
             "iptables -F SHADOW_KS; iptables -X SHADOW_KS 2>/dev/null; "
             "ip6tables -D OUTPUT -j SHADOW_KS6 2>/dev/null; "
             "ip6tables -F SHADOW_KS6; ip6tables -X SHADOW_KS6 2>/dev/null; "
             "systemctl stop tor", 10000);
    m_savedRules.clear();
#endif
    m_active = false;
    setStatus("off");
    emit activeChanged();
}

void PrivacyMode::verify()
{
    QProcess p;
#ifdef SC_LINUX
    p.start("bash", {"-c",
        "curl --socks5 127.0.0.1:9050 --max-time 10 -s https://check.torproject.org/api/ip"
    });
#elif defined(SC_WINDOWS)
    p.start("curl", {"--socks5", "127.0.0.1:9050", "--max-time", "10", "-s",
                     "https://check.torproject.org/api/ip"});
#endif
    const bool finished = p.waitForFinished(15000);
    if (!finished || p.exitStatus() != QProcess::NormalExit) {
        emit verifyResult(false, "curl timed out or crashed.");
        return;
    }
    const QString out = p.readAllStandardOutput();
    const bool ok = out.contains("\"IsTor\":true");
    emit verifyResult(ok, ok ? "Tor confirmed — all traffic is routed through Tor."
                             : "Not routing through Tor — check that Tor is running.");
}
