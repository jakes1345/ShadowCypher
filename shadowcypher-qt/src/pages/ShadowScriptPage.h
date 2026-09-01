#pragma once
#include <QWidget>
#include <QListWidget>
#include <QTextEdit>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QLabel>
#include "../ipc/IpcClient.h"
#include "../widgets/TacticalTerminal.h"

class ShadowScriptPage : public QWidget {
    Q_OBJECT
public:
    explicit ShadowScriptPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void loadMissions();
    void onMissionSelected(QListWidgetItem* item);
    void runMission();
    void stopMission();
    void onIpcResult(int id, QJsonObject result);

private:
    IpcClient*        m_ipc;
    QListWidget*      m_missionList;
    QPlainTextEdit*   m_editor;
    TacticalTerminal* m_output;
    QPushButton*      m_runBtn;
    QPushButton*      m_stopBtn;
    QLabel*           m_statusLabel;
    QString           m_currentMission;
    int               m_runReqId  = -1;
    int               m_stopReqId = -1;
    bool              m_running   = false;

    void buildUi();
    void setRunningState(bool running);
    void scanLocalMissions();

    static QString missionDir();
};
