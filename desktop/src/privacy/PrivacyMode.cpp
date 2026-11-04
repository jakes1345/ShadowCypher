#include "PrivacyMode.h"
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#ifdef SC_LINUX
#include <unistd.h>
#endif

#ifndef SC_PRIVACY_HELPER
#define SC_PRIVACY_HELPER ""
#endif

// Written by the helper only once the kill-switch rules are confirmed in place.
static const char* kMarker = "/run/shadowcypher/privacy-active";

PrivacyMode::PrivacyMode(QObject* parent) : QObject(parent)
{
#ifdef SC_LINUX
    // The kill-switch outlives the app; pick up one left on by a previous session.
    if (QFile::exists(kMarker)) {
        m_active = true;
        m_status = "active";
    }
#endif
}

void PrivacyMode::engage()
{
#ifdef SC_LINUX
    runHelper("engage");
#else
    setStatus("unsupported: Windows kill-switch not implemented");
#endif
}

void PrivacyMode::disengage()
{
#ifdef SC_LINUX
    runHelper("disengage");
#endif
}

void PrivacyMode::runHelper(const QString& verb)
{
#ifdef SC_LINUX
    if (m_busy) return;
    const QString helper = QStringLiteral(SC_PRIVACY_HELPER);
    if (helper.isEmpty() || !QFileInfo(helper).isExecutable()) {
        setStatus("error: privacy helper not installed (sudo cmake --install build)");
        return;
    }

    auto* proc = new QProcess(this);
    // Already root (e.g. launched with sudo): no need to go through polkit.
    if (geteuid() == 0)
        proc->start(helper, {verb});
    else
        proc->start("pkexec", {helper, verb});

    setBusy(true);
    setStatus(verb == "engage" ? "engaging" : "disengaging");

    connect(proc, &QProcess::finished, this, [this, proc, verb](int code, QProcess::ExitStatus st) {
        proc->deleteLater();
        setBusy(false);
        const QString out = QString::fromUtf8(proc->readAllStandardOutput()).trimmed();
        onHelperFinished(verb, st == QProcess::NormalExit ? code : -1, out);
    });
    connect(proc, &QProcess::errorOccurred, this, [this, proc](QProcess::ProcessError err) {
        if (err != QProcess::FailedToStart) return;
        proc->deleteLater();
        setBusy(false);
        setStatus("error: pkexec is not available");
    });
#else
    Q_UNUSED(verb)
#endif
}

void PrivacyMode::onHelperFinished(const QString& verb, int code, const QString& output)
{
    // pkexec: 126 = authentication dialog dismissed, 127 = not authorized.
    if (code == 126 || code == 127) {
        setStatus(code == 126 ? "cancelled: authentication dismissed" : "error: not authorized");
        setActive(QFile::exists(kMarker));
        return;
    }

    const QString lastLine = output.section('\n', -1);
    if (code == 0) {
        setActive(verb == "engage");
        setStatus(verb == "engage" ? "active" : "off");
        return;
    }

    // The helper rolls back on failure, so trust the marker for the real state.
    setActive(QFile::exists(kMarker));
    setStatus(lastLine.startsWith("error:") ? lastLine
                                            : QString("error: helper exited with code %1").arg(code));
}

void PrivacyMode::verify()
{
    if (m_busy) return;
    // --socks5-hostname makes Tor resolve DNS; plain --socks5 resolves locally,
    // which the kill-switch blocks (and would leak the lookup anyway).
    auto* proc = new QProcess(this);
    setBusy(true);
    connect(proc, &QProcess::finished, this, [this, proc](int, QProcess::ExitStatus st) {
        proc->deleteLater();
        setBusy(false);
        if (st != QProcess::NormalExit) {
            emit verifyResult(false, "curl crashed.");
            return;
        }
        const bool torOk = proc->readAllStandardOutput().contains("\"IsTor\":true");
        if (!torOk) {
            emit verifyResult(false, "SOCKS proxy is NOT routing through Tor.");
            return;
        }
#ifdef SC_LINUX
        if (m_active && QFile::exists(kMarker))
            emit verifyResult(true,  "Full protection confirmed: SOCKS proxy routes through Tor and IPv4/IPv6 kill-switch is in place.");
        else
            emit verifyResult(false, "SOCKS proxy via Tor confirmed — but kill-switch is NOT active. Traffic outside the proxy may not be protected.");
#else
        emit verifyResult(true, "SOCKS proxy via Tor confirmed. Note: no system-wide kill-switch on this platform.");
#endif
    });
    connect(proc, &QProcess::errorOccurred, this, [this, proc](QProcess::ProcessError err) {
        if (err != QProcess::FailedToStart) return;
        proc->deleteLater();
        setBusy(false);
        emit verifyResult(false, "curl is not installed.");
    });
    proc->start("curl", {"--socks5-hostname", "127.0.0.1:9050", "--max-time", "10", "-s",
                         "https://check.torproject.org/api/ip"});
}
