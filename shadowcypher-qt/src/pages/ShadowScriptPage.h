#pragma once
#include <QWidget>
#include <QListWidget>
#include <QTextEdit>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QLabel>
#include "MissionRunner.h"
#include "../widgets/TacticalTerminal.h"

class ShadowScriptPage : public QWidget {
    Q_OBJECT
public:
    explicit ShadowScriptPage(QWidget* parent = nullptr);

private slots:
    void onMissionSelected(QListWidgetItem* item);
    void runMission();
    void stopMission();

private:
    shadow::MissionRunner* m_runner;
    QListWidget*      m_missionList;
    QPlainTextEdit*   m_editor;
    TacticalTerminal* m_output;
    QPushButton*      m_runBtn;
    QPushButton*      m_stopBtn;
    QLabel*           m_statusLabel;
    QString           m_currentMission;
    QString           m_sourceDirectory;
    bool              m_running   = false;

    void buildUi();
    void setRunningState(bool running);
    void scanLocalMissions();

    static QString missionDir();
};
