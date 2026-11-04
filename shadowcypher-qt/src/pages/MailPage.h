#pragma once
#include <QWidget>
#include <QListWidget>
#include <QTextEdit>
#include <QPlainTextEdit>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QTimer>
#include <QJsonObject>
#include <QJsonArray>

class MailPage : public QWidget {
    Q_OBJECT
public:
    explicit MailPage(QWidget* parent = nullptr);

private slots:
    void refresh();
    void onMessageClicked(QListWidgetItem* item);
    void sendMail();
    void toggleCompose();

private:
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

    bool    m_sending = false;
    QString m_openId;   // message currently shown in the body view

    void    buildUi();
    void    loadMessages(const QJsonArray& messages);
    void    showMessage(const QJsonObject& msg, const QString& body);
    void    finishSend(bool ok, const QString& error);

    // Helpers
    QWidget* createMessageWidget(const QJsonObject& msg);
    void     setComposeEnabled(bool on);
    void     showSendStatus(const QString& text, bool success);
};
