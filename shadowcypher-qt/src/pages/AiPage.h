#pragma once
#include <QWidget>
#include <QTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QTimer>
#include "../ipc/IpcClient.h"

// AI Assistant chat page — streams responses via IPC to Python AI engine
class AiPage : public QWidget {
    Q_OBJECT
public:
    explicit AiPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void sendMessage();
    void onIpcResult(int id, QJsonObject result);

private:
    IpcClient*   m_ipc;
    QTextEdit*   m_chatView;
    QLineEdit*   m_input;
    QPushButton* m_sendBtn;
    QLabel*      m_modelLabel;
    int          m_chatReqId = -1;
    bool         m_waiting   = false;

    void buildUi();
    void appendMessage(const QString& role, const QString& content);
    void setWaiting(bool waiting);
};
