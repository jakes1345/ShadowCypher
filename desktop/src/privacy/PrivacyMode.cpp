#include "PrivacyMode.h"
#include <QProcess>

// Run a single iptables/ip6tables/systemctl command as an argument list (no shell injection).
// Returns true only if the process exits normally with code 0.
static bool run(const QString& prog, const QStringList& args, int timeoutMs = 8000)
{
    QProcess p;
    p.start(prog, args);
    const bool finished = p.waitForFinished(timeoutMs);
    return finished
        && p.exitStatus() == QProcess::NormalExit
        && p.exitCode() == 0;
}

// Check whether a rule reference exists without changing anything.
static bool ruleExists(const QString& table, const QStringList& ruleArgs)
{
    // iptables -t <table> -C <ruleArgs> exits 0 if rule exists, 1 if not.
    QStringList args = {"-t", table, "-C"};
    args << ruleArgs;
    return run("iptables", args);
}
static bool rule6Exists(const QString& table, const QStringList& ruleArgs)
{
    QStringList args = {"-t", table, "-C"};
    args << ruleArgs;
    return run("ip6tables", args);
}

PrivacyMode::PrivacyMode(QObject* parent) : QObject(parent) {}

void PrivacyMode::engage()
{
#ifdef SC_LINUX
    setStatus("engaging");

    // Save existing rules for clean restore on disengage.
    {
        QProcess save;
        save.start("bash", {"-c", "iptables-save && ip6tables-save"});
        if (save.waitForFinished(5000) && save.exitStatus() == QProcess::NormalExit)
            m_savedRules = save.readAllStandardOutput();
    }

    // ── IPv4 kill-switch ──────────────────────────────────────────────────
    // Create chain (tolerate "already exists"); fail on anything else.
    run("iptables", {"-N", "SHADOW_KS"}); // tolerated if chain exists
    if (!run("iptables", {"-F", "SHADOW_KS"})
     || !run("iptables", {"-A", "SHADOW_KS", "-m", "owner", "--uid-owner", "debian-tor", "-j", "ACCEPT"})
     || !run("iptables", {"-A", "SHADOW_KS", "-o", "lo", "-j", "ACCEPT"})
     || !run("iptables", {"-A", "SHADOW_KS", "-j", "DROP"})) {
        rollback();
        setStatus("error: failed to build IPv4 kill-switch chain");
        emit activeChanged();
        return;
    }
    // Insert into OUTPUT only if not already there.
    if (!ruleExists("filter", {"OUTPUT", "-j", "SHADOW_KS"}))
        if (!run("iptables", {"-I", "OUTPUT", "1", "-j", "SHADOW_KS"})) {
            rollback();
            setStatus("error: failed to insert IPv4 OUTPUT rule");
            emit activeChanged();
            return;
        }

    // ── IPv6 kill-switch ──────────────────────────────────────────────────
    run("ip6tables", {"-N", "SHADOW_KS6"});
    if (!run("ip6tables", {"-F", "SHADOW_KS6"})
     || !run("ip6tables", {"-A", "SHADOW_KS6", "-o", "lo", "-j", "ACCEPT"})
     || !run("ip6tables", {"-A", "SHADOW_KS6", "-j", "DROP"})) {
        rollback();
        setStatus("error: failed to build IPv6 kill-switch chain");
        emit activeChanged();
        return;
    }
    if (!rule6Exists("filter", {"OUTPUT", "-j", "SHADOW_KS6"}))
        if (!run("ip6tables", {"-I", "OUTPUT", "1", "-j", "SHADOW_KS6"})) {
            rollback();
            setStatus("error: failed to insert IPv6 OUTPUT rule");
            emit activeChanged();
            return;
        }

    // ── Start Tor ─────────────────────────────────────────────────────────
    if (!run("systemctl", {"start", "tor"}, 20000)) {
        rollback();
        setStatus("error: Tor failed to start");
        emit activeChanged();
        return;
    }

    // ── Confirm rules are actually in place before claiming active ────────
    if (!ruleExists("filter", {"OUTPUT", "-j", "SHADOW_KS"})
     || !rule6Exists("filter", {"OUTPUT", "-j", "SHADOW_KS6"})) {
        rollback();
        setStatus("error: kill-switch rules not confirmed after setup");
        emit activeChanged();
        return;
    }

    m_active = true;
    setStatus("active");
    emit activeChanged();

#elif defined(SC_WINDOWS)
    setStatus("unsupported: Windows kill-switch not implemented");
    m_active = false;
    emit activeChanged();
#endif
}

void PrivacyMode::disengage()
{
#ifdef SC_LINUX
    rollback();
#endif
    m_active = false;
    setStatus("off");
    emit activeChanged();
}

void PrivacyMode::rollback()
{
#ifdef SC_LINUX
    run("iptables",  {"-D", "OUTPUT", "-j", "SHADOW_KS"});
    run("iptables",  {"-F", "SHADOW_KS"});
    run("iptables",  {"-X", "SHADOW_KS"});
    run("ip6tables", {"-D", "OUTPUT", "-j", "SHADOW_KS6"});
    run("ip6tables", {"-F", "SHADOW_KS6"});
    run("ip6tables", {"-X", "SHADOW_KS6"});
    run("systemctl", {"stop", "tor"}, 10000);
    m_savedRules.clear();
#endif
}

void PrivacyMode::verify()
{
    // Check whether the SOCKS proxy reaches the Tor network.
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
    const QString out   = p.readAllStandardOutput();
    const bool torOk    = out.contains("\"IsTor\":true");

    if (!torOk) {
        emit verifyResult(false, "SOCKS proxy is NOT routing through Tor.");
        return;
    }

#ifdef SC_LINUX
    // Only claim full traffic protection when the kill-switch rules are confirmed present.
    const bool ksOk = m_active
        && ruleExists("filter", {"OUTPUT", "-j", "SHADOW_KS"})
        && rule6Exists("filter", {"OUTPUT", "-j", "SHADOW_KS6"});

    if (ksOk)
        emit verifyResult(true,  "Full protection confirmed: SOCKS proxy routes through Tor and IPv4/IPv6 kill-switch is in place.");
    else
        emit verifyResult(false, "SOCKS proxy via Tor confirmed — but kill-switch is NOT active. Traffic outside the proxy may not be protected.");
#else
    emit verifyResult(true, "SOCKS proxy via Tor confirmed. Note: no system-wide kill-switch on this platform.");
#endif
}
