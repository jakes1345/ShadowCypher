#pragma once
#include <QWidget>
#include <QWebSocket>
#include <QLineEdit>
#include <QPushButton>
#include <QLabel>
#include <QScrollArea>
#include <QVBoxLayout>
#include "../ipc/IpcClient.h"

// Encrypted real-time chat page — connects to ShadowCypher chat server via WebSocket
class ChatPage : public QWidget {
    Q_OBJECT
public:
    explicit ChatPage(IpcClient* ipc, QWidget* parent = nullptr);

private slots:
    void joinRoom();
    void sendMessage();
    void onWsConnected();
    void onWsDisconnected();
    void onTextMessageReceived(const QString& message);

private:
    IpcClient*   m_ipc;
    QWebSocket*  m_socket;

    // Top bar
    QLineEdit*   m_roomInput;
    QPushButton* m_joinBtn;
    QLabel*      m_connDot;

    // Message area
    QScrollArea* m_scrollArea;
    QWidget*     m_bubblesWidget;
    QVBoxLayout* m_bubblesLayout;

    // Bottom bar
    QLineEdit*   m_msgInput;
    QPushButton* m_sendBtn;

    QString m_currentRoom;
    QString m_apiKey;
    QString m_serverUrl;

    void buildUi();
    void connectWebSocket();
    void appendBubble(const QString& sender, const QString& content, bool isSelf);
    void scrollToBottom();

    // Simulated E2E encryption layer (AES-256-GCM placeholder)
    // TODO: replace with real AES-256-GCM via OpenSSL
    QString encryptMessage(const QString& plaintext, const QString& key);
    QString decryptMessage(const QString& ciphertext, const QString& key);
};
