#include "Process.h"
#include <QElapsedTimer>
#include <QProcess>
#ifdef Q_OS_UNIX
#include <csignal>
#include <unistd.h>
#endif

namespace shadow {
void checkCancelled(const Cancel& cancel) {
    if (cancel && cancel->load()) throw Error("Operation cancelled");
}

ProcessResult runProcess(const QString& program, const QStringList& args,
                         const Cancel& cancel, int timeoutMs,
                         const QByteArray& input, const QString& directory) {
    checkCancelled(cancel);
    if (program.isEmpty()) throw Error("A program is required");
    QProcess process;
#ifdef Q_OS_UNIX
    process.setChildProcessModifier([] { if (::setpgid(0, 0) != 0) ::_exit(126); });
#endif
    if (!directory.isEmpty()) process.setWorkingDirectory(directory);
    process.start(program, args);
    if (!process.waitForStarted(3000))
        throw Error(QString("Cannot start %1: %2").arg(program, process.errorString()));
    if (!input.isEmpty()) process.write(input);
    process.closeWriteChannel();
    ProcessResult result;
    QElapsedTimer timer;
    timer.start();
    auto drain = [&] {
        result.out += process.readAllStandardOutput();
        result.err += process.readAllStandardError();
        if (result.out.size() + result.err.size() > 4 * 1024 * 1024)
            throw Error("Command output exceeded 4 MiB");
    };
    try {
        while (process.state() != QProcess::NotRunning) {
            checkCancelled(cancel);
            if (timer.elapsed() >= timeoutMs) throw Error("Command timed out: " + program);
            process.waitForFinished(25);
            drain();
        }
        drain();
    } catch (...) {
#ifdef Q_OS_UNIX
        if (process.processId() > 0) ::kill(-static_cast<pid_t>(process.processId()), SIGKILL);
#endif
        process.kill();
        process.waitForFinished(3000);
        throw;
    }
    if (process.exitStatus() == QProcess::CrashExit) throw Error("Command crashed: " + program);
    result.exitCode = process.exitCode();
    return result;
}

QStringList splitCommand(const QString& command) {
    // POSIX-style quoting without shell expansion, redirection, or pipelines.
    QStringList args;
    QString current;
    QChar quote;
    bool escaped = false, started = false;
    for (QChar c : command) {
        if (escaped) { current += c; escaped = false; started = true; }
        else if (c == '\\' && quote != '\'') { escaped = true; started = true; }
        else if (!quote.isNull()) {
            if (c == quote) quote = {}; else current += c;
        } else if (c == '\'' || c == '"') { quote = c; started = true; }
        else if (c.isSpace()) {
            if (started) { args.append(current); current.clear(); started = false; }
        } else { current += c; started = true; }
    }
    if (escaped || !quote.isNull()) throw Error("Unterminated command quote or escape");
    if (started) args.append(current);
    if (args.isEmpty()) throw Error("Empty command");
    return args;
}
}
