#pragma once
#include <QWidget>
#include <QTabWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QProcess>
#include <QCheckBox>
#include <QComboBox>
#include "../widgets/TacticalTerminal.h"

class VulnPage : public QWidget {
    Q_OBJECT
public:
    explicit VulnPage(QWidget* parent = nullptr);

private slots:
    void runNikto();
    void runSqlmap();
    void runNmapNse();
    void runSearchsploit();
    void stopAll();
    void onOutput();
    void onFinished(int code, QProcess::ExitStatus);

private:
    void buildUi();
    void startTool(const QStringList& cmd, const QString& label, TacticalTerminal* out);

    QTabWidget*   m_tabs;

    // Nikto tab
    QLineEdit*    m_niktoTarget;
    QCheckBox*    m_niktoSsl;
    QComboBox*    m_niktoCgiCombo;
    TacticalTerminal* m_niktoOut;

    // SQLmap tab
    QLineEdit*    m_sqlUrl;
    QComboBox*    m_sqlLevel;
    QComboBox*    m_sqlRisk;
    QCheckBox*    m_sqlDbs;
    TacticalTerminal* m_sqlOut;

    // Nmap NSE tab
    QLineEdit*    m_nseTarget;
    QLineEdit*    m_nsePorts;
    QComboBox*    m_nseScript;
    TacticalTerminal* m_nseOut;

    // Searchsploit tab
    QLineEdit*    m_splitQuery;
    TacticalTerminal* m_splitOut;

    QPushButton*  m_stopBtn;

    QProcess*     m_proc{nullptr};
    QString       m_activeLabel;
    TacticalTerminal* m_activeOut{nullptr};
};
