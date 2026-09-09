#pragma once
#include <QWidget>
#include <QLineEdit>
#include <QTabWidget>
#include <QLabel>
#include <QPushButton>
#include <QProcess>
#include <QComboBox>
#include "../widgets/TacticalTerminal.h"

class OsintPage : public QWidget {
    Q_OBJECT
public:
    explicit OsintPage(QWidget* parent = nullptr);

private slots:
    void runWhois();
    void runDns();
    void runHarvester();
    void runSubfinder();
    void runAmass();
    void runShodan();
    void stopAll();
    void onOutput();
    void onFinished(int code, QProcess::ExitStatus);

private:
    void buildUi();
    void startTool(const QStringList& cmd, const QString& label);

    QLineEdit*      m_targetEdit;
    QTabWidget*     m_tabs;

    // Per-tab terminals
    TacticalTerminal* m_whoisOut;
    TacticalTerminal* m_dnsOut;
    TacticalTerminal* m_harvOut;
    TacticalTerminal* m_subOut;
    TacticalTerminal* m_amassOut;
    TacticalTerminal* m_shodanOut;

    QPushButton*    m_stopBtn;

    QProcess*       m_proc{nullptr};
    QString         m_activeLabel;
    TacticalTerminal* m_activeOut{nullptr};
};
