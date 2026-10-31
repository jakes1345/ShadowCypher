#include "MissionRunner.h"
#include <QCoreApplication>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QTimer>

namespace shadow {
MissionRunner::MissionRunner(QObject* parent, QString executable)
    : QObject(parent), m_executable(std::move(executable)) {
    connect(&m_process, &QProcess::started, this, [this] { if (m_stopping) m_process.terminate(); });
    connect(&m_process, &QProcess::readyReadStandardOutput, this, &MissionRunner::readOutput);
    connect(&m_process, &QProcess::readyReadStandardError, this, [this] {
        const auto text = QString::fromUtf8(m_process.readAllStandardError()).trimmed();
        if (!text.isEmpty()) emit output(text);
    });
    connect(&m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) finish(false, "Cannot start native runtime: " + m_process.errorString());
    });
    connect(&m_process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
        [this](int code, QProcess::ExitStatus status) {
            readOutput();
            const bool success = !m_stopping && m_completed && m_error.isEmpty() && code == 0 && status == QProcess::NormalExit;
            const auto message = m_stopping ? QString("Mission cancelled") : (!m_error.isEmpty() ? m_error :
                success ? QString("Mission complete") : QString("Native runtime exited without completing the mission (exit %1)").arg(code));
            finish(success, message);
        });
}

MissionRunner::~MissionRunner() {
    disconnect(&m_process, nullptr, this, nullptr);
    if (m_process.state() != QProcess::NotRunning) {
        m_process.terminate();
        if (!m_process.waitForFinished(3000)) { m_process.kill(); m_process.waitForFinished(1000); }
    }
}

bool MissionRunner::start(const QString& source, const QString& directory, const QString& configIni) {
    if (m_running) return false;
    if (m_executable.isEmpty()) {
        for (const auto& candidate : {QCoreApplication::applicationDirPath()+"/shadowcypher-runtime",
              QCoreApplication::applicationDirPath()+"/core/shadowcypher-runtime", QStandardPaths::findExecutable("shadowcypher-runtime")}) {
            if (!candidate.isEmpty() && QFileInfo(candidate).isExecutable()) { m_executable = candidate; break; }
        }
    }
    if (m_executable.isEmpty()) { emit finished(false, "Native runtime is missing; rebuild or reinstall ShadowCypher"); return false; }
    m_temporary = std::make_unique<QTemporaryDir>();
    if (!m_temporary->isValid()) { emit finished(false, "Cannot create mission workspace"); return false; }
    QFile file(m_temporary->filePath("mission.shadow"));
    const auto bytes = source.toUtf8();
    if (bytes.size() > 1024*1024 || !file.open(QIODevice::WriteOnly) || file.write(bytes) != bytes.size()) {
        emit finished(false, "Cannot write mission source (limit 1 MiB)"); m_temporary.reset(); return false;
    }
    file.setPermissions(QFile::ReadOwner | QFile::WriteOwner);
    file.close();
    QStringList args{"script", file.fileName(), "--json-lines", "--source-directory", directory};
    if (!configIni.isEmpty()) args << "--config-ini" << configIni;
    m_running = true; m_stopping = false; m_completed = false;
    m_error.clear(); m_buffer.clear();
    m_process.start(m_executable, args);
    return true;
}

void MissionRunner::stop() {
    if (!m_running || m_stopping) return;
    m_stopping = true;
    m_process.terminate();
    // Bound shutdown even if an external library becomes unresponsive.
    const auto pid = m_process.processId();
    QTimer::singleShot(3000, this, [this, pid] {
        if (m_running && m_stopping && m_process.processId() == pid) m_process.kill();
    });
}

void MissionRunner::readOutput() {
    m_buffer += m_process.readAllStandardOutput();
    if (m_buffer.size() > 8*1024*1024) { m_error = "Native runtime output exceeded 8 MiB"; stop(); return; }
    qsizetype end;
    while ((end = m_buffer.indexOf('\n')) >= 0) {
        const auto line = m_buffer.left(end); m_buffer.remove(0, end+1);
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(line, &error);
        if (error.error != QJsonParseError::NoError || !doc.isObject()) { m_error = "Invalid native runtime output"; continue; }
        const auto record = doc.object();
        const auto type = record.value("type").toString();
        if (type == "output") emit output(record.value("text").toString());
        else if (type == "complete") m_completed = true;
        else if (type == "error") m_error = record.value("message").toString("Mission failed");
        else m_error = "Unknown native runtime output record";
    }
}

void MissionRunner::finish(bool success, const QString& message) {
    if (!m_running) return;
    m_running = false;
    m_temporary.reset();
    emit finished(success, message);
}
}
