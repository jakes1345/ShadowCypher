#pragma once
#include <QWidget>
#include <QListWidget>
#include <QTextEdit>
#include <QPlainTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QTimer>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonObject>
#include <QJsonArray>
#include "../ipc/IpcClient.h"

class MailPage : public QWidget {
    Q_OBJECT
public:
    explicit MailPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void refresh();
    void onMessageClicked(QListWidgetItem* item);
    void sendMail();
    void toggleCompose();
    void onIpcResult(int id, QJsonObject result);
    void onNetworkReply(QNetworkReply* reply);

private:
    IpcClient*            m_ipc;
    QNetworkAccessManager* m_nam;

    // Left panel
    QListWidget*     m_msgList;
    QPushButton*     m_composeBtn;
    QLabel*          m_syncLabel;
    QTimer*          m_timer;

    // Right panel — body view
    QTextEdit*       m_bodyView;

    // Right panel — compose
    QWidget*         m_composePanel;
    QLineEdit*       m_toField;
    QLineEdit*       m_subjectField;
    QPlainTextEdit*  m_bodyField;
    QPushButton*     m_sendBtn;
    QLabel*          m_sendStatusLabel;

    int  m_inboxReqId = -1;
    int  m_sendReqId  = -1;
    bool m_sending    = false;

    void    buildUi();
    void    loadMessages(const QJsonArray& messages);
    void    fetchInboxHttp();
    void    sendMailHttp(const QString& to, const QString& subject, const QString& body);
    QString apiKey() const;
    QString apiBaseUrl() const;

    // Helpers
    QWidget* createMessageWidget(const QJsonObject& msg);
    void     setComposeEnabled(bool on);
    void     showSendStatus(const QString& text, bool success);
};
