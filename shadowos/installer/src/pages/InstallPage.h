#pragma once
#include <QWidget>
#include <QTextEdit>
#include <QLabel>
#include <QProgressBar>
#include <QProcess>
#include "../InstallState.h"

class InstallPage : public QWidget {
    Q_OBJECT
public:
    explicit InstallPage(InstallState* state, QWidget* parent = nullptr);
    void begin();

signals:
    void finished(bool success);

private slots:
    void onReadyRead();
    void onFinished(int exitCode, QProcess::ExitStatus status);

private:
    InstallState* m_state;
    QTextEdit*    m_log;
    QLabel*       m_status;
    QProgressBar* m_progress;
    QProcess*     m_proc;

    QString buildScript();
    QByteArray configJson() const;
    QByteArray credentialsJson() const;
    static constexpr const char* kConfigPath = "/tmp/shadowos-install.json";
    static constexpr const char* kCredsPath  = "/tmp/shadowos-install-creds.json";
    void    appendLog(const QString& line, bool error = false);
};
