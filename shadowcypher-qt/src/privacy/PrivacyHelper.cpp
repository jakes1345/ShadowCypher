#include "PrivacyHelper.h"
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#ifdef Q_OS_UNIX
#include <unistd.h>
#endif

#ifndef SC_PRIVACY_HELPER
#define SC_PRIVACY_HELPER ""
#endif

static const char* kMarker = "/run/shadowcypher/privacy-active";

PrivacyHelper::PrivacyHelper(QObject* parent) : QObject(parent) {}

bool PrivacyHelper::killSwitchActive()
{
    return QFile::exists(QString::fromLatin1(kMarker));
}

void PrivacyHelper::run(const QString& verb)
{
    if (m_busy) return;
#if defined(Q_OS_LINUX)
    const QString helper = QStringLiteral(SC_PRIVACY_HELPER);
    if (helper.isEmpty() || !QFileInfo(helper).isExecutable()) {
        emit finished(false, killSwitchActive(),
                      "The privacy helper isn't installed. Install ShadowCypher with "
                      "`sudo cmake --install build`.");
        return;
    }

    auto* proc = new QProcess(this);
    m_busy = true;
    connect(proc, &QProcess::finished, this, [this, proc, verb](int code, QProcess::ExitStatus st) {
        proc->deleteLater();
        m_busy = false;
        done(verb, st == QProcess::NormalExit ? code : -1,
             QString::fromUtf8(proc->readAllStandardOutput()).trimmed());
    });
    connect(proc, &QProcess::errorOccurred, this, [this, proc](QProcess::ProcessError err) {
        if (err != QProcess::FailedToStart) return;
        proc->deleteLater();
        m_busy = false;
        emit finished(false, killSwitchActive(), "pkexec isn't available, so the firewall can't be changed.");
    });
    // Already root (e.g. started with sudo): polkit isn't needed.
    if (geteuid() == 0)
        proc->start(helper, {verb});
    else
        proc->start(QStringLiteral("pkexec"), {helper, verb});
#else
    Q_UNUSED(verb)
    emit finished(false, false, "Ghost mode's kill-switch is only available on Linux.");
#endif
}

void PrivacyHelper::done(const QString& verb, int code, const QString& output)
{
    const bool active = killSwitchActive();
    // pkexec: 126 = authentication dialog dismissed, 127 = not authorized.
    if (code == 126) { emit finished(false, active, "Cancelled: the administrator prompt was dismissed."); return; }
    if (code == 127) { emit finished(false, active, "Not authorized to change the firewall."); return; }
    if (code == 0) {
        emit finished(true, active, verb == QLatin1String("engage")
                                        ? "Kill-switch on: only Tor can reach the network."
                                        : "Kill-switch off: normal networking restored.");
        return;
    }
    // The helper rolls back on failure, so the marker is the real state.
    const QString last = output.section('\n', -1);
    emit finished(false, active, last.startsWith(QLatin1String("error:"))
                                     ? last.mid(7)
                                     : QString("The privacy helper failed (exit code %1).").arg(code));
}
