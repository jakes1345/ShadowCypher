#pragma once
#include <QObject>
#include <QProcess>
#include <QTemporaryDir>
#include <memory>

namespace shadow {
class MissionRunner : public QObject {
    Q_OBJECT
public:
    explicit MissionRunner(QObject* parent = nullptr, QString executable = {});
    ~MissionRunner() override;
    bool start(const QString& source, const QString& directory, const QString& configIni = {});
    void stop();
    bool running() const { return m_running; }
signals:
    void output(QString text);
    void finished(bool success, QString message);
private:
    QString m_executable;
    QProcess m_process;
    QByteArray m_buffer;
    QString m_error;
    std::unique_ptr<QTemporaryDir> m_temporary;
    bool m_running = false;
    bool m_stopping = false;
    bool m_completed = false;
    void readOutput();
    void finish(bool success, const QString& message);
};
}
